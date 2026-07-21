"""
Consolidate duplicate non-cancelled invoices of the same fee category for one
student into a single invoice, WITHOUT losing any real payment already
collected: every Payment row on the invoices being retired is re-pointed onto
the surviving invoice (not discarded), then the surviving invoice's
amount_paid/balance/status are recomputed from the real sum of its (now
combined) SUCCESS payments — same logic as recompute_invoice_totals.py.

This differs from fix_duplicate_registration_invoice.py, which keeps the
"best" invoice and cancels the others outright — fine when only one of the
duplicates was ever actually paid, but it silently drops any money that had
been paid against the cancelled invoices. Use this command instead whenever
more than one of the duplicates has real payments on it.

The invoice kept is the OLDEST (first created) of the group — cancelled
invoices keep their own (now zeroed-out) amount_paid/balance for the record,
but are excluded from every total/aggregate in the app already (CANCELLED
status).

Usage:
    python manage.py consolidate_student_invoices --email ibrahim.coulibaly@escam-test.ci --category INSCRIPTION
    python manage.py consolidate_student_invoices --matricule ESCAM-CO20260001 --category INSCRIPTION --yes
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Consolidate duplicate same-category invoices for one student, preserving all real payments on the survivor."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Email of the student user')
        parser.add_argument('--matricule', help='Matricule of the student (alternative to --email)')
        parser.add_argument('--category', required=True, choices=['INSCRIPTION', 'SCOLARITE'],
                             help='Which fee category to consolidate duplicates for')
        parser.add_argument('--yes', action='store_true', help='Apply the changes. Without this flag, dry-run only.')

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.finance.models import Invoice, Payment

        if not options['email'] and not options['matricule']:
            raise CommandError('Pass --email or --matricule.')

        try:
            if options['email']:
                student = Student.objects.select_related('user').get(user__email=options['email'])
            else:
                student = Student.objects.select_related('user').get(matricule=options['matricule'])
        except Student.DoesNotExist:
            raise CommandError('No matching student found.')

        category = options['category']
        confirm = options['yes']

        candidates = [
            inv for inv in Invoice.objects.filter(student=student, is_active=True).exclude(status='CANCELLED')
            .prefetch_related('items__fee_type', 'payments')
            if any((it.fee_type.code or '').upper() == category for it in inv.items.all() if it.fee_type_id)
        ]

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== consolidate_student_invoices — {student.user.full_name} ({student.user.email}) — {category} ===\n"
        ))
        self.stdout.write(f'  Factures {category} non annulées trouvées : {len(candidates)}')
        for inv in candidates:
            self.stdout.write(f'    - {inv.invoice_number} | total={inv.total} paid={inv.amount_paid} status={inv.status} | {inv.payments.count()} paiement(s)')

        if len(candidates) <= 1:
            self.stdout.write(self.style.SUCCESS('\nRien à consolider — 0 ou 1 facture, pas de doublon.'))
            return

        candidates.sort(key=lambda inv: inv.created_at)
        keep = candidates[0]
        to_retire = candidates[1:]

        moved_payments = []
        for inv in to_retire:
            for p in inv.payments.all():
                moved_payments.append((p, inv.invoice_number))

        self.stdout.write(self.style.WARNING(f'\n  Conservée : {keep.invoice_number} (créée le {keep.created_at})'))
        for inv in to_retire:
            self.stdout.write(f'  À annuler : {inv.invoice_number} ({inv.payments.count()} paiement(s) à déplacer vers {keep.invoice_number})')

        if not confirm:
            self.stdout.write(self.style.WARNING('\nDry-run uniquement — relancez avec --yes pour appliquer.'))
            return

        with transaction.atomic():
            for p, _ in moved_payments:
                p.invoice = keep
                p.save(update_fields=['invoice'])

            for inv in to_retire:
                inv.status = 'CANCELLED'
                inv.save(update_fields=['status'])

            from decimal import Decimal
            from django.db.models import Sum
            total_success = (
                Payment.objects.filter(invoice=keep, status='SUCCESS')
                .aggregate(total=Sum('amount'))['total'] or Decimal('0')
            )
            keep.amount_paid = total_success
            keep.calculate_totals()
            keep.save(update_fields=['subtotal', 'total', 'amount_paid', 'balance', 'status'])

            if category == 'INSCRIPTION' and keep.balance <= 0 and not student.is_enrolled:
                student.is_enrolled = True
                student.save(update_fields=['is_enrolled'])

        self.stdout.write(self.style.SUCCESS(
            f'\nFait. {len(moved_payments)} paiement(s) déplacé(s) vers {keep.invoice_number}. '
            f'Nouveau total payé={keep.amount_paid}, solde={keep.balance}, statut={keep.status}.'
        ))
