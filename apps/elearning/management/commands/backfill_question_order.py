from django.core.management.base import BaseCommand

from apps.elearning.models import Quiz, Question


class Command(BaseCommand):
    help = (
        "One-time fix for exam/quiz questions saved before the frontend sent an "
        "explicit `order` — every question ended up with order=0, so Question.Meta "
        ".ordering = ['quiz', 'order'] fell back to an arbitrary DB order (not "
        "creation order), showing e.g. 'Question 2' under the 'Question 1/2' badge. "
        "Reassigns order=0,1,2... per quiz, by created_at (creation sequence)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Actually save the corrected order (default is dry-run).',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        fixed_quizzes = 0
        fixed_questions = 0

        for quiz in Quiz.objects.all():
            questions = list(quiz.questions.order_by('created_at'))
            if not questions:
                continue
            # Already correctly ordered (0,1,2...) — nothing to do.
            if [q.order for q in questions] == list(range(len(questions))):
                continue
            fixed_quizzes += 1
            self.stdout.write(f"Quiz {quiz.id} ({quiz.title or 'sans titre'}): {len(questions)} question(s)")
            for i, q in enumerate(questions):
                if q.order != i:
                    self.stdout.write(f"  - order {q.order} -> {i}: {q.text[:60]!r}")
                    fixed_questions += 1
                    if apply:
                        q.order = i
                        q.save(update_fields=['order'])

        if fixed_quizzes == 0:
            self.stdout.write(self.style.SUCCESS('Aucun quiz a corriger.'))
        elif apply:
            self.stdout.write(self.style.SUCCESS(f'{fixed_questions} question(s) corrigee(s) sur {fixed_quizzes} quiz.'))
        else:
            self.stdout.write(self.style.WARNING(
                f'{fixed_questions} question(s) a corriger sur {fixed_quizzes} quiz — relancez avec --apply pour appliquer.'
            ))
