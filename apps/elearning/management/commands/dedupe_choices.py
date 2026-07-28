from django.core.management.base import BaseCommand

from apps.elearning.models import Question


class Command(BaseCommand):
    help = (
        "One-time cleanup for QCM/QCU choices duplicated by the AI generator "
        "(ai_generate in views.py) before its token budget was fixed to scale "
        "with the requested question count. With too little budget for a large "
        "batch, the model degraded on later questions and repeated the same "
        "choice text several times within one question — the exam page showed "
        "them as separate, identical-looking options (e.g. 'Reserve aux societes "
        "de capitaux' appearing 4 times), confusing the candidate. Per question, "
        "keeps the first choice for each distinct (case-insensitive, trimmed) "
        "text and deletes the rest, preserving relative order."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Actually delete the duplicate choices (default is dry-run).',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        fixed_questions = 0
        deleted_choices = 0

        for question in Question.objects.all():
            choices = list(question.choices.order_by('order', 'created_at'))
            if len(choices) < 2:
                continue
            seen = set()
            duplicates = []
            for c in choices:
                key = (c.text or '').strip().lower()
                if key and key in seen:
                    duplicates.append(c)
                else:
                    seen.add(key)
            if not duplicates:
                continue
            fixed_questions += 1
            self.stdout.write(f"Question {question.id} ({question.text[:60]!r}): {len(duplicates)} doublon(s)")
            for c in duplicates:
                self.stdout.write(f"  - supprime: {c.text[:60]!r}")
                deleted_choices += 1
                if apply:
                    c.delete()

        if fixed_questions == 0:
            self.stdout.write(self.style.SUCCESS('Aucune question a corriger.'))
        elif apply:
            self.stdout.write(self.style.SUCCESS(f'{deleted_choices} choix en doublon supprime(s) sur {fixed_questions} question(s).'))
        else:
            self.stdout.write(self.style.WARNING(
                f'{deleted_choices} choix en doublon a supprimer sur {fixed_questions} question(s) — relancez avec --apply pour appliquer.'
            ))
