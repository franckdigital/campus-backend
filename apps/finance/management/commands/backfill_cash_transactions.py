"""
Backfill CashTransaction records for existing SUCCESS payments that have none.

Usage:
    python manage.py backfill_cash_transactions
    python manage.py backfill_cash_transactions --dry-run
"""
from decimal import Decimal
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create CashTransaction records for past SUCCESS payments that have none.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview without saving')

    def handle(self, *args, **options):
        from apps.finance.models import Payment, CashTransaction
        from apps.finance.signals import _get_or_create_open_session

        dry_run = options['dry_run']

        payments = (
            Payment.objects
            .filter(status='SUCCESS', is_active=True)
            .filter(cash_transactions__isnull=True)
            .select_related('invoice__student__user', 'invoice__site', 'payment_method')
            .order_by('created_at')
        )

        total = payments.count()
        self.stdout.write(f"Payments to backfill: {total}")
        if dry_run:
            self.stdout.write("[DRY-RUN] No records will be created.\n")

        count = 0
        amount_sum = Decimal('0')
        skipped = 0

        for p in payments:
            inv = p.invoice
            site = getattr(inv, 'site', None) or getattr(inv.student, 'site', None)

            if not dry_run:
                session = _get_or_create_open_session(site, payment_method=p.payment_method)
                if not session:
                    self.stderr.write(f"  SKIP  no cash register for site {site} — payment {p.id}")
                    skipped += 1
                    continue

            is_inscription = inv.items.filter(fee_type__code__iregex=r'inscri|reg').exists()
            fee_label = "Frais d'inscription" if is_inscription else "Frais de scolarité"
            try:
                student_name = inv.student.user.get_full_name() or str(inv.student)
            except Exception:
                student_name = ''

            description = f"{fee_label} — {student_name} (facture {inv.invoice_number})"
            ref_date = p.created_at.strftime('%Y%m%d') if p.created_at else '00000000'
            reference = f"PAY-{ref_date}-{str(p.id)[:8].upper()}"

            self.stdout.write(
                f"  {'[DRY] ' if dry_run else ''}+{p.amount} FCFA — {description}"
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
                session.cash_register.current_balance += p.amount
                session.cash_register.save(update_fields=['current_balance'])

            count += 1
            amount_sum += p.amount

        verb = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb} {count} transaction(s) — {float(amount_sum):,.0f} FCFA"
                + (f" | {skipped} skipped (no register)" if skipped else "")
            )
        )
