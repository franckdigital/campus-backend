"""
diagnose_teacher_scoping.py
─────────────────────────────
Diagnostic complémentaire à find_invisible_exams / backfill_class_subject_teacher :
le backfill n'a rien trouvé à créer alors que find_invisible_exams remonte 28
examens invisibles. Ce script affiche les chiffres bruts pour comprendre pourquoi
(ClassSubjectTeacher vide/mal peuplé ? Lesson/Assignment.teacher jamais renseigné ?
les couples classe+matière des examens ne correspondent à rien du tout ?).

Usage :
    python manage.py diagnose_teacher_scoping
"""

from django.core.management.base import BaseCommand

from apps.academic.models import ClassSubjectTeacher, TeacherProfile
from apps.elearning.models import Lesson, Assignment, Quiz, SecureExam


class Command(BaseCommand):
    help = "Affiche des compteurs bruts pour diagnostiquer le scoping enseignant (ClassSubjectTeacher, teacher FK, etc.)."

    def handle(self, *args, **options):
        self.stdout.write("=== Compteurs globaux ===")
        self.stdout.write(f"TeacherProfile: {TeacherProfile.objects.count()}")
        self.stdout.write(f"ClassSubjectTeacher (total): {ClassSubjectTeacher.objects.count()}")
        self.stdout.write(f"ClassSubjectTeacher (is_active=True): {ClassSubjectTeacher.objects.filter(is_active=True).count()}")

        self.stdout.write("")
        self.stdout.write("=== Champ teacher direct (Lesson / Assignment) ===")
        self.stdout.write(f"Lesson total: {Lesson.objects.count()} — avec teacher renseigné: {Lesson.objects.filter(teacher__isnull=False).count()}")
        self.stdout.write(f"Assignment total: {Assignment.objects.count()} — avec teacher renseigné: {Assignment.objects.filter(teacher__isnull=False).count()}")

        self.stdout.write("")
        self.stdout.write("=== Couples (classe, matière) utilisés par le contenu, vs ClassSubjectTeacher ===")
        active_pairs = set(ClassSubjectTeacher.objects.filter(is_active=True).values_list('class_obj_id', 'subject_id'))
        self.stdout.write(f"Couples actifs dans ClassSubjectTeacher: {len(active_pairs)}")

        for label, model in (('Quiz', Quiz), ('Assignment', Assignment), ('SecureExam', SecureExam)):
            pairs = set(
                model.objects.filter(class_obj__isnull=False, subject__isnull=False)
                .values_list('class_obj_id', 'subject_id')
            )
            matched = pairs & active_pairs
            self.stdout.write(f"{label}: {len(pairs)} couple(s) distinct(s) utilisé(s), {len(matched)} couvert(s) par ClassSubjectTeacher actif")

        self.stdout.write("")
        self.stdout.write("=== Détail ClassSubjectTeacher (max 30) ===")
        for cst in ClassSubjectTeacher.objects.select_related('teacher__user', 'class_obj', 'subject')[:30]:
            self.stdout.write(
                f"  id={cst.id} teacher={cst.teacher_id} ({getattr(cst.teacher.user, 'email', '?') if cst.teacher_id else '?'}) "
                f"class={cst.class_obj_id} ({getattr(cst.class_obj, 'code', '?') if cst.class_obj_id else '?'}) "
                f"subject={cst.subject_id} ({getattr(cst.subject, 'code', '?') if cst.subject_id else '?'}) "
                f"active={cst.is_active}"
            )

        self.stdout.write("")
        self.stdout.write("=== Détail des enseignants ===")
        for t in TeacherProfile.objects.select_related('user')[:30]:
            n = t.class_subjects.filter(is_active=True).count()
            self.stdout.write(f"  teacher_id={t.id} email={getattr(t.user, 'email', '?')} class_subjects_actifs={n}")
