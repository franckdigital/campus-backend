"""
DESTRUCTIVE — wipes all student financial transaction data system-wide:
every Payment, InvoiceItem, Invoice and CashTransaction row, and resets each
Student's financial snapshot fields (is_enrolled, total_paid,
remaining_balance) back to their defaults.

Does NOT touch FeeConfiguration (the barème) or Student.registration_fee /
Student.tuition_fee (the student's assigned base-fee snapshot, not
transactional history) — those are configuration, not "financial data"
resulting from payments.

⚠️ Interaction to be aware of: this resets is_enrolled=False for
EVERY student. Combined with the registration-fee access gate
(apps.students.permissions.IsRegistrationFeePaidOrExempt), every currently
active/already-paid student will be locked out of the whole app immediately
after this runs, until fresh invoices exist and get paid again. Only run
this when that is genuinely intended.

Usage:
    python manage.py wipe_student_finance_data            # dry-run (default, no writes)
    python manage.py wipe_student_finance_data --yes       # actually deletes/resets
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'DESTRUCTIVE: wipe all Invoice/Payment/CashTransaction data and reset Student financial fields.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes', action='store_true',
            help='Actually perform the deletion/reset. Without this flag, only a dry-run preview is printed.'
        )

    def handle(self, *args, **options):
        from apps.finance.models import Invoice, InvoiceItem, Payment, CashTransaction
        from apps.students.models import Student

        confirm = options['yes']

        payment_count = Payment.objects.count()
        item_count = InvoiceItem.objects.count()
        invoice_count = Invoice.objects.count()
        cash_tx_count = CashTransaction.objects.count()
        student_count = Student.objects.filter(is_enrolled=True).count()

        self.stdout.write(self.style.WARNING(
            '\n=== wipe_student_finance_data ===\n'
            + ('[DRY-RUN] Nothing will be deleted. Pass --yes to actually run this.\n' if not confirm else
               '!!! --yes given: this WILL permanently delete data. !!!\n')
        ))
        self.stdout.write(f'  Payment rows to delete:          {payment_count}')
        self.stdout.write(f'  InvoiceItem rows to delete:       {item_count}')
        self.stdout.write(f'  Invoice rows to delete:           {invoice_count}')
        self.stdout.write(f'  CashTransaction rows to delete:   {cash_tx_count}')
        self.stdout.write(f'  Students to reset (currently is_enrolled=True): {student_count}')

        if not confirm:
            self.stdout.write(self.style.WARNING(
                '\nDry-run only — no changes made. Re-run with --yes to execute.'
            ))
            return

        with transaction.atomic():
            deleted_cash = CashTransaction.objects.all().delete()[0]
            deleted_payments = Payment.objects.all().delete()[0]
            deleted_items = InvoiceItem.objects.all().delete()[0]
            deleted_invoices = Invoice.objects.all().delete()[0]
            updated_students = Student.objects.update(
                is_enrolled=False, total_paid=0, remaining_balance=0,
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Deleted {deleted_cash} cash transaction(s), {deleted_payments} payment(s), '
            f'{deleted_items} invoice item(s), {deleted_invoices} invoice(s). '
            f'Reset financial fields on {updated_students} student(s).'
        ))
