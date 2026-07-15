"""
diagnose_teacher.py
─────────────────────
Diagnostic ciblé pour un enseignant précis : montre ses assignations
ClassSubjectTeacher actuelles, son site/école, et — pour comparaison —
les classes/matières de son site qui n'ont encore aucune assignation
active pour aucun enseignant (candidates probables pour compléter son
emploi du temps si c'est lui qui est censé les enseigner).

Usage :
    python manage.py diagnose_teacher --email k.aristide@escam.net
"""

from django.core.management.base import BaseCommand, CommandError

from apps.academic.models import ClassSubjectTeacher, TeacherProfile, Class, Subject
from apps.elearning.models import SecureExam, Quiz, Assignment


class Command(BaseCommand):
    help = "Diagnostic ClassSubjectTeacher / site pour un enseignant donné."

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help="Email du compte enseignant.")

    def handle(self, *args, **options):
        email = options['email']
        try:
            teacher = TeacherProfile.objects.select_related('user').get(user__email=email)
        except TeacherProfile.DoesNotExist:
            raise CommandError(f"Aucun TeacherProfile pour l'email {email!r}")

        self.stdout.write(f"TeacherProfile: id={teacher.id} email={email}")

        self.stdout.write("")
        self.stdout.write("=== Assignations ClassSubjectTeacher actuelles ===")
        assignments = ClassSubjectTeacher.objects.filter(teacher=teacher).select_related('class_obj', 'subject')
        for a in assignments:
            self.stdout.write(f"  class={a.class_obj_id} ({a.class_obj.code}, site={a.class_obj.site_id}) subject={a.subject_id} ({a.subject.code}) active={a.is_active}")
        if not assignments:
            self.stdout.write("  (aucune)")

        site_ids = set(assignments.values_list('class_obj__site_id', flat=True))
        if not site_ids:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Aucune assignation existante : impossible de déduire le site/école automatiquement."))
            return

        self.stdout.write("")
        self.stdout.write(f"=== Classes du même site ({site_ids}) ===")
        classes = Class.objects.filter(site_id__in=site_ids)
        class_ids = list(classes.values_list('id', flat=True))
        for c in classes:
            self.stdout.write(f"  class={c.id} code={c.code} name={c.name}")

        self.stdout.write("")
        self.stdout.write("=== Couples (classe de ce site, matière) utilisés par SecureExam/Quiz/Assignment mais SANS ClassSubjectTeacher actif ===")
        active_pairs = set(ClassSubjectTeacher.objects.filter(is_active=True).values_list('class_obj_id', 'subject_id'))
        for label, model in (('SecureExam', SecureExam), ('Quiz', Quiz), ('Assignment', Assignment)):
            pairs = set(
                model.objects.filter(class_obj_id__in=class_ids, subject__isnull=False)
                .values_list('class_obj_id', 'subject_id')
            )
            missing = pairs - active_pairs
            for class_id, subject_id in missing:
                subj = Subject.objects.filter(id=subject_id).first()
                cls = classes.filter(id=class_id).first()
                self.stdout.write(f"  [{label}] class={class_id} ({cls.code if cls else '?'}) subject={subject_id} ({subj.code if subj else '?'})")
