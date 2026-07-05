"""
Recompute every invoice's subtotal/total/amount_paid/balance/status from its
real InvoiceItems and SUCCESS Payments — the same logic the on_payment_save
signal applies to a single invoice whenever a payment is saved (see
apps.finance.signals.on_payment_save), just run once across every invoice to
correct any historical drift (e.g. a payment corrected/deleted outside the
normal save() flow, or data touched by an older bug).

CANCELLED invoices are left untouched — they're already excluded from every
total/aggregate in the app, and recomputing could incorrectly resurrect their
status (e.g. back to PAID) from balance <= 0.

Usage:
    python manage.py recompute_invoice_totals             # dry-run, prints diffs
    python manage.py recompute_invoice_totals --yes        # apply
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum


class Command(BaseCommand):
    help = "Recompute amount_paid/balance/status for every non-cancelled invoice from real payments."

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes', action='store_true',
            help='Actually apply the corrections. Without this flag, only a dry-run diff is printed.'
        )

    def handle(self, *args, **options):
        from apps.finance.models import Invoice, Payment

        confirm = options['yes']
        invoices = Invoice.objects.filter(is_active=True).exclude(status='CANCELLED').prefetch_related('items', 'payments')

        changed = 0
        unchanged = 0

        for invoice in invoices:
            old_subtotal, old_total = invoice.subtotal, invoice.total
            old_paid, old_balance, old_status = invoice.amount_paid, invoice.balance, invoice.status

            total_success = (
                Payment.objects.filter(invoice=invoice, status='SUCCESS')
                .aggregate(total=Sum('amount'))['total'] or Decimal('0')
            )
            invoice.amount_paid = total_success
            invoice.calculate_totals()

            diff = (
                invoice.subtotal != old_subtotal or invoice.total != old_total or
                invoice.amount_paid != old_paid or invoice.balance != old_balance or
                invoice.status != old_status
            )
            if not diff:
                unchanged += 1
                continue

            changed += 1
            self.stdout.write(
                f'  {invoice.invoice_number} | '
                f'subtotal {old_subtotal}->{invoice.subtotal} | total {old_total}->{invoice.total} | '
                f'paid {old_paid}->{invoice.amount_paid} | balance {old_balance}->{invoice.balance} | '
                f'status {old_status}->{invoice.status}'
            )
            if confirm:
                with transaction.atomic():
                    invoice.save(update_fields=['subtotal', 'total', 'amount_paid', 'balance', 'status'])

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"Corrigé" if confirm else "À corriger (dry-run)"}: {changed} facture(s) | inchangées: {unchanged}'
        ))
        if not confirm and changed:
            self.stdout.write(self.style.WARNING('Dry-run uniquement — relancez avec --yes pour appliquer.'))
