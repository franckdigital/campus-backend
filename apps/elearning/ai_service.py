"""
Proxy service to Anthropic Claude API for e-learning AI features (Lots 15/16/17).
Falls back to a stub response if ANTHROPIC_API_KEY is not configured.
"""
import json
from django.conf import settings

ANTHROPIC_API_KEY = getattr(settings, 'ANTHROPIC_API_KEY', '')
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', '')
GEMINI_VISION_MODEL = getattr(settings, 'GEMINI_VISION_MODEL', 'gemini-2.0-flash')


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
    }


def analyze_exam_snapshot(image_bytes: bytes) -> dict:
    """Proctoring — Gemini vision analysis of one exam webcam snapshot.

    Unlike the boolean-only client-side TensorFlow.js detection, this asks a
    real vision model to describe in plain French exactly what it observes
    (talking to someone off-camera, looking at a phone, a second person in
    frame...), not just "phone: yes/no". Returns a dict always shaped the
    same way — including a 'description' string suitable for direct display
    next to the snapshot in the admin review screen — so callers never need
    to special-case a missing/failed analysis.

    Falls back to a neutral stub (no flags raised) if GEMINI_API_KEY isn't
    configured or the call fails, so proctoring degrades gracefully instead
    of crashing when the free-tier key is absent or rate-limited.
    """
    if not GEMINI_API_KEY:
        return _gemini_stub_result("Analyse IA indisponible (GEMINI_API_KEY non configurée).")

    import base64
    import requests

    img_b64 = base64.b64encode(image_bytes).decode()
    prompt = (
        "Tu es un système de surveillance d'examen en ligne. Regarde cette capture webcam "
        "d'un(e) étudiant(e) en train de composer et décris EXACTEMENT ce que tu observes, "
        "en une phrase courte et factuelle en français. Sois précis et concret, par exemple : "
        "\"L'étudiant regarde son téléphone posé à côté du clavier\", \"Une deuxième personne "
        "est visible derrière l'étudiant\", \"L'étudiant semble parler à quelqu'un hors champ\", "
        "\"L'étudiant tient un téléphone devant son visage\", \"Aucune anomalie, l'étudiant "
        "regarde son écran normalement\". Réponds uniquement avec un objet JSON strict : "
        "{\"description\": string (la phrase en français), \"face_detected\": bool, "
        "\"phone_detected\": bool, \"multiple_faces\": bool, \"suspicious\": bool "
        "(true si le comportement observé est suspect pour un examen surveillé)}."
    )
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
                    'temperature': 0.2,
                    'responseMimeType': 'application/json',
                    'maxOutputTokens': 500,
                    # Newer Gemini models spend part of the output token
                    # budget on hidden "thinking" tokens by default — for a
                    # one-sentence classification task that just silently
                    # truncates the actual JSON answer before it's written.
                    'thinkingConfig': {'thinkingBudget': 0},
                },
            },
            timeout=20,
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
        }
    except Exception as e:
        return _gemini_stub_result(f"[Erreur analyse IA : {e}]")
