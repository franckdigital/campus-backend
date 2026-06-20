"""
clean_sites.py
Supprime les sites en doublon créés par plusieurs exécutions de seed_full.
Garde uniquement le site le plus récent pour chaque code officiel.

Codes officiels : ITA-MARC, ITA-PLAT, ITA-2PL, PIGIER, ISPA

Usage:
    python manage.py clean_sites           (dry-run, affiche ce qui serait supprimé)
    python manage.py clean_sites --apply   (applique réellement la suppression)
"""
from django.core.management.base import BaseCommand

OFFICIAL_CODES = ['ITA-MARC', 'ITA-PLAT', 'ITA-2PL', 'PIGIER', 'ISPA']

# Noms canoniques attendus pour chaque code
CANONICAL_NAMES = {
    'ITA-MARC': 'ITA Marcory',
    'ITA-PLAT': "Institut des Technologies d'Abidjan",
    'ITA-2PL':  'ITA 2 Plateaux',
    'PIGIER':   'PIGIER',
    'ISPA':     'ISPA',
}


class Command(BaseCommand):
    help = 'Nettoie les sites dupliqués (dry-run par défaut)'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Applique réellement la suppression')

    def handle(self, *args, **options):
        from apps.core.models import Site

        apply = options['apply']
        all_sites = list(Site.objects.order_by('created_at'))

        self.stdout.write(f'\nSites actuels en base ({len(all_sites)}) :')
        for s in all_sites:
            self.stdout.write(f'  [{s.code}] {s.name}  (id={s.id})')

        # ── 1. Dédoublonner par code ────────────────────────────
        to_delete_ids = []
        for code in OFFICIAL_CODES:
            same_code = [s for s in all_sites if s.code == code]
            if len(same_code) > 1:
                # garder le plus récent
                keeper = same_code[-1]
                dupes  = same_code[:-1]
                for d in dupes:
                    self.stdout.write(
                        self.style.WARNING(f'  DOUBLON code {code}: supprimer "{d.name}" (id={d.id})')
                    )
                    to_delete_ids.append(d.id)

        # ── 2. Supprimer les sites hors codes officiels ─────────
        extra = [s for s in all_sites if s.code not in OFFICIAL_CODES]
        for s in extra:
            self.stdout.write(
                self.style.WARNING(f'  EXTRA non-officiel: supprimer "{s.name}" [{s.code}] (id={s.id})')
            )
            to_delete_ids.append(s.id)

        if not to_delete_ids:
            self.stdout.write(self.style.SUCCESS('\nAucun doublon ni site extra. Base propre.'))
            return

        self.stdout.write(f'\n{len(to_delete_ids)} site(s) à supprimer.')

        if not apply:
            self.stdout.write(
                self.style.WARNING(
                    '\n[DRY-RUN] Aucune suppression effectuée. '
                    'Relancez avec --apply pour appliquer.'
                )
            )
            return

        # Suppression en cascade — Django gère les FK avec SET_NULL/CASCADE
        deleted, detail = Site.objects.filter(id__in=to_delete_ids).delete()
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ {deleted} objet(s) supprimé(s) : {detail}'
        ))

        # Vérification finale
        remaining = Site.objects.order_by('created_at')
        self.stdout.write(f'\nSites restants ({remaining.count()}) :')
        for s in remaining:
            self.stdout.write(f'  [{s.code}] {s.name}')
