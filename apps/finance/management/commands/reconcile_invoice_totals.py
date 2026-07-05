"""
Recompute amount_paid/balance/status on every Invoice from the SUM of its
SUCCESS payments.

Fixes stale totals left behind by a bug in on_payment_save (apps.finance.
signals): the invoice sync used to run AFTER the auto cash-transaction step,
which could `return` early (no cash register configured for the site, or a
CashTransaction already existing for the payment) and silently skip the
invoice sync for that save — leaving amount_paid/balance/status stuck at an
older value even though the Payment itself was correctly marked SUCCESS.

Usage:
    python manage.py reconcile_invoice_totals
    python manage.py reconcile_invoice_totals --dry-run
    python manage.py reconcile_invoice_totals --student <student_id>
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum


class Command(BaseCommand):
    help = 'Resync Invoice.amount_paid/balance/status from SUCCESS payments.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
        parser.add_argument('--student', help='Limit to a single student id')

    def handle(self, *args, **options):
        from apps.finance.models import Invoice, Payment

        dry_run = options['dry_run']
        student_id = options.get('student')

        invoices = Invoice.objects.filter(is_active=True)
        if student_id:
            invoices = invoices.filter(student_id=student_id)

        total_checked = 0
        fixed = 0
        fixed_amount = Decimal('0')

        for invoice in invoices:
            total_checked += 1
            total_success = (
                Payment.objects.filter(invoice=invoice, status='SUCCESS')
                .aggregate(total=Sum('amount'))['total'] or Decimal('0')
            )
            if invoice.amount_paid == total_success:
                continue

            old = invoice.amount_paid
            self.stdout.write(
                f"  {'[DRY] ' if dry_run else ''}{invoice.invoice_number}: "
                f"amount_paid {old} -> {total_success}"
            )
            if not dry_run:
                invoice.amount_paid = total_success
                invoice.calculate_totals()
                invoice.save(update_fields=['amount_paid', 'balance', 'status', 'subtotal', 'total'])

            fixed += 1
            fixed_amount += (total_success - old)

        verb = "Would fix" if dry_run else "Fixed"
        self.stdout.write(
            self.style.SUCCESS(
                f"\nChecked {total_checked} invoice(s). {verb} {fixed} "
                f"with a total delta of {float(fixed_amount):,.0f} FCFA"
            )
        )
