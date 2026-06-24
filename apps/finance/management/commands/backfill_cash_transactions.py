"""
Management command to backfill CashTransaction records for existing SUCCESS payments.

Usage:
    python manage.py backfill_cash_transactions
    python manage.py backfill_cash_transactions --dry-run
    python manage.py backfill_cash_transactions --session-id <uuid>
"""
from django.core.management.base import BaseCommand
from django.db.models import Q


class Command(BaseCommand):
    help = 'Create CashTransaction records for past SUCCESS payments that have none.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
        parser.add_argument('--session-id', type=str, help='Force a specific CashSession UUID')

    def handle(self, *args, **options):
        from apps.finance.models import Payment, CashSession, CashTransaction

        dry_run = options['dry_run']

        # Find the session to use
        if options.get('session_id'):
            try:
                session = CashSession.objects.get(id=options['session_id'])
            except CashSession.DoesNotExist:
                self.stderr.write(f"Session {options['session_id']} not found.")
                return
        else:
            session = (
                CashSession.objects
                .filter(status='OPEN', is_active=True)
                .order_by('-opened_at')
                .first()
            )
            if not session:
                self.stderr.write(
                    "No open session found. Open a session first or pass --session-id."
                )
                return

        self.stdout.write(f"Using session: {session} (id={session.id})")

        # All SUCCESS payments without a cash transaction
        payments = (
            Payment.objects
            .filter(status='SUCCESS', is_active=True)
            .filter(cash_transactions__isnull=True)
            .select_related('invoice__student__user', 'invoice')
            .order_by('created_at')
        )

        self.stdout.write(f"Payments to backfill: {payments.count()}")

        if dry_run:
            self.stdout.write("[DRY-RUN] No records will be created.")

        count = 0
        total_amount = 0

        for p in payments:
            inv = p.invoice
            inv_text = (inv.notes or '').lower()

            is_inscription = 'inscription' in inv_text or inv.items.filter(
                Q(description__icontains='inscription') |
                Q(fee_type__name__icontains='inscription') |
                Q(fee_type__code__icontains='REGISTRATION')
            ).exists()

            fee_label = "Frais d'inscription" if is_inscription else "Frais de scolarité"
            try:
                student_name = inv.student.user.get_full_name() or str(inv.student)
            except Exception:
                student_name = str(inv.student_id)

            description = f"{fee_label} — {student_name} (facture {inv.invoice_number})"
            ref_date = p.created_at.strftime('%Y%m%d') if p.created_at else '00000000'
            reference = f"PAY-{ref_date}-{str(p.id)[:8].upper()}"

            self.stdout.write(
                f"  {'[DRY] ' if dry_run else ''}{p.amount} FCFA — {description}"
            )

            if not dry_run:
                CashTransaction.objects.create(
                    session=session,
                    payment=p,
                    transaction_type='IN',
                    amount=p.amount,
                    description=description,
                    reference=reference,
                )

            count += 1
            total_amount += float(p.amount)

        action = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{action} {count} transactions — Total: {total_amount:,.0f} FCFA"
            )
        )

        if not dry_run and count > 0:
            # Update cash register balance
            session.cash_register.current_balance = (
                session.cash_register.current_balance + total_amount
            )
            session.cash_register.save(update_fields=['current_balance'])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cash register balance updated: "
                    f"{float(session.cash_register.current_balance):,.0f} FCFA"
                )
            )
