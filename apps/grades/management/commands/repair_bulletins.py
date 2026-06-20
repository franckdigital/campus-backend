from django.core.management.base import BaseCommand
from apps.grades.models import ReportCard
from apps.grades.views import _compute_student_averages


class Command(BaseCommand):
    help = 'Recalcule et corrige subject_averages pour tous les bulletins existants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--site',
            type=str,
            help='Limiter à un site (code ou nom partiel)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les bulletins qui seraient corrigés sans modifier la base',
        )

    def handle(self, *args, **options):
        qs = ReportCard.objects.select_related(
            'student__user', 'class_group__site', 'semester'
        )
        if options['site']:
            qs = qs.filter(class_group__site__name__icontains=options['site'])

        total = qs.count()
        self.stdout.write(f'Bulletins trouvés : {total}')

        fixed = 0
        skipped = 0
        errors = 0

        for card in qs:
            try:
                global_avg, subject_map = _compute_student_averages(
                    card.student, card.class_group, card.semester
                )

                if not subject_map:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [SKIP] {card.student} — {card.class_group} S{card.semester}: '
                            f'aucune note trouvée'
                        )
                    )
                    skipped += 1
                    continue

                if options['dry_run']:
                    self.stdout.write(
                        f'  [DRY] {card.student} — {card.class_group}: '
                        f'{len(subject_map)} matières, moy={global_avg}'
                    )
                    fixed += 1
                    continue

                card.subject_averages = subject_map
                if global_avg is not None:
                    card.average = str(round(global_avg, 2))
                card.save(update_fields=['subject_averages', 'average'])
                fixed += 1

            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f'  [ERR] bulletin pk={card.pk}: {exc}')
                )
                errors += 1

        label = 'seraient corrigés' if options['dry_run'] else 'corrigés'
        self.stdout.write(
            self.style.SUCCESS(
                f'\nTerminé — {fixed} bulletins {label}, '
                f'{skipped} ignorés (sans notes), {errors} erreurs.'
            )
        )
