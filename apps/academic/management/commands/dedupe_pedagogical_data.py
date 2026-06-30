from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        'Merge duplicate Filières (Program) and Niveaux (Level) created by the '
        '"Créer nouveau" inline-create flow, which used to create a new row '
        'every time even when one with the same name already existed. '
        'For each duplicate group, keeps the oldest record and reassigns '
        'Levels/Classes pointing to the duplicates onto the canonical one, '
        'then deletes the duplicates.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be merged/deleted without changing the database.',
        )

    def handle(self, *args, **options):
        from apps.academic.models import Program, Level

        dry_run = options['dry_run']
        self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved') if dry_run
                           else self.style.WARNING('LIVE RUN — changes will be saved'))

        with transaction.atomic():
            programs_merged, levels_merged = self._dedupe(Program, Level, dry_run)
            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Programs merged: {programs_merged} | Levels merged: {levels_merged}'
        ))

    def _dedupe(self, Program, Level, dry_run):
        programs_merged = 0
        levels_merged = 0

        # ── 1. Merge duplicate Programs: same site + same name (case-insensitive) ──
        groups = defaultdict(list)
        for p in Program.objects.order_by('created_at'):
            groups[(p.site_id, p.name.strip().lower())].append(p)

        for (site_id, name), progs in groups.items():
            if len(progs) <= 1:
                continue
            canonical, dups = progs[0], progs[1:]
            self.stdout.write(
                f'Programme "{name}" (site={site_id}): garde {canonical.code}, '
                f'fusionne {[d.code for d in dups]}'
            )
            for dup in dups:
                moved = Level.objects.filter(program=dup).update(program=canonical)
                self.stdout.write(f'  -> {moved} niveau(x) déplacé(s) de {dup.code} vers {canonical.code}')
                if not dry_run:
                    dup.delete()
                programs_merged += 1

        # ── 2. Merge duplicate Levels: same program + same name (case-insensitive) ──
        groups = defaultdict(list)
        for lvl in Level.objects.select_related('program').order_by('created_at'):
            groups[(lvl.program_id, lvl.name.strip().lower())].append(lvl)

        for (program_id, name), lvls in groups.items():
            if len(lvls) <= 1:
                continue
            canonical, dups = lvls[0], lvls[1:]
            self.stdout.write(
                f'Niveau "{name}" (programme={program_id}): garde {canonical.code}, '
                f'fusionne {[d.code for d in dups]}'
            )
            for dup in dups:
                from apps.academic.models import Class, LevelSubject

                moved = Class.objects.filter(level=dup).update(level=canonical)
                self.stdout.write(f'  -> {moved} classe(s) déplacée(s) de {dup.code} vers {canonical.code}')

                # LevelSubject has a unique_together=['level', 'subject'] constraint, so a
                # straight bulk update could collide if the canonical level already has the
                # same subject attached — reassign row by row and drop true duplicates.
                existing_subject_ids = set(
                    LevelSubject.objects.filter(level=canonical).values_list('subject_id', flat=True)
                )
                for ls in LevelSubject.objects.filter(level=dup):
                    if ls.subject_id in existing_subject_ids:
                        ls.delete()
                    else:
                        ls.level = canonical
                        ls.save(update_fields=['level'])
                        existing_subject_ids.add(ls.subject_id)

                if not dry_run:
                    dup.delete()
                levels_merged += 1

        return programs_merged, levels_merged
