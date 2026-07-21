"""
Read-only diagnostic: lists every invoice for one student with full detail
(fee types on each item, status, amounts, created_at) — used to identify
duplicate/orphan invoices (e.g. an INSCRIPTION invoice with a balance left
even though the student's is_enrolled flag says paid).

Usage:
    python manage.py list_student_invoices --email ibrahim.coulibaly@escam-test.ci
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "List every invoice (with items) for one student, for duplicate/orphan diagnosis."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Email of the student user')
        parser.add_argument('--matricule', help='Matricule of the student (alternative to --email)')

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.finance.models import Invoice

        if not options['email'] and not options['matricule']:
            raise CommandError('Pass --email or --matricule.')

        try:
            if options['email']:
                student = Student.objects.select_related('user').get(user__email=options['email'])
            else:
                student = Student.objects.select_related('user').get(matricule=options['matricule'])
        except Student.DoesNotExist:
            raise CommandError('No matching student found.')

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== Factures de {student.user.full_name} ({student.user.email}) — #{student.matricule} ===\n"
        ))
        self.stdout.write(f"  is_enrolled = {student.is_enrolled}")

        invoices = Invoice.objects.filter(student=student).prefetch_related('items__fee_type').order_by('created_at')
        for inv in invoices:
            items = ', '.join(
                f"{it.fee_type.code if it.fee_type_id else '?'}={it.description!r} x{it.quantity} @ {it.unit_price}"
                for it in inv.items.all()
            ) or '(aucun item)'
            self.stdout.write(
                f"\n  {inv.invoice_number} | id={inv.id} | is_active={inv.is_active} | status={inv.status} | "
                f"total={inv.total} amount_paid={inv.amount_paid} balance={inv.balance} | created_at={inv.created_at}"
            )
            self.stdout.write(f"    items: {items}")
            payments = list(inv.payments.all().values('payment_number', 'amount', 'status', 'created_at'))
            for p in payments:
                self.stdout.write(f"    payment: {p}")
