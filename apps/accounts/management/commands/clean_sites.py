"""
clean_sites.py — Supprime les sites dupliqués ou hors codes officiels.

Usage:
    python manage.py clean_sites           # dry-run (affiche sans supprimer)
    python manage.py clean_sites --apply   # supprime réellement
"""
from django.core.management.base import BaseCommand

OFFICIAL_CODES = ['ITA-MARC', 'ITA-PLAT', 'ITA-2PL', 'PIGIER', 'ISPA']


class Command(BaseCommand):
    help = 'Nettoie les sites dupliqués (dry-run par défaut, --apply pour exécuter)'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Applique réellement la suppression')

    def handle(self, *args, **options):
        from apps.core.models import Site

        apply = options['apply']
        all_sites = list(Site.objects.order_by('created_at'))

        self.stdout.write(f'\nSites actuels en base ({len(all_sites)}) :')
        for s in all_sites:
            self.stdout.write(f'  [{s.code:10}] {s.name}')

        to_delete_ids = []

        # 1. Doublons de même code (garder le plus récent)
        for code in OFFICIAL_CODES:
            same_code = [s for s in all_sites if s.code == code]
            if len(same_code) > 1:
                for dupe in same_code[:-1]:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  DOUBLON [{code}] → supprimer "{dupe.name}" (id={dupe.id})'
                        )
                    )
                    to_delete_ids.append(dupe.id)

        # 2. Sites hors codes officiels
        extras = [s for s in all_sites if s.code not in OFFICIAL_CODES]
        for s in extras:
            self.stdout.write(
                self.style.WARNING(
                    f'  EXTRA [{s.code}] → supprimer "{s.name}" (id={s.id})'
                )
            )
            to_delete_ids.append(s.id)

        if not to_delete_ids:
            self.stdout.write(self.style.SUCCESS('\nAucun doublon. Base propre.'))
            return

        self.stdout.write(f'\n{len(to_delete_ids)} site(s) à supprimer.')

        if not apply:
            self.stdout.write(
                self.style.WARNING(
                    'Dry-run — aucune suppression. '
                    'Relancez avec --apply pour appliquer.'
                )
            )
            return

        deleted, detail = Site.objects.filter(id__in=to_delete_ids).delete()
        self.stdout.write(self.style.SUCCESS(f'\n✓ {deleted} objet(s) supprimé(s) : {detail}'))

        remaining = list(Site.objects.order_by('created_at'))
        self.stdout.write(f'\nSites restants ({len(remaining)}) :')
        for s in remaining:
            self.stdout.write(self.style.SUCCESS(f'  [{s.code:10}] {s.name}'))
