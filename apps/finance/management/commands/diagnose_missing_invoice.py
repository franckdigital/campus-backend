"""
Read-only diagnostic: a payment (e.g. PAY-2026-000023) references an invoice
by number (e.g. INV-ESCAM-CO-2026-00007) that never shows up in the admin
Finances > Factures list/search, even by searching that exact number. This
prints the invoice's raw DB state and replicates the admin list's queryset +
search filter to see exactly where it's being excluded.

Usage:
    python manage.py diagnose_missing_invoice --payment PAY-2026-000023
    python manage.py diagnose_missing_invoice --invoice-number INV-ESCAM-CO-2026-00007
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Diagnose why an invoice referenced by a payment doesn't appear in the admin invoice list/search."

    def add_arguments(self, parser):
        parser.add_argument('--payment', help='payment_number, e.g. PAY-2026-000023')
        parser.add_argument('--invoice-number', help='invoice_number, e.g. INV-ESCAM-CO-2026-00007')

    def handle(self, *args, **options):
        from apps.finance.models import Invoice, Payment
        from apps.finance.views import InvoiceViewSet

        if not options['payment'] and not options['invoice_number']:
            raise CommandError('Pass --payment or --invoice-number.')

        invoice = None
        if options['payment']:
            try:
                payment = Payment.objects.select_related('invoice').get(payment_number=options['payment'])
            except Payment.DoesNotExist:
                raise CommandError(f"Aucun paiement {options['payment']!r} trouvé.")
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== Paiement {payment.payment_number} ===\n'))
            self.stdout.write(f'  id={payment.id} status={payment.status} amount={payment.amount} invoice_id={payment.invoice_id}')
            invoice = payment.invoice
        else:
            invoice = Invoice.objects.filter(invoice_number=options['invoice_number']).first()
            if not invoice:
                raise CommandError(f"Aucune facture avec invoice_number={options['invoice_number']!r}.")

        self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== Facture {invoice.invoice_number} — état brut en DB ===\n'))
        self.stdout.write(f'  id={invoice.id}')
        self.stdout.write(f'  invoice_number={invoice.invoice_number!r}')
        self.stdout.write(f'  is_active={invoice.is_active}')
        self.stdout.write(f'  status={invoice.status}')
        self.stdout.write(f'  student_id={invoice.student_id} student={invoice.student}')
        self.stdout.write(f'  site_id={invoice.site_id} site={invoice.site}')
        self.stdout.write(f'  academic_year_id={invoice.academic_year_id} academic_year={invoice.academic_year}')
        self.stdout.write(f'  total={invoice.total} amount_paid={invoice.amount_paid} balance={invoice.balance}')
        self.stdout.write(f'  created_at={invoice.created_at}')

        # Are there duplicates sharing the same invoice_number (would break
        # uniqueness assumptions and confuse the frontend's key/search)?
        dupes = Invoice.objects.filter(invoice_number=invoice.invoice_number)
        self.stdout.write(f'\n  Nombre de factures partageant ce invoice_number: {dupes.count()}')
        for d in dupes:
            self.stdout.write(f'    - id={d.id} is_active={d.is_active} status={d.status} student_id={d.student_id}')

        # Replicate exactly what GET /invoices/?search=<numéro complet> does.
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Reproduction de la recherche admin (search=invoice_number) ===\n'))
        vs = InvoiceViewSet()
        base_qs = vs.queryset
        self.stdout.write(f'  Total factures dans le queryset de base (sans filtre): {base_qs.count()}')
        self.stdout.write(f'  Cette facture est-elle dans le queryset de base ? {base_qs.filter(pk=invoice.pk).exists()}')

        from rest_framework.filters import SearchFilter
        import re
        search_term = invoice.invoice_number
        # Manually apply the same icontains OR across search_fields DRF's
        # SearchFilter would build, without needing a real request/view.
        from django.db.models import Q
        q = Q()
        for field in vs.search_fields:
            q |= Q(**{f'{field}__icontains': search_term})
        matched = base_qs.filter(q)
        self.stdout.write(f'  search={search_term!r} -> {matched.count()} résultat(s), présent: {matched.filter(pk=invoice.pk).exists()}')

        # Also try just the trailing number, matching what a human would
        # likely type into the search box (e.g. "00007").
        short_term = invoice.invoice_number.split('-')[-1]
        q2 = Q()
        for field in vs.search_fields:
            q2 |= Q(**{f'{field}__icontains': short_term})
        matched2 = base_qs.filter(q2)
        self.stdout.write(f'  search={short_term!r} -> {matched2.count()} résultat(s), présent: {matched2.filter(pk=invoice.pk).exists()}')
