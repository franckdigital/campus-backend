"""
Diagnostic : affiche les caisses, sessions et paiements sans transaction.

Usage:
    python manage.py diagnose_cash
    python manage.py diagnose_cash --fix      # lance le backfill si nécessaire
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Diagnostique les caisses et les paiements sans transaction de caisse.'

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true', help='Crée les transactions manquantes')

    def handle(self, *args, **options):
        from apps.finance.models import CashRegister, CashSession, CashTransaction, Payment

        # 1. Caisses actives
        self.stdout.write(self.style.SUCCESS('\n=== CAISSES ACTIVES ==='))
        for r in CashRegister.objects.filter(is_active=True).select_related('site').order_by('site__code'):
            sessions = r.sessions.filter(status='OPEN').count()
            self.stdout.write(
                f"  {r.site.code if r.site else '?':15} | code={r.code!r:25} | name={r.name!r} | sessions_open={sessions} | balance={r.current_balance}"
            )

        # 2. Sessions ouvertes
        self.stdout.write(self.style.SUCCESS('\n=== SESSIONS OUVERTES ==='))
        for s in CashSession.objects.filter(status='OPEN').select_related('cash_register__site').order_by('-opened_at')[:20]:
            tx_count = s.transactions.filter(is_active=True).count()
            self.stdout.write(
                f"  {s.cash_register.site.code if s.cash_register.site else '?':15} | {s.cash_register.name!r:30} | {str(s.id)[:8]} | {s.opened_at:%Y-%m-%d} | {tx_count} tx"
            )

        # 3. Paiements SUCCESS sans transaction de caisse
        missing = (
            Payment.objects
            .filter(status='SUCCESS', is_active=True)
            .filter(cash_transactions__isnull=True)
            .select_related('invoice__site', 'invoice__student__user', 'payment_method')
            .order_by('-created_at')
        )
        count = missing.count()
        self.stdout.write(self.style.SUCCESS(f'\n=== PAIEMENTS SANS TRANSACTION ({count}) ==='))
        for p in missing[:20]:
            site = getattr(p.invoice, 'site', None)
            pm = p.payment_method
            student = p.invoice.student
            self.stdout.write(
                f"  {str(p.id)[:8]} | {p.amount:>10} FCFA | pm={pm.code if pm else '?':20} | site={site.code if site else '?'} | etudiant={student.user.get_full_name() if student else '?'} | {p.created_at:%Y-%m-%d %H:%M}"
            )

        if options['fix'] and count > 0:
            self.stdout.write(self.style.WARNING('\n--- CORRECTION ---'))
            from apps.finance.signals import _get_or_create_open_session
            from decimal import Decimal

            created = 0
            for p in missing:
                inv = p.invoice
                site = getattr(inv, 'site', None) or getattr(inv.student, 'site', None)
                session = _get_or_create_open_session(site, payment_method=p.payment_method)
                if not session:
                    self.stderr.write(f"  SKIP {str(p.id)[:8]}: pas de caisse pour site={site}")
                    continue

                is_inscription = inv.items.filter(fee_type__code__iregex=r'inscri|reg').exists()
                fee_label = "Frais d'inscription" if is_inscription else "Frais de scolarité"
                try:
                    student_name = inv.student.user.get_full_name() or str(inv.student)
                except Exception:
                    student_name = ''
                ref_date = p.created_at.strftime('%Y%m%d') if p.created_at else '00000000'
                reference = f"PAY-{ref_date}-{str(p.id)[:8].upper()}"
                description = f"{fee_label} — {student_name} (facture {inv.invoice_number})"

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
                self.stdout.write(
                    f"  ✓ {p.amount} FCFA → {session.cash_register.name} ({session.cash_register.site.code if session.cash_register.site else '?'})"
                )
                created += 1

            self.stdout.write(self.style.SUCCESS(f'\n{created} transaction(s) créée(s).'))
        elif count > 0:
            self.stdout.write(self.style.WARNING('\nLancez avec --fix pour créer les transactions manquantes.'))
