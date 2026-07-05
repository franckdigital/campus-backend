"""
Student KPI computation + AI-generated performance analysis.

KPIs (attendance, punctuality, grades, trend, class comparison) are plain
DB aggregations, recomputed on every request — cheap. Only the AI narrative
is expensive (LLM call via apps.elearning.ai_service._call_claude, the only
Claude integration point in this codebase) and is cached on
StudentKPIAnalysis, regenerated only when there's no cached analysis for the
semester yet, or when an admin explicitly asks for a refresh.
"""
import json
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg
from django.utils import timezone

from .models import StudentKPIAnalysis

REFRESH_COOLDOWN = timedelta(minutes=5)

RISK_WEIGHTS = {
    'academic': 0.40,
    'attendance': 0.25,
    'punctuality': 0.15,
    'trend': 0.20,
}


def _get_current_class(student, semester):
    from apps.academic.models import Enrollment
    enr = Enrollment.objects.filter(
        student=student, academic_year=semester.academic_year,
        status='ENROLLED', is_active=True,
    ).select_related('class_obj').first()
    return enr.class_obj if enr else None


def compute_attendance_kpis(student, semester):
    from apps.attendance.models import AttendanceRecord

    qs = AttendanceRecord.objects.filter(
        student=student,
        attendance_session__date__gte=semester.start_date,
        attendance_session__date__lte=semester.end_date,
    )
    total = qs.count()
    present = qs.filter(status='PRESENT').count()
    late = qs.filter(status='LATE').count()
    absent = qs.filter(status='ABSENT').count()
    excused = qs.filter(status='EXCUSED').count()
    # EXCUSED absences are neither penalized nor counted as attendance —
    # they're outside the student's control (justified leave).
    countable = total - excused

    attendance_rate = round((present + late) / countable * 100, 1) if countable > 0 else None
    late_rate = round(late / countable * 100, 1) if countable > 0 else None

    return {
        'total_sessions': total,
        'present_count': present,
        'absent_count': absent,
        'late_count': late,
        'excused_count': excused,
        'attendance_rate': attendance_rate,
        'late_rate': late_rate,
    }


def compute_academic_kpis(student, class_group, semester):
    from apps.grades.models import ReportCard
    from apps.grades.views import _compute_student_averages

    if not class_group:
        return {
            'grade_global_average': None, 'subject_averages': [],
            'weak_subjects': [], 'rank': None, 'total_students': None,
        }

    rc = ReportCard.objects.filter(
        student=student, class_group=class_group, semester=semester,
    ).first()

    if rc and rc.average is not None:
        avg = float(rc.average)
        rank, total_students = rc.rank, rc.total_students
        subject_averages = [
            {
                'subject_id': s.get('subject_id'),
                'subject_name': s.get('subject_name'),
                'coefficient': s.get('coefficient'),
                'average': s.get('average'),
                'grade_count': len(s.get('grades', [])),
            }
            for s in (rc.subject_averages or {}).values()
        ]
    else:
        avg_decimal, subject_map = _compute_student_averages(student, class_group, semester)
        avg = float(avg_decimal) if avg_decimal else None
        rank, total_students = None, None
        subject_averages = [
            {
                'subject_id': s['subject_id'],
                'subject_name': s['subject_name'],
                'coefficient': s['coefficient'],
                'average': s['average'],
                'grade_count': len(s['grades']),
            }
            for s in subject_map.values()
        ]

    weak_subjects = sorted(
        [s for s in subject_averages if s.get('average') is not None and s['average'] < 10],
        key=lambda s: s['average'],
    )[:3]

    return {
        'grade_global_average': avg,
        'subject_averages': subject_averages,
        'weak_subjects': weak_subjects,
        'rank': rank,
        'total_students': total_students,
    }


def get_semester_history(student, semester, limit=4):
    """Chronological averages for the student's last `limit` semesters
    (including the current one), using ReportCard when available and
    falling back to a live computation otherwise. Also returns the class
    average/rank for the current semester for comparison."""
    from apps.academic.models import Semester
    from apps.grades.models import ReportCard

    # Semester.start_date already orders semesters chronologically across
    # academic years — no need to compare academic_year FKs directly.
    past_semesters = list(
        Semester.objects.filter(
            start_date__lte=semester.start_date,
        ).order_by('-start_date')[:limit]
    )
    past_semesters.reverse()  # chronological order, oldest first

    history = []
    for sem in past_semesters:
        class_group = _get_current_class(student, sem)
        avg = None
        rank = None
        total_students = None
        if class_group:
            rc = ReportCard.objects.filter(
                student=student, class_group=class_group, semester=sem,
            ).first()
            if rc and rc.average is not None:
                avg = float(rc.average)
                rank, total_students = rc.rank, rc.total_students
            else:
                from apps.grades.views import _compute_student_averages
                avg_decimal, _ = _compute_student_averages(student, class_group, sem)
                avg = float(avg_decimal) if avg_decimal else None
        history.append({
            'semester_id': sem.id,
            'semester_label': sem.label or sem.name,
            'average': avg,
            'rank': rank,
            'total_students': total_students,
        })

    delta_vs_previous = None
    if len(history) >= 2 and history[-1]['average'] is not None and history[-2]['average'] is not None:
        delta_vs_previous = round(history[-1]['average'] - history[-2]['average'], 2)

    # Class comparison for the current semester
    class_group = _get_current_class(student, semester)
    class_average = None
    class_rank = None
    class_total_students = None
    if class_group:
        agg = ReportCard.objects.filter(
            class_group=class_group, semester=semester, average__isnull=False,
        ).aggregate(avg=Avg('average'))
        class_average = round(float(agg['avg']), 2) if agg['avg'] is not None else None
        my_card = ReportCard.objects.filter(
            student=student, class_group=class_group, semester=semester,
        ).first()
        if my_card:
            class_rank, class_total_students = my_card.rank, my_card.total_students

    return {
        'history': history,
        'delta_vs_previous': delta_vs_previous,
        'class_average': class_average,
        'class_rank': class_rank,
        'class_total_students': class_total_students,
    }


def _clamp(value, lo=0, hi=100):
    return max(lo, min(hi, value))


def compute_risk_score(academic_kpis, attendance_kpis, trend):
    """Explainable weighted risk formula — every component/weight/threshold
    is plain arithmetic on already-computed KPIs, nothing derived from the
    LLM. Returns (score, level, components)."""
    avg = academic_kpis['grade_global_average']
    academic_component = (avg / 20) * 100 if avg is not None else 50

    attendance_rate = attendance_kpis['attendance_rate']
    attendance_component = attendance_rate if attendance_rate is not None else 70

    late_rate = attendance_kpis['late_rate']
    punctuality_component = (100 - late_rate) if late_rate is not None else 100

    delta = trend['delta_vs_previous']
    trend_component = _clamp(50 + delta * 10) if delta is not None else 50

    performance_score = (
        RISK_WEIGHTS['academic'] * academic_component
        + RISK_WEIGHTS['attendance'] * attendance_component
        + RISK_WEIGHTS['punctuality'] * punctuality_component
        + RISK_WEIGHTS['trend'] * trend_component
    )
    risk_score = round(_clamp(100 - performance_score))

    if risk_score < 30:
        risk_level = 'LOW'
    elif risk_score < 60:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'HIGH'

    components = {
        'academic': round(academic_component, 1),
        'attendance': round(attendance_component, 1),
        'punctuality': round(punctuality_component, 1),
        'trend': round(trend_component, 1),
    }
    return risk_score, risk_level, components


def compute_student_kpis(student, semester):
    class_group = _get_current_class(student, semester)
    attendance = compute_attendance_kpis(student, semester)
    academic = compute_academic_kpis(student, class_group, semester)
    trend = get_semester_history(student, semester)
    risk_score, risk_level, risk_components = compute_risk_score(academic, attendance, trend)

    return {
        'kpis': {**attendance, **{k: v for k, v in academic.items() if k not in ('rank', 'total_students')}},
        'trend': trend,
        'risk': {
            'score': risk_score,
            'level': risk_level,
            'components': risk_components,
            'weights': RISK_WEIGHTS,
        },
    }


AI_SYSTEM_PROMPT = (
    "Tu es un conseiller pédagogique expert. Tu reçois des données chiffrées "
    "déjà calculées sur un étudiant (assiduité, ponctualité, moyennes par "
    "matière, tendance, score de risque). Rédige, en français, une analyse "
    "en texte brut : PAS de Markdown, pas d'astérisques, pas de dièses — "
    "utilise des lignes vides et des tirets '-' pour les listes, le texte "
    "est affiché tel quel sans moteur de rendu. Structure obligatoire avec "
    "ces intitulés exacts en majuscules suivis de deux-points, chacun sur sa "
    "propre ligne : SYNTHÈSE:, POINTS FORTS:, MATIÈRES À RENFORCER:, "
    "CONSEILS DE MÉTHODE DE TRAVAIL:, EXPLICATION DU RISQUE:. "
    "Règle absolue : n'utilise QUE les chiffres, noms de matières et valeurs "
    "fournis dans les données ; n'invente jamais une note, une date ou une "
    "matière absente des données. Si une donnée manque, dis-le explicitement "
    "plutôt que de l'estimer. Sois concret et actionnable."
)


def generate_ai_analysis(kpi_payload):
    from apps.elearning.ai_service import _call_claude

    message = (
        "Voici les données factuelles de l'étudiant (utilise-les telles "
        "quelles, sans en inventer d'autres) :\n\n"
        + json.dumps(kpi_payload, ensure_ascii=False, indent=2, default=str)
    )
    return _call_claude(AI_SYSTEM_PROMPT, [{'role': 'user', 'content': message}], max_tokens=1500)


def get_or_generate_analysis(student, semester=None, refresh=False):
    from apps.academic.models import Semester

    if semester is None:
        semester = Semester.objects.filter(is_current=True).first()
    if semester is None:
        return {
            'student_id': str(student.id), 'semester': None,
            'kpis': None, 'trend': None, 'risk': None,
            'ai_summary': '', 'ai_generated_at': None, 'ai_tokens_used': 0,
            'has_ai_analysis': False,
        }

    computed = compute_student_kpis(student, semester)

    analysis, _ = StudentKPIAnalysis.objects.get_or_create(
        student=student, semester=semester,
    )

    on_cooldown = (
        analysis.generated_at is not None
        and timezone.now() - analysis.generated_at < REFRESH_COOLDOWN
    )
    should_generate = not analysis.generated_at or (refresh and not on_cooldown)

    if should_generate:
        text, tokens = generate_ai_analysis(computed)
        analysis.ai_summary = text
        analysis.ai_tokens_used = tokens
        analysis.generated_at = timezone.now()

    analysis.risk_score = computed['risk']['score']
    analysis.risk_level = computed['risk']['level']
    analysis.kpi_snapshot = computed
    analysis.save(update_fields=[
        'risk_score', 'risk_level', 'kpi_snapshot',
        'ai_summary', 'ai_tokens_used', 'generated_at', 'updated_at',
    ])

    return {
        'student_id': str(student.id),
        'semester': {
            'id': semester.id,
            'label': semester.label or semester.name,
            'academic_year': semester.academic_year.name,
        },
        'kpis': computed['kpis'],
        'trend': computed['trend'],
        'risk': computed['risk'],
        'ai_summary': analysis.ai_summary,
        'ai_generated_at': analysis.generated_at,
        'ai_tokens_used': analysis.ai_tokens_used,
        'has_ai_analysis': bool(analysis.generated_at),
    }
