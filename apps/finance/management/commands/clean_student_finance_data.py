"""
Wipe all financial transaction data (Invoice/InvoiceItem/Payment) for ONE
specific student, and reset their financial snapshot fields — for cleaning
up leftover/inconsistent test data (e.g. from seed_echeancier_students)
without touching any other student.

Usage:
    python manage.py clean_student_finance_data --email ibrahim.coulibaly@escam-test.ci            # dry-run (default, no writes)
    python manage.py clean_student_finance_data --email ibrahim.coulibaly@escam-test.ci --yes       # actually deletes/resets
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Wipe Invoice/Payment data for one student (by email or matricule) and reset their financial fields.'

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Email of the student user')
        parser.add_argument('--matricule', help='Matricule of the student (alternative to --email)')
        parser.add_argument(
            '--yes', action='store_true',
            help='Actually perform the deletion/reset. Without this flag, only a dry-run preview is printed.'
        )

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.finance.models import Invoice, InvoiceItem, Payment

        if not options['email'] and not options['matricule']:
            raise CommandError('Pass --email or --matricule to identify the student.')

        try:
            if options['email']:
                student = Student.objects.select_related('user').get(user__email=options['email'])
            else:
                student = Student.objects.select_related('user').get(matricule=options['matricule'])
        except Student.DoesNotExist:
            raise CommandError('No matching student found.')

        confirm = options['yes']
        invoices = Invoice.objects.filter(student=student)
        items = InvoiceItem.objects.filter(invoice__student=student)
        payments = Payment.objects.filter(invoice__student=student)

        self.stdout.write(self.style.WARNING(
            f"\n=== clean_student_finance_data — {student.user.full_name} ({student.user.email}) — #{student.matricule} ===\n"
            + ('[DRY-RUN] Nothing will be deleted. Pass --yes to actually run this.\n' if not confirm else
               '!!! --yes given: this WILL permanently delete data for this student. !!!\n')
        ))
        self.stdout.write(f'  Payment rows to delete:      {payments.count()}')
        self.stdout.write(f'  InvoiceItem rows to delete:  {items.count()}')
        self.stdout.write(f'  Invoice rows to delete:      {invoices.count()}')
        for inv in invoices:
            self.stdout.write(
                f'    - {inv.invoice_number} | {inv.notes or "(sans note)"} | '
                f'total={inv.total} paid={inv.amount_paid} status={inv.status}'
            )

        if not confirm:
            self.stdout.write(self.style.WARNING(
                '\nDry-run only — no changes made. Re-run with --yes to execute.'
            ))
            return

        with transaction.atomic():
            deleted_payments = payments.delete()[0]
            deleted_items = items.delete()[0]
            deleted_invoices = invoices.delete()[0]
            student.registration_fee_paid = False
            student.total_paid = 0
            student.remaining_balance = student.registration_fee + student.tuition_fee
            student.save(update_fields=['registration_fee_paid', 'total_paid', 'remaining_balance'])

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Deleted {deleted_payments} payment(s), {deleted_items} invoice item(s), '
            f'{deleted_invoices} invoice(s). Reset financial fields on {student.user.full_name}.'
        ))
