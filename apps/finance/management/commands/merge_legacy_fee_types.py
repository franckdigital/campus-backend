"""
Some invoices were created with abbreviated FeeType codes ('INSCR', 'SCOL')
instead of the canonical ones ('INSCRIPTION', 'SCOLARITE') used everywhere
else. Every inscription/scolarité classification in the app (frontend
computeFeeBreakdown/getInvoiceLabel, backend financial_summary) matches
fee_type codes against /inscri|regist/i and /tuition|scolarit/i — 'INSCR'
(missing the trailing "i") and 'SCOL' (too short) match NEITHER regex, so
invoices using them become invisible to every total/breakdown and silently
fall back to the configured barème amount instead of the real invoice data.

This re-points every InvoiceItem from the legacy FeeType onto the existing
canonical one (found by code), so all classification logic picks them up
retroactively — no money amounts change, only which FeeType each item
references. The now-unused legacy FeeType rows are left in place (just
orphaned) rather than deleted, in case anything else still references them.

Usage:
    python manage.py merge_legacy_fee_types              # dry-run
    python manage.py merge_legacy_fee_types --yes         # apply
"""
from django.core.management.base import BaseCommand

LEGACY_TO_CANONICAL = {
    'INSCR': 'INSCRIPTION',
    'SCOL': 'SCOLARITE',
}


class Command(BaseCommand):
    help = "Re-point InvoiceItems from legacy abbreviated FeeType codes (INSCR/SCOL) to the canonical ones."

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Apply the changes. Without this flag, dry-run only.')

    def handle(self, *args, **options):
        from apps.finance.models import FeeType, InvoiceItem

        confirm = options['yes']

        for legacy_code, canonical_code in LEGACY_TO_CANONICAL.items():
            legacy = FeeType.objects.filter(code=legacy_code).first()
            canonical = FeeType.objects.filter(code=canonical_code).first()

            self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {legacy_code} -> {canonical_code} ===\n'))
            if not legacy:
                self.stdout.write(f'  Aucun FeeType avec code={legacy_code!r} — rien à faire.')
                continue
            if not canonical:
                self.stdout.write(self.style.ERROR(
                    f'  Aucun FeeType canonique avec code={canonical_code!r} trouvé — impossible de fusionner automatiquement.'
                ))
                continue

            items = InvoiceItem.objects.filter(fee_type=legacy)
            self.stdout.write(f'  {items.count()} InvoiceItem(s) référencent {legacy_code!r} (id={legacy.id})')
            for it in items:
                self.stdout.write(f'    - item={it.id} invoice={it.invoice.invoice_number} description={it.description!r}')

            if confirm:
                updated = items.update(fee_type=canonical)
                self.stdout.write(self.style.SUCCESS(f'  -> {updated} item(s) repointé(s) vers {canonical_code!r} (id={canonical.id}).'))
            elif items.exists():
                self.stdout.write(self.style.WARNING('  Dry-run — relancez avec --yes pour appliquer.'))
