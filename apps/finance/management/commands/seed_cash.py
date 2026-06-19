"""
seed_cash.py
------------
Alimente la caisse avec des sessions et transactions réalistes.

Usage:
    python manage.py seed_cash
    python manage.py seed_cash --wipe   # supprime sessions/transactions avant de recréer
"""
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone


# (transaction_type, amount, description, reference)
SESSION_1_TXNS = [
    ('IN',  Decimal('150000'), 'Paiement scolarité S1 - KONE Mamadou',     'PAY-S1-0041'),
    ('IN',  Decimal('100000'), 'Paiement scolarité S1 - DIALLO Aminata',   'PAY-S1-0042'),
    ('IN',  Decimal('75000'),  "Frais d'inscription - COULIBALY Ibrahim",  'PAY-S1-0043'),
    ('OUT', Decimal('15000'),  'Achat fournitures de bureau',               'EXP-S1-001'),
    ('OUT', Decimal('8500'),   'Transport livraison matériel pédagogique',  'EXP-S1-002'),
]  # IN: 325 000 | OUT: 23 500 | net: 301 500 | closing: 0 + 301 500 = 301 500

SESSION_2_TXNS = [
    ('IN',  Decimal('125000'), 'Paiement scolarité S2 - TRAORE Fatou',     'PAY-S2-0055'),
    ('IN',  Decimal('75000'),  'Paiement scolarité S2 - BAMBA Seydou',     'PAY-S2-0056'),
    ('IN',  Decimal('25000'),  "Frais d'inscription - YEO Mariam",         'PAY-S2-0057'),
    ('OUT', Decimal('25000'),  'Entretien et nettoyage locaux',            'EXP-S2-001'),
    ('OUT', Decimal('12000'),  'Petites fournitures classe',               'EXP-S2-002'),
    ('OUT', Decimal('39500'),  'Achat imprimante partagée bureau scol.',   'EXP-S2-003'),
]  # IN: 225 000 | OUT: 76 500 | net: 148 500 | closing: 301 500 + 148 500 = 450 000

SESSION_TODAY_TXNS = [
    ('IN',  Decimal('100000'), 'Paiement scolarité - OUATTARA Paul',       'PAY-TD-0071'),
    ('IN',  Decimal('50000'),  'Paiement partiel - CAMARA Djénéba',       'PAY-TD-0072'),
    ('OUT', Decimal('18000'),  'Achat ramettes papier A4 (10 ramettes)',   'EXP-TD-001'),
    ('OUT', Decimal('7000'),   'Frais envoi courrier recommandé',          'EXP-TD-002'),
]  # IN: 150 000 | OUT: 25 000 | net: 125 000 (session toujours ouverte)


class Command(BaseCommand):
    help = 'Seed caisse : sessions + transactions réalistes pour Trésorerie et Caisse'

    def add_arguments(self, parser):
        parser.add_argument('--wipe', action='store_true',
                            help='Supprime les sessions/transactions existantes avant de recréer')

    def handle(self, *args, **options):
        from apps.finance.models import CashRegister, CashSession, CashTransaction
        from apps.accounts.models import User

        admin = (
            User.objects.filter(user_type='ADMIN', is_active=True).first()
            or User.objects.filter(is_superuser=True).first()
        )
        if not admin:
            self.stderr.write('Aucun admin trouvé.')
            return

        register = CashRegister.objects.filter(is_active=True).first()
        if not register:
            self.stderr.write('Aucune caisse trouvée.')
            return

        self.stdout.write(f'  Caisse cible : {register.name} ({register.code})')

        if options['wipe']:
            CashTransaction.objects.filter(session__cash_register=register).delete()
            CashSession.objects.filter(cash_register=register).delete()
            self.stdout.write(self.style.WARNING('  Sessions/transactions supprimées (--wipe)'))

        today = timezone.now().date()
        date_s1 = today - timedelta(days=12)
        date_s2 = today - timedelta(days=7)

        # ── Session 1 (CLOSED, il y a 12 jours) ───────────────────────────────
        s1, created_s1 = self._get_or_create_session(
            register=register,
            admin=admin,
            session_date=date_s1,
            opening_balance=Decimal('0'),
            transactions=SESSION_1_TXNS,
        )
        if created_s1:
            s1_in  = sum(a for t, a, *_ in SESSION_1_TXNS if t == 'IN')
            s1_out = sum(a for t, a, *_ in SESSION_1_TXNS if t == 'OUT')
            closing = Decimal('0') + s1_in - s1_out
            s1.closing_balance = closing
            s1.expected_balance = closing
            s1.difference = Decimal('0')
            s1.status = 'CLOSED'
            s1.closed_by = admin
            s1.save()
            CashSession.objects.filter(pk=s1.pk).update(
                closed_at=timezone.make_aware(
                    datetime(date_s1.year, date_s1.month, date_s1.day, 17, 30, 0)
                )
            )
            self.stdout.write(f'  [1/3] Session {date_s1} créée — clôturée à {closing:,.0f} FCFA')
        else:
            self.stdout.write(f'  [1/3] Session {date_s1} déjà existante — ignorée')

        # ── Session 2 (CLOSED, il y a 7 jours) ────────────────────────────────
        S1_CLOSING = Decimal('301500')
        s2, created_s2 = self._get_or_create_session(
            register=register,
            admin=admin,
            session_date=date_s2,
            opening_balance=S1_CLOSING,
            transactions=SESSION_2_TXNS,
        )
        if created_s2:
            s2_in  = sum(a for t, a, *_ in SESSION_2_TXNS if t == 'IN')
            s2_out = sum(a for t, a, *_ in SESSION_2_TXNS if t == 'OUT')
            closing = S1_CLOSING + s2_in - s2_out   # = 450 000
            s2.closing_balance = closing
            s2.expected_balance = closing
            s2.difference = Decimal('0')
            s2.status = 'CLOSED'
            s2.closed_by = admin
            s2.save()
            CashSession.objects.filter(pk=s2.pk).update(
                closed_at=timezone.make_aware(
                    datetime(date_s2.year, date_s2.month, date_s2.day, 18, 0, 0)
                )
            )
            self.stdout.write(f'  [2/3] Session {date_s2} créée — clôturée à {closing:,.0f} FCFA')
        else:
            self.stdout.write(f'  [2/3] Session {date_s2} déjà existante — ignorée')

        # ── Session 3 (OPEN, aujourd'hui) ─────────────────────────────────────
        S2_CLOSING = Decimal('450000')
        existing_today = CashSession.objects.filter(
            cash_register=register,
            opened_at__date=today,
        ).first()

        if existing_today:
            self.stdout.write(f'  [3/3] Session {today} déjà existante — ignorée')
        else:
            s3 = CashSession.objects.create(
                cash_register=register,
                opened_by=admin,
                opening_balance=S2_CLOSING,
                status='OPEN',
                is_active=True,
            )
            for txn_type, amount, description, reference in SESSION_TODAY_TXNS:
                CashTransaction.objects.create(
                    session=s3,
                    transaction_type=txn_type,
                    amount=amount,
                    description=description,
                    reference=reference,
                    recorded_by=admin,
                    is_active=True,
                )
            self.stdout.write(f'  [3/3] Session {today} créée (OUVERTE) '
                              f'— {len(SESSION_TODAY_TXNS)} transactions')

        # Synchroniser l'état de la caisse
        register.is_open = True
        register.current_balance = S2_CLOSING
        register.save()

        # Résumé final
        total_sessions = CashSession.objects.filter(cash_register=register).count()
        total_txns = CashTransaction.objects.filter(session__cash_register=register).count()
        today_in  = sum(a for t, a, *_ in SESSION_TODAY_TXNS if t == 'IN')
        today_out = sum(a for t, a, *_ in SESSION_TODAY_TXNS if t == 'OUT')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Caisse initialisée avec succès !'))
        self.stdout.write(f'  - {total_sessions} sessions de caisse')
        self.stdout.write(f'  - {total_txns} transactions')
        self.stdout.write(f'  - Solde caisse (dernier solde fermé) : {S2_CLOSING:,.0f} FCFA')
        self.stdout.write(
            f"  - Trésorerie aujourd'hui : {today_in:,.0f} entrées / "
            f"{today_out:,.0f} sorties / {today_in - today_out:,.0f} net"
        )

    def _get_or_create_session(self, register, admin, session_date, opening_balance, transactions):
        """Crée une session backdatée si aucune n'existe pour cette date."""
        from apps.finance.models import CashSession, CashTransaction

        existing = CashSession.objects.filter(
            cash_register=register,
            opened_at__date=session_date,
        ).first()
        if existing:
            return existing, False

        session = CashSession.objects.create(
            cash_register=register,
            opened_by=admin,
            opening_balance=opening_balance,
            status='OPEN',
            is_active=True,
        )
        # Backdate : auto_now_add interdit le passage direct en create()
        CashSession.objects.filter(pk=session.pk).update(
            opened_at=timezone.make_aware(
                datetime(session_date.year, session_date.month, session_date.day, 8, 0, 0)
            )
        )
        session.refresh_from_db()

        for txn_type, amount, description, reference in transactions:
            CashTransaction.objects.create(
                session=session,
                transaction_type=txn_type,
                amount=amount,
                description=description,
                reference=reference,
                recorded_by=admin,
                is_active=True,
            )

        return session, True
