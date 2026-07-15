"""
assign_teacher_site_gaps.py
─────────────────────────────
Pour un enseignant donné, trouve tous les couples (classe, matière) de son
site qui sont utilisés par du contenu (SecureExam/Quiz/Assignment/Lesson)
mais n'ont AUCUNE assignation ClassSubjectTeacher active pour personne, et
les assigne à cet enseignant. N'écrase jamais un couple déjà assigné à un
autre enseignant (ClassSubjectTeacher a unique_together=['class_obj', 'subject'],
un seul enseignant par couple) — ces couples-là sont juste listés en conflit.

Usage :
    python manage.py assign_teacher_site_gaps --email k.aristide@escam.net --dry-run
    python manage.py assign_teacher_site_gaps --email k.aristide@escam.net
"""

from django.core.management.base import BaseCommand, CommandError

from apps.academic.models import ClassSubjectTeacher, TeacherProfile, Class
from apps.elearning.models import SecureExam, Quiz, Assignment, Lesson


class Command(BaseCommand):
    help = "Comble les trous ClassSubjectTeacher (sans assignation du tout) sur le site d'un enseignant, en les lui assignant."

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help="Email du compte enseignant.")
        parser.add_argument('--dry-run', action='store_true', help="Affiche sans modifier.")

    def handle(self, *args, **options):
        email = options['email']
        dry_run = options['dry_run']
        try:
            teacher = TeacherProfile.objects.select_related('user').get(user__email=email)
        except TeacherProfile.DoesNotExist:
            raise CommandError(f"Aucun TeacherProfile pour l'email {email!r}")

        site_ids = set(
            ClassSubjectTeacher.objects.filter(teacher=teacher).values_list('class_obj__site_id', flat=True)
        )
        if not site_ids:
            raise CommandError("Cet enseignant n'a aucune assignation existante : impossible de déduire son site.")

        class_ids = list(Class.objects.filter(site_id__in=site_ids).values_list('id', flat=True))
        active_pairs = set(ClassSubjectTeacher.objects.values_list('class_obj_id', 'subject_id'))  # tout couple déjà pris, actif ou non

        gaps = set()
        for model in (SecureExam, Quiz, Assignment, Lesson):
            pairs = set(
                model.objects.filter(class_obj_id__in=class_ids, subject__isnull=False)
                .values_list('class_obj_id', 'subject_id')
            )
            gaps.update(pairs - active_pairs)

        if not gaps:
            self.stdout.write(self.style.SUCCESS("Aucun trou à combler sur le site de cet enseignant."))
            return

        self.stdout.write(f"{len(gaps)} couple(s) (classe, matière) sans assignation à combler pour {email} :")
        for class_id, subject_id in sorted(gaps):
            self.stdout.write(f"  + class={class_id} subject={subject_id}")
            if not dry_run:
                ClassSubjectTeacher.objects.create(
                    class_obj_id=class_id, subject_id=subject_id, teacher=teacher, is_active=True,
                )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run : aucune modification appliquée."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{len(gaps)} assignation(s) créée(s) pour {email}."))
