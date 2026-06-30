"""
Delete test payments and reset invoice balances.

Usage:
    python manage.py clean_test_payments
    python manage.py clean_test_payments --student EL-2024-001
    python manage.py clean_test_payments --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum


class Command(BaseCommand):
    help = 'Delete test payments and recalculate invoice balances'

    def add_arguments(self, parser):
        parser.add_argument(
            '--student',
            help='Matricule of the student whose payments to clean (default: all elearning test students)',
        )
        parser.add_argument(
            '--payment-numbers',
            nargs='+',
            help='Specific payment numbers to delete',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        from apps.finance.models import Payment, Invoice

        dry_run = options['dry_run']

        if options['payment_numbers']:
            payments = Payment.objects.filter(payment_number__in=options['payment_numbers'])
        elif options['student']:
            payments = Payment.objects.filter(invoice__student__matricule=options['student'])
        else:
            # Default: delete all payments for elearning test students
            # seeded by seed_demo_complet (el1–el5 students, PAY-TEST-001–005)
            payments = Payment.objects.filter(
                invoice__student__matricule__startswith='EL-'
            )

        payments = payments.select_related('invoice', 'invoice__student')

        if not payments.exists():
            self.stdout.write(self.style.WARNING('No matching payments found.'))
            return

        self.stdout.write(f'{"[DRY RUN] " if dry_run else ""}Found {payments.count()} payment(s) to delete:')
        affected_invoices = set()
        for p in payments:
            student = p.invoice.student
            self.stdout.write(
                f'  - {p.payment_number} | {p.amount} F | {p.status} | '
                f'Invoice {p.invoice.invoice_number} | Student {student.matricule}'
            )
            affected_invoices.add(p.invoice_id)

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — nothing deleted.'))
            return

        with transaction.atomic():
            payments.delete()

            # Recalculate amount_paid for each affected invoice
            for invoice_id in affected_invoices:
                invoice = Invoice.objects.get(id=invoice_id)
                paid_total = Payment.objects.filter(
                    invoice=invoice, status='SUCCESS', is_active=True
                ).aggregate(s=Sum('amount'))['s'] or 0
                invoice.amount_paid = paid_total
                invoice.calculate_totals()
                invoice.save()
                self.stdout.write(
                    f'  Recalculated invoice {invoice.invoice_number}: '
                    f'total={invoice.total} paid={invoice.amount_paid} balance={invoice.balance} status={invoice.status}'
                )

        self.stdout.write(self.style.SUCCESS('Done.'))
