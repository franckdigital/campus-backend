"""
Read-only diagnostic: lists every FeeType row and how many InvoiceItems
reference each one — used to spot legacy/abbreviated codes (e.g. 'INSCR',
'SCOL') that don't match the 'inscri|regist' / 'tuition|scolarit' regexes
used everywhere (frontend computeFeeBreakdown/getInvoiceLabel, backend
financial_summary) to classify invoices as inscription vs scolarité.

Usage:
    python manage.py list_fee_types
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "List every FeeType and how many InvoiceItems use it, to spot legacy/abbreviated codes."

    def handle(self, *args, **options):
        from apps.finance.models import FeeType, InvoiceItem
        import re

        reg_re = re.compile(r'inscri|regist', re.I)
        tuition_re = re.compile(r'tuition|scolarit', re.I)

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== FeeType rows ===\n'))
        for ft in FeeType.objects.all().order_by('code'):
            count = InvoiceItem.objects.filter(fee_type=ft).count()
            matches_reg = bool(reg_re.search(ft.code))
            matches_tuition = bool(tuition_re.search(ft.code))
            flag = ''
            if not matches_reg and not matches_tuition:
                flag = '  <-- MATCHES NEITHER REGEX (invisible to inscription/scolarité classification)'
            self.stdout.write(
                f"  code={ft.code!r:20} name={ft.name!r:30} items={count:4} "
                f"matches_inscription_regex={matches_reg} matches_tuition_regex={matches_tuition}{flag}"
            )
