"""
Registration (inscription) is supposed to be a single, one-time, full
payment — but a student can end up with TWO non-cancelled inscription
invoices (e.g. one created before the "prepare_invoices" fee-gate bug was
fixed, another created afterward and actually paid). The aggregation logic
everywhere (web + mobile) sums ALL non-cancelled invoices of a given fee
type, so two 150 000 F inscription invoices show as "Total 300 000 F"
instead of the real 150 000 F barème, and the student never reaches
"inscription validée" even though they've genuinely paid in full.

This command finds a student's non-cancelled INSCRIPTION invoices; if there
is more than one, it keeps the "best" one (prefer PAID, else the one with
the most amount_paid) and cancels the rest — CANCELLED invoices are already
excluded from every total/aggregate in the app, no other code changes
needed. Then syncs Student.registration_fee_paid from the kept invoice.

Usage:
    python manage.py fix_duplicate_registration_invoice --email ibrahim.coulibaly@escam-test.ci            # dry-run
    python manage.py fix_duplicate_registration_invoice --email ibrahim.coulibaly@escam-test.ci --yes       # apply
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Cancel duplicate non-cancelled inscription invoices for one student, keeping only the paid/best one."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Email of the student user')
        parser.add_argument('--matricule', help='Matricule of the student (alternative to --email)')
        parser.add_argument(
            '--yes', action='store_true',
            help='Actually cancel the duplicate(s) and sync the student. Without this flag, only a dry-run preview is printed.'
        )

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.finance.models import Invoice

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

        reg_invoices = [
            inv for inv in Invoice.objects.filter(student=student, is_active=True).exclude(status='CANCELLED')
            .prefetch_related('items__fee_type')
            if any((it.fee_type.code or '').upper() == 'INSCRIPTION' for it in inv.items.all() if it.fee_type_id)
        ]

        self.stdout.write(self.style.WARNING(
            f"\n=== fix_duplicate_registration_invoice — {student.user.full_name} ({student.user.email}) — #{student.matricule} ===\n"
        ))
        self.stdout.write(f'  Inscription invoices found (non-cancelled): {len(reg_invoices)}')
        for inv in reg_invoices:
            self.stdout.write(f'    - {inv.invoice_number} | total={inv.total} paid={inv.amount_paid} status={inv.status}')

        if len(reg_invoices) <= 1:
            self.stdout.write(self.style.SUCCESS('\nNothing to do — 0 or 1 inscription invoice, no duplicate.'))
            return

        # Keep the PAID one if any, else the one with the most amount_paid.
        keep = max(reg_invoices, key=lambda inv: (inv.status == 'PAID', inv.amount_paid))
        to_cancel = [inv for inv in reg_invoices if inv.pk != keep.pk]

        self.stdout.write(self.style.WARNING(f'\n  Keeping: {keep.invoice_number} (total={keep.total}, paid={keep.amount_paid}, status={keep.status})'))
        for inv in to_cancel:
            self.stdout.write(f'  Would cancel: {inv.invoice_number} (total={inv.total}, paid={inv.amount_paid}, status={inv.status})')

        new_registration_fee_paid = keep.balance <= 0

        if not confirm:
            self.stdout.write(self.style.WARNING(
                f'\nDry-run only — no changes made. Would also set registration_fee_paid={new_registration_fee_paid}. '
                'Re-run with --yes to execute.'
            ))
            return

        with transaction.atomic():
            for inv in to_cancel:
                inv.status = 'CANCELLED'
                inv.save()
            if student.registration_fee_paid != new_registration_fee_paid:
                student.registration_fee_paid = new_registration_fee_paid
                student.save(update_fields=['registration_fee_paid'])

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Cancelled {len(to_cancel)} duplicate invoice(s), kept {keep.invoice_number}. '
            f'registration_fee_paid={new_registration_fee_paid}.'
        ))
