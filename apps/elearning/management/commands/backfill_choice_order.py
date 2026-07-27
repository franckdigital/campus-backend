from django.core.management.base import BaseCommand

from apps.elearning.models import Question, Choice


class Command(BaseCommand):
    help = (
        "One-time fix for QCM choices saved before the frontend sent an explicit "
        "`order` (ExamManager.jsx's exam builder never did, unlike QuizManager.jsx) "
        "— every choice ended up with order=0, so Choice.Meta.ordering = "
        "['question', 'order'] fell back to an arbitrary DB order, showing choices "
        "in a different order than the teacher typed them (and shifting between "
        "reloads) even though grading itself (by choice id) stayed correct. "
        "Reassigns order=0,1,2... per question, by created_at (creation sequence)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Actually save the corrected order (default is dry-run).',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        fixed_questions = 0
        fixed_choices = 0

        for question in Question.objects.all():
            choices = list(question.choices.order_by('created_at'))
            if not choices:
                continue
            # Already correctly ordered (0,1,2...) — nothing to do.
            if [c.order for c in choices] == list(range(len(choices))):
                continue
            fixed_questions += 1
            self.stdout.write(f"Question {question.id} ({question.text[:60]!r}): {len(choices)} choix")
            for i, c in enumerate(choices):
                if c.order != i:
                    self.stdout.write(f"  - order {c.order} -> {i}: {c.text[:60]!r}")
                    fixed_choices += 1
                    if apply:
                        c.order = i
                        c.save(update_fields=['order'])

        if fixed_questions == 0:
            self.stdout.write(self.style.SUCCESS('Aucune question a corriger.'))
        elif apply:
            self.stdout.write(self.style.SUCCESS(f'{fixed_choices} choix corrige(s) sur {fixed_questions} question(s).'))
        else:
            self.stdout.write(self.style.WARNING(
                f'{fixed_choices} choix a corriger sur {fixed_questions} question(s) — relancez avec --apply pour appliquer.'
            ))
