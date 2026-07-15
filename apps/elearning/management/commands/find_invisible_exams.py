"""
find_invisible_exams.py
────────────────────────
Diagnostic pour la panne "l'enseignant ne voit pas l'examen créé en admin".
SecureExam.class_obj/subject sont nullable (contrairement à Quiz/Assignment),
et TeacherScopedContentMixin.get_queryset() (apps/elearning/views.py) exige
un ClassSubjectTeacher actif correspondant pour que l'examen apparaisse côté
enseignant. Cette commande liste tout SecureExam qui restera invisible pour
n'importe quel enseignant, avec la raison précise.

Usage :
    python manage.py find_invisible_exams
"""

from django.core.management.base import BaseCommand

from apps.academic.models import ClassSubjectTeacher
from apps.elearning.models import SecureExam


class Command(BaseCommand):
    help = "Liste les SecureExam invisibles pour tout enseignant (class_obj/subject manquant ou sans ClassSubjectTeacher actif)."

    def handle(self, *args, **options):
        active_pairs = set(
            ClassSubjectTeacher.objects.filter(is_active=True).values_list('class_obj_id', 'subject_id')
        )

        exams = SecureExam.objects.all().order_by('-created_at')
        problems = []
        for exam in exams:
            if exam.class_obj_id is None or exam.subject_id is None:
                problems.append((exam, "classe et/ou matière non renseignée"))
            elif (exam.class_obj_id, exam.subject_id) not in active_pairs:
                problems.append((exam, "aucune assignation ClassSubjectTeacher active pour cette classe+matière"))

        if not problems:
            self.stdout.write(self.style.SUCCESS('Aucun examen invisible détecté.'))
            return

        self.stdout.write(f"{len(problems)} examen(s) invisible(s) pour tout enseignant :")
        for exam, reason in problems:
            sessions = exam.sessions.filter(status='SUBMITTED').count()
            self.stdout.write(
                f"  - #{exam.id} {exam.title!r} (classe={exam.class_obj_id}, matiere={exam.subject_id}) "
                f"— {reason} — {sessions} copie(s) soumise(s) en attente de correction"
            )
