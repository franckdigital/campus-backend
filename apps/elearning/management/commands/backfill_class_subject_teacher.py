"""
backfill_class_subject_teacher.py
──────────────────────────────────
Le 15/07/2026, TeacherScopedContentMixin (apps/elearning/views.py) a été
ajouté sur QuizViewSet/AssignmentViewSet/SecureExamViewSet/LessonViewSet/
VirtualLabViewSet pour restreindre chaque enseignant à ses propres classes
et matières. Il s'appuie exclusivement sur ClassSubjectTeacher (emploi du
temps) : si un enseignant n'a aucune ligne active dans cette table pour
une classe+matière donnée, get_queryset() renvoie .none() — même si cet
enseignant possède bel et bien des devoirs/quiz/examens sur cette
classe+matière (via Lesson.teacher ou Assignment.teacher). C'est ce qui
a rendu tout l'onglet "Corrections eLearning" vide pour les enseignants
dont l'emploi du temps n'était pas renseigné.

Cette commande reconstruit les lignes ClassSubjectTeacher manquantes à
partir des couples (class_obj, subject, teacher) réellement utilisés
dans Lesson et Assignment (les deux seuls modèles qui portent un FK
`teacher` direct) — la source de vérité la plus fiable de "qui enseigne
quoi à qui" disponible dans les données existantes.

Usage :
    python manage.py backfill_class_subject_teacher --dry-run   # affiche sans corriger
    python manage.py backfill_class_subject_teacher             # corrige
"""

from django.core.management.base import BaseCommand

from apps.academic.models import ClassSubjectTeacher
from apps.elearning.models import Lesson, Assignment


class Command(BaseCommand):
    help = "Recrée les ClassSubjectTeacher manquants à partir des Lesson/Assignment existants."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Affiche les lignes à créer sans les créer.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        wanted = set()
        for model in (Lesson, Assignment):
            triples = model.objects.filter(
                teacher__isnull=False, class_obj__isnull=False, subject__isnull=False
            ).values_list('class_obj_id', 'subject_id', 'teacher_id').distinct()
            wanted.update(triples)

        # (class_obj, subject) is unique in ClassSubjectTeacher — one teacher
        # per class+subject — so index existing rows by that pair, not by
        # the full triple, to correctly detect conflicts vs. simple gaps.
        existing_by_pair = {
            (row['class_obj_id'], row['subject_id']): row
            for row in ClassSubjectTeacher.objects.values('class_obj_id', 'subject_id', 'teacher_id', 'is_active')
        }

        to_create, to_reactivate, conflicts = [], [], []
        for class_id, subject_id, teacher_id in sorted(wanted):
            row = existing_by_pair.get((class_id, subject_id))
            if row is None:
                to_create.append((class_id, subject_id, teacher_id))
            elif row['teacher_id'] == teacher_id:
                if not row['is_active']:
                    to_reactivate.append((class_id, subject_id, teacher_id))
            else:
                conflicts.append((class_id, subject_id, teacher_id, row['teacher_id']))

        if not to_create and not to_reactivate and not conflicts:
            self.stdout.write(self.style.SUCCESS('Aucune assignation manquante.'))
            return

        for class_id, subject_id, teacher_id in to_create:
            self.stdout.write(f"  + creer classe={class_id} matiere={subject_id} enseignant={teacher_id}")
            if not dry_run:
                ClassSubjectTeacher.objects.create(
                    class_obj_id=class_id, subject_id=subject_id, teacher_id=teacher_id, is_active=True,
                )

        for class_id, subject_id, teacher_id in to_reactivate:
            self.stdout.write(f"  ~ reactiver classe={class_id} matiere={subject_id} enseignant={teacher_id}")
            if not dry_run:
                ClassSubjectTeacher.objects.filter(
                    class_obj_id=class_id, subject_id=subject_id, teacher_id=teacher_id,
                ).update(is_active=True)

        for class_id, subject_id, teacher_id, other_teacher_id in conflicts:
            self.stdout.write(self.style.ERROR(
                f"  ! conflit classe={class_id} matiere={subject_id}: Lesson/Assignment.teacher={teacher_id} "
                f"mais ClassSubjectTeacher existant pointe vers enseignant={other_teacher_id} — non modifié, a verifier manuellement."
            ))

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run : aucune modification appliquée.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'{len(to_create)} créée(s), {len(to_reactivate)} réactivée(s), {len(conflicts)} conflit(s) à vérifier manuellement.'
            ))
