"""
Proxy service to Anthropic Claude API for e-learning AI features (Lots 15/16/17).
Falls back to a stub response if ANTHROPIC_API_KEY is not configured.
"""
import json
import logging
import threading
import time
from collections import deque
from django.conf import settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = getattr(settings, 'ANTHROPIC_API_KEY', '')
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', '')
GEMINI_VISION_MODEL = getattr(settings, 'GEMINI_VISION_MODEL', 'gemini-2.0-flash')
GEMINI_MAX_CONCURRENT_REQUESTS = getattr(settings, 'GEMINI_MAX_CONCURRENT_REQUESTS', 12)
# Real requests-per-minute budget for the configured GEMINI_API_KEY — a
# concurrency cap alone (above) only limits how many calls are *in flight*
# at once; it doesn't stop the app from *firing* more requests per minute
# than Gemini actually allows, which just trades "blocked server threads"
# for "wasted 429 responses" without saving any real capacity. Default is
# conservative (comfortably under the free tier's own low RPM ceiling) —
# raise it via the env var once billing is enabled on the Gemini project.
GEMINI_RPM_LIMIT = getattr(settings, 'GEMINI_RPM_LIMIT', 12)
# Slots carved out of GEMINI_RPM_LIMIT reserved exclusively for `priority`
# calls (see analyze_exam_snapshot) — checking whether an *already
# suspended* student keeps misbehaving is the highest-value use of scarce
# quota (see SecureExamTakeScreen.js's suspension-escalation flow), so a
# burst of routine first-time checks from other students can never fully
# starve those checks out.
GEMINI_PRIORITY_RPM_RESERVE = getattr(settings, 'GEMINI_PRIORITY_RPM_RESERVE', 3)

# One process-wide semaphore shared by every request this worker process
# handles (analyze_exam_snapshot runs as a synchronous DRF view, so each
# concurrent call occupies its own thread while it blocks on Gemini's
# network I/O). Bounds how many Gemini calls can be in flight at once so a
# burst of concurrent exam-takers doesn't fire dozens of parallel requests
# that (a) collectively exceed the account's own rate limit — every one of
# them coming back 429 — and (b) exhaust the ASGI sync-view thread pool,
# which used to make *unrelated* requests across the whole app queue up
# behind these slow, blocking calls too. Excess requests wait briefly for a
# free slot (acquire has its own short timeout below) instead of piling up
# unboundedly.
_gemini_semaphore = threading.Semaphore(GEMINI_MAX_CONCURRENT_REQUESTS)

# Sliding-window (last 60s) request counter, checked *before* even touching
# the semaphore/network — cheap, in-memory, and specifically caps the actual
# requests-per-minute rate against GEMINI_RPM_LIMIT, which the semaphore
# above cannot do on its own (a burst of short, fast requests can blow past
# an RPM budget while never having more than a couple in flight at once).
# Process-local: on a deployment with multiple Daphne/Gunicorn worker
# processes each process gets its own independent budget, so the effective
# total is (GEMINI_RPM_LIMIT × process count) — fine for the single/few
# -process scale this project runs at; move to a Redis-backed counter
# (REDIS_URL is already configured for Channels/Celery) if that stops
# holding.
_rpm_lock = threading.Lock()
_rpm_timestamps = deque()          # monotonic times of general (non-priority) grants in the last 60s
_rpm_priority_timestamps = deque() # monotonic times of priority grants in the last 60s


def _try_acquire_rpm_slot(priority: bool) -> bool:
    now = time.monotonic()
    cutoff = now - 60
    with _rpm_lock:
        while _rpm_timestamps and _rpm_timestamps[0] < cutoff:
            _rpm_timestamps.popleft()
        while _rpm_priority_timestamps and _rpm_priority_timestamps[0] < cutoff:
            _rpm_priority_timestamps.popleft()
        total_used = len(_rpm_timestamps) + len(_rpm_priority_timestamps)
        if priority:
            # Priority traffic can draw on the whole budget, not just its
            # reserve — the reserve only exists to protect it *from*
            # general traffic, not to cap it below general's own share.
            if total_used >= GEMINI_RPM_LIMIT:
                return False
            _rpm_priority_timestamps.append(now)
            return True
        general_budget = max(GEMINI_RPM_LIMIT - GEMINI_PRIORITY_RPM_RESERVE, 0)
        if len(_rpm_timestamps) >= general_budget:
            return False
        _rpm_timestamps.append(now)
        return True


def _call_claude(system_prompt: str, messages: list[dict], max_tokens: int = 2048) -> tuple[str, int]:
    """Call Claude API and return (text_response, tokens_used)."""
    if not ANTHROPIC_API_KEY:
        return _stub_response(messages), 0

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        text = response.content[0].text if response.content else ''
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return text, tokens
    except Exception as e:
        return f"[Erreur IA : {e}]", 0


def _stub_response(messages: list[dict]) -> str:
    last = messages[-1]['content'] if messages else ''
    return (
        f"[Mode démo — configurez ANTHROPIC_API_KEY pour activer l'IA réelle]\n"
        f"Question reçue : {last[:200]}"
    )


def chat_tutor(history: list[dict], subject_name: str = '', lesson_title: str = '') -> tuple[str, int]:
    """Lot 15 — Assistant tutorat étudiant."""
    context = ''
    if subject_name:
        context += f" La matière est : {subject_name}."
    if lesson_title:
        context += f" La leçon en cours est : {lesson_title}."

    system = (
        "Tu es un assistant pédagogique bienveillant et expert dans toutes les matières universitaires."
        f"{context}"
        " Réponds de façon claire, pédagogique et en français. "
        "Explique les concepts, propose des exemples, aide l'étudiant à comprendre sans donner les réponses directement. "
        "Si l'étudiant demande un quiz, génère des questions pertinentes. "
        "Utilise des listes à puces et du Markdown pour une meilleure lisibilité."
    )
    return _call_claude(system, history, max_tokens=1500)


def chat_teacher(history: list[dict], subject_name: str = '') -> tuple[str, int]:
    """Lot 16 — Assistant enseignant."""
    context = f" La matière est : {subject_name}." if subject_name else ''
    system = (
        "Tu es un assistant pour enseignants universitaires. Tu aides à créer du contenu pédagogique."
        f"{context}"
        " Tu peux générer : cours structurés, quiz, examens, barèmes, commentaires de correction, "
        "fiches de révision, plans de cours, diapositives. "
        "Réponds en français, avec un format Markdown clair et professionnel."
    )
    return _call_claude(system, history, max_tokens=3000)


def generate_content(generate_type: str, prompt: str, options: dict = None) -> tuple[str, int]:
    """Lot 16 — Génération de contenu pédagogique."""
    options = options or {}

    type_instructions = {
        'quiz': (
            "Génère un quiz avec des questions variées (QCU, QCM, texte libre). "
            "Pour chaque question inclus : le texte de la question, le type (QCU/QCM/TEXT), "
            "les choix de réponse (avec indication de la bonne réponse), une explication. "
            "Format JSON structuré."
        ),
        'summary': "Génère un résumé structuré clair et complet du contenu demandé.",
        'flashcards': (
            "Génère des flashcards (recto/verso) pour mémoriser les concepts clés. "
            "Format : liste de paires question/réponse en JSON."
        ),
        'plan': "Génère un plan de révision détaillé et progressif.",
        'slides': (
            "Génère un plan de diapositives (slides) structuré avec titre, sous-titres "
            "et points clés pour chaque slide."
        ),
        'exam': (
            "Génère un examen universitaire complet avec différents types de questions, "
            "barème indicatif et consignes. Format Markdown."
        ),
        'rubric': "Génère un barème de correction détaillé avec critères et points.",
        'feedback': "Génère un commentaire de correction pédagogique et constructif.",
    }

    instruction = type_instructions.get(generate_type, "Génère le contenu demandé.")
    system = (
        f"Tu es un expert en création de contenu pédagogique universitaire. {instruction} "
        "Réponds en français."
    )
    messages = [{'role': 'user', 'content': prompt}]
    return _call_claude(system, messages, max_tokens=3000)


def grade_submission(submission_text: str, criteria: str = '', max_score: float = 20) -> tuple[str, int]:
    """Lot 17 — Correction automatique de copie."""
    system = (
        "Tu es un correcteur universitaire expert. Tu évalues des copies d'étudiants. "
        f"Note maximale : {max_score} points. "
        + (f"Critères de correction : {criteria}. " if criteria else "")
        + "Fournis : une note chiffrée, des commentaires détaillés par section, "
        "les points forts, les points faibles, et des conseils d'amélioration. "
        "Format de réponse JSON : {\"score\": <note>, \"feedback\": \"...\", \"strengths\": [...], \"weaknesses\": [...], \"suggestions\": [...]}"
    )
    messages = [{'role': 'user', 'content': f"Voici la copie à corriger :\n\n{submission_text}"}]
    return _call_claude(system, messages, max_tokens=2000)


def check_plagiarism_basic(text: str, references: list[str]) -> dict:
    """Lot 17 — Détection de similitude basique (sans API externe)."""
    from difflib import SequenceMatcher

    results = []
    for ref in references:
        ratio = SequenceMatcher(None, text.lower(), ref.lower()).ratio()
        results.append(round(ratio * 100, 1))

    max_similarity = max(results) if results else 0
    return {
        'max_similarity_percent': max_similarity,
        'is_flagged': max_similarity > 70,
        'details': results,
    }


def _gemini_stub_result(reason: str) -> dict:
    return {
        'description': reason,
        'face_detected': True,
        'phone_detected': False,
        'multiple_faces': False,
        'suspicious': False,
        'looking_away': False,
        'gaze_direction': 'aucun',
        # False whenever this is a fallback rather than a real verdict — a
        # "clean" stub result means "we don't know", not "nothing suspicious
        # was observed". Callers that adapt their polling rate (mobile's
        # capture loop) or that want to distinguish the two cases read this.
        'ai_available': False,
    }


def analyze_exam_snapshot(image_bytes: bytes, priority: bool = False) -> dict:
    """Proctoring — Gemini vision analysis of one exam webcam snapshot.

    Unlike the boolean-only client-side TensorFlow.js detection, this asks a
    real vision model to describe in plain French exactly what it observes
    (talking to someone off-camera, looking at a phone, a second person in
    frame...), not just "phone: yes/no". Returns a dict always shaped the
    same way — including a 'description' string suitable for direct display
    next to the snapshot in the admin review screen — so callers never need
    to special-case a missing/failed analysis.

    `priority=True` marks a check for a session that's *already suspended*
    (verifying whether the student keeps misbehaving during the suspension —
    see SecureExamTakeScreen.js) — the single highest-value use of a scarce
    Gemini quota, so it draws from a reserved slice of the rate budget that
    routine first-offense checks can't touch (see GEMINI_PRIORITY_RPM_RESERVE).

    Falls back to a neutral stub (no flags raised) if GEMINI_API_KEY isn't
    configured, the rate/concurrency budget is exhausted, or the call fails,
    so proctoring degrades gracefully instead of crashing when the free-tier
    key is absent or rate-limited.
    """
    if not GEMINI_API_KEY:
        return _gemini_stub_result("Analyse IA indisponible (GEMINI_API_KEY non configurée).")

    if not _try_acquire_rpm_slot(priority):
        # Known in advance we'd very likely just get a 429 back — don't even
        # spend a semaphore slot or a network round-trip finding that out;
        # conserve the budget for the next capture instead.
        logger.info('Gemini snapshot analysis skipped — RPM budget (%s/min, priority=%s) exhausted.', GEMINI_RPM_LIMIT, priority)
        return _gemini_stub_result(
            "Analyse IA momentanément indisponible (service surchargé) — la prochaine capture réessaiera automatiquement."
        )

    import base64
    import requests

    img_b64 = base64.b64encode(image_bytes).decode()
    prompt = (
        "Tu es un système de surveillance d'examen en ligne. Regarde très attentivement cette "
        "capture webcam d'un(e) étudiant(e) en train de composer — y compris les bords de "
        "l'image et tout ce que la personne tient dans ses mains ou près de son visage, même "
        "partiellement visible ou flou — et décris EXACTEMENT ce que tu observes, en une phrase "
        "courte et factuelle en français. Sois précis et concret, par exemple : \"L'étudiant "
        "regarde son téléphone posé à côté du clavier\", \"Une deuxième personne est visible "
        "derrière l'étudiant\", \"L'étudiant semble parler à quelqu'un hors champ\", \"L'étudiant "
        "tient un téléphone ou un objet devant son visage\", \"Aucune anomalie, l'étudiant "
        "regarde son écran normalement\". En cas de doute sur la présence d'un téléphone ou d'un "
        "objet tenu en main, signale-le plutôt que de l'ignorer (mieux vaut un faux positif "
        "qu'une fraude manquée). Regarde aussi où pointe le regard/la tête de l'étudiant : un "
        "regard bref vers le clavier ou le bas de l'écran est normal, mais un regard clairement "
        "détourné et soutenu — vers le haut (au plafond), la gauche, la droite, ou carrément "
        "retourné vers l'arrière/le côté (comme pour regarder quelqu'un ou quelque chose hors "
        "champ) — doit être signalé avec la direction observée."
    )
    response_schema = {
        'type': 'OBJECT',
        'properties': {
            'description':     {'type': 'STRING'},
            'face_detected':   {'type': 'BOOLEAN'},
            'phone_detected':  {'type': 'BOOLEAN'},
            'multiple_faces':  {'type': 'BOOLEAN'},
            'suspicious':      {'type': 'BOOLEAN'},
            'looking_away':    {'type': 'BOOLEAN'},
            'gaze_direction':  {'type': 'STRING', 'enum': ['haut', 'bas', 'gauche', 'droite', 'derriere', 'aucun']},
        },
        'required': [
            'description', 'face_detected', 'phone_detected', 'multiple_faces', 'suspicious',
            'looking_away', 'gaze_direction',
        ],
    }

    # Bound how long a request waits for a free concurrency slot before
    # giving up — under a genuine burst (dozens of students' captures
    # landing at once), queuing forever here would just move the pile-up
    # from "blocked on Gemini" to "blocked on this semaphore", tying up the
    # same worker threads either way. Failing fast into the neutral stub
    # after a few seconds keeps this one slow proctoring tick from blocking
    # the thread indefinitely — the next capture (a few seconds later) tries
    # again on its own.
    if not _gemini_semaphore.acquire(timeout=8):
        logger.warning('Gemini snapshot analysis skipped — concurrency limit (%s) reached.', GEMINI_MAX_CONCURRENT_REQUESTS)
        return _gemini_stub_result(
            "Analyse IA momentanément indisponible (service surchargé) — la prochaine capture réessaiera automatiquement."
        )

    try:
        # Two attempts, short timeout each — worst case this call blocks its
        # thread for roughly (6 + 1 + 6) = 13s instead of the ~65s it could
        # reach at 3 attempts × 20s timeout with a growing sleep backoff.
        # That budget matters a lot under concurrent load: every second a
        # thread spends blocked here is a second it can't serve any other
        # request (this view runs synchronously), so a handful of slow calls
        # used to be enough to exhaust the whole app's request-handling
        # capacity, not just this endpoint's.
        max_attempts = 2
        last_error = None
        for attempt in range(max_attempts):
            try:
                resp = requests.post(
                    f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_VISION_MODEL}:generateContent',
                    params={'key': GEMINI_API_KEY},
                    json={
                        'contents': [{
                            'parts': [
                                {'text': prompt},
                                {'inline_data': {'mime_type': 'image/jpeg', 'data': img_b64}},
                            ],
                        }],
                        'generationConfig': {
                            'temperature': 0.1,
                            'responseMimeType': 'application/json',
                            # A strict schema (rather than just prompting for JSON)
                            # is what actually guarantees well-formed, complete
                            # output — responseMimeType alone still occasionally
                            # produced JSON that failed to parse.
                            'responseSchema': response_schema,
                            'maxOutputTokens': 800,
                            # Newer Gemini models spend part of the output token
                            # budget on hidden "thinking" tokens by default — for a
                            # one-sentence classification task that just silently
                            # truncates the actual JSON answer before it's written.
                            'thinkingConfig': {'thinkingBudget': 0},
                        },
                    },
                    timeout=6,
                )
                resp.raise_for_status()
                text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                parsed = json.loads(text)
                return {
                    'description': parsed.get('description') or 'Analyse indisponible.',
                    'face_detected': parsed.get('face_detected', True),
                    'phone_detected': parsed.get('phone_detected', False),
                    'multiple_faces': parsed.get('multiple_faces', False),
                    'suspicious': parsed.get('suspicious', False),
                    'looking_away': parsed.get('looking_away', False),
                    'gaze_direction': parsed.get('gaze_direction') or 'aucun',
                    'ai_available': True,
                }
            except requests.exceptions.HTTPError as e:
                last_error = e
                status_code = e.response.status_code if e.response is not None else None
                # 429 (rate limited) and 503 (momentarily overloaded) are
                # transient on Google's side — worth one quick retry.
                # Anything else (401 bad key, 400 bad request...) won't
                # succeed on retry, so fail fast instead of burning the
                # request budget (and holding the semaphore slot longer).
                if status_code not in (429, 503) or attempt == max_attempts - 1:
                    break
                time.sleep(1.0)
            except Exception as e:
                last_error = e
                break

        logger.warning('Gemini snapshot analysis failed after retries: %s', last_error)
        # Show a clean, non-technical message to the admin instead of the raw
        # exception (e.g. a Python traceback string) — the real error is still
        # logged above for debugging. Not marked suspicious: a transient outage
        # on Google's side isn't evidence of anything about the student.
        return _gemini_stub_result(
            "Analyse IA momentanément indisponible (service surchargé) — la prochaine capture réessaiera automatiquement."
        )
    finally:
        _gemini_semaphore.release()
