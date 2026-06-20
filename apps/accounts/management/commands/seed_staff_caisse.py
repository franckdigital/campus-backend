"""
seed_staff_caisse.py
--------------------
Alimente le Personnel (StaffProfile + expériences) et la Caisse
(CashRegister + CashSession + CashTransaction) pour chaque site actif.

Usage :
    python manage.py seed_staff_caisse
    python manage.py seed_staff_caisse --wipe   # supprime et recrée
"""
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone


# ── Postes par département ────────────────────────────────────────────────────
STAFF_POSITIONS = [
    # (department, position, contract_type, hours)
    ('SCOLARITE',    'Chargé(e) de scolarité',      'PERMANENT', 40),
    ('COMPTABILITE', 'Comptable principal(e)',        'PERMANENT', 40),
    ('SECRETARIAT',  'Secrétaire de direction',       'PERMANENT', 40),
    ('INFORMATIQUE', 'Technicien informatique',        'CONTRACT',  35),
    ('BIBLIOTHEQUE', 'Bibliothécaire',                 'PERMANENT', 40),
    ('MAINTENANCE',  'Agent de maintenance',           'CONTRACT',  40),
    ('SCOLARITE',    "Assistant(e) de scolarité",      'CONTRACT',  40),
    ('COMPTABILITE', 'Assistant comptable',             'INTERN',    35),
    ('SECRETARIAT',  "Agent d'accueil",                'CONTRACT',  40),
    ('DIRECTION',    'Chargé(e) de communication',    'CONTRACT',  40),
]

# Expériences précédentes à créer pour les profils
EXPERIENCES_POOL = [
    # (company, position, years_start, years_end)  — years_end=None → poste actuel
    ("INPHB - Institut National Polytechnique", "Secrétaire administrative",   3, 1),
    ("BNI Côte d'Ivoire",                       "Agent de guichet",             5, 2),
    ("Lycée Technique d'Abidjan",               "Comptable",                    4, 1),
    ("CAMTEL CI",                               "Technicien réseau",            3, None),
    ("Université Félix Houphouët-Boigny",       "Bibliothécaire adjoint(e)",   6, 2),
    ("Résidence Les Palmiers",                  "Agent d'entretien",            2, None),
    ("Académie Internationale",                 "Conseiller(e) pédagogique",   4, 1),
    ("Cabinet Audit & Finance CI",              "Assistant comptable",          2, None),
    ("Mairie d'Abidjan",                        "Agent administratif",          5, 3),
    ("Orange CI",                               "Chargé(e) clientèle",         3, 1),
]


# ── Données de caisse par session ────────────────────────────────────────────
# Chaque entrée = une session (IN/OUT/description/ref)
# 4 sessions fermées + 1 ouverte (aujourd'hui)

SESSIONS_TEMPLATE = [
    # session_1 — S-20 (fermée)
    {
        'days_ago': 20,
        'opening_balance': Decimal('0'),
        'status': 'CLOSED',
        'transactions': [
            ('IN',  Decimal('175000'), "Paiement scolarité S1 - COULIBALY Ibrahim",    'PAY-S1-{site}-001'),
            ('IN',  Decimal('125000'), "Paiement scolarité S1 - TRAORE Aminata",        'PAY-S1-{site}-002'),
            ('IN',  Decimal('75000'),  "Frais d'inscription - BAMBA Seydou",            'PAY-S1-{site}-003'),
            ('IN',  Decimal('50000'),  "Paiement partiel - DIALLO Fatoumata",           'PAY-S1-{site}-004'),
            ('OUT', Decimal('18000'),  "Achat fournitures de bureau",                   'EXP-S1-{site}-001'),
            ('OUT', Decimal('7500'),   "Transport livraison matériel pédagogique",      'EXP-S1-{site}-002'),
            ('OUT', Decimal('12000'),  "Petites fournitures salle de cours",            'EXP-S1-{site}-003'),
        ],
    },
    # session_2 — S-14 (fermée)
    {
        'days_ago': 14,
        'opening_balance': Decimal('387500'),  # net session 1
        'status': 'CLOSED',
        'transactions': [
            ('IN',  Decimal('200000'), "Paiement scolarité S1 - YEO Paul",              'PAY-S2-{site}-001'),
            ('IN',  Decimal('100000'), "Paiement scolarité S1 - KONE Mariam",           'PAY-S2-{site}-002'),
            ('IN',  Decimal('150000'), "Paiement scolarité - OUATTARA Djeneba",         'PAY-S2-{site}-003'),
            ('OUT', Decimal('25000'),  "Entretien et nettoyage des locaux",             'EXP-S2-{site}-001'),
            ('OUT', Decimal('45000'),  "Facture électricité partielle",                 'EXP-S2-{site}-002'),
            ('OUT', Decimal('15000'),  "Achat ramettes papier A4",                     'EXP-S2-{site}-003'),
            ('OUT', Decimal('8500'),   "Frais courrier recommandé",                    'EXP-S2-{site}-004'),
        ],
    },
    # session_3 — S-7 (fermée)
    {
        'days_ago': 7,
        'opening_balance': Decimal('731000'),  # net sessions 1+2
        'status': 'CLOSED',
        'transactions': [
            ('IN',  Decimal('250000'), "Règlement frais scolarité - CAMARA Ali",        'PAY-S3-{site}-001'),
            ('IN',  Decimal('75000'),  "Frais d'inscription - BAKAYOKO Salif",          'PAY-S3-{site}-002'),
            ('IN',  Decimal('125000'), "Paiement scolarité - FOFANA Maimouna",          'PAY-S3-{site}-003'),
            ('OUT', Decimal('65000'),  "Achat matériel informatique (clavier/souris)",  'EXP-S3-{site}-001'),
            ('OUT', Decimal('32000'),  "Maintenance photocopieur",                      'EXP-S3-{site}-002'),
            ('OUT', Decimal('22000'),  "Fournitures pédagogiques divers",               'EXP-S3-{site}-003'),
        ],
    },
    # session_4 — S-3 (fermée)
    {
        'days_ago': 3,
        'opening_balance': Decimal('1062000'),  # net sessions 1+2+3
        'status': 'CLOSED',
        'transactions': [
            ('IN',  Decimal('300000'), "Paiement groupé scolarité - Promo BTS2",        'PAY-S4-{site}-001'),
            ('IN',  Decimal('175000'), "Paiement scolarité - DIABATE Ibrahim",          'PAY-S4-{site}-002'),
            ('OUT', Decimal('850000'), "Virement salaires personnel - Juin 2026",       'SAL-{site}-001'),
            ('OUT', Decimal('180000'), "Loyer bâtiment principal - Juin 2026",          'LOYER-{site}-001'),
            ('OUT', Decimal('28500'),  "Facture eau et électricité",                    'EXP-S4-{site}-001'),
            ('IN',  Decimal('100000'), "Paiement tardif - SORO Adjoua",                 'PAY-S4-{site}-003'),
        ],
    },
    # session_5 — Aujourd'hui (ouverte)
    {
        'days_ago': 0,
        'opening_balance': Decimal('578500'),  # solde après session 4
        'status': 'OPEN',
        'transactions': [
            ('IN',  Decimal('150000'), "Paiement scolarité S2 - GNALY Narcisse",        'PAY-TD-{site}-001'),
            ('IN',  Decimal('75000'),  "Frais inscription - ASSI Konan",                'PAY-TD-{site}-002'),
            ('IN',  Decimal('100000'), "Paiement partiel - GRAH Amos",                  'PAY-TD-{site}-003'),
            ('OUT', Decimal('15000'),  "Achat stylos et cahiers pédagogiques",          'EXP-TD-{site}-001'),
            ('OUT', Decimal('9500'),   "Frais envoi diplômes par coursier",             'EXP-TD-{site}-002'),
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed Personnel (StaffProfile) et Caisse (CashRegister + sessions) pour tous les sites'

    def add_arguments(self, parser):
        parser.add_argument(
            '--wipe', action='store_true',
            help='Supprime les profils staff et sessions de caisse avant de recréer'
        )

    def handle(self, *args, **options):
        from apps.core.models import Site, AcademicYear
        from apps.accounts.models import User
        from apps.staff.models import StaffProfile, StaffExperience
        from apps.finance.models import CashRegister, CashSession, CashTransaction

        sites = list(Site.objects.filter(is_active=True).order_by('name'))
        if not sites:
            self.stderr.write(self.style.ERROR('Aucun site actif trouvé. Lancez seed_full d\'abord.'))
            return

        academic_year = AcademicYear.objects.filter(is_current=True).first()
        super_admin = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.filter(user_type='ADMIN').first()
        )

        if options['wipe']:
            StaffExperience.objects.all().delete()
            StaffProfile.objects.all().delete()
            CashTransaction.objects.all().delete()
            CashSession.objects.all().delete()
            CashRegister.objects.all().delete()
            self.stdout.write(self.style.WARNING('  Données personnel et caisse supprimées (--wipe)'))

        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('══════════════════════════════════════════════'))
        self.stdout.write(self.style.HTTP_INFO('    SEED : Personnel & Caisse'))
        self.stdout.write(self.style.HTTP_INFO('══════════════════════════════════════════════'))

        total_profiles   = 0
        total_exp        = 0
        total_registers  = 0
        total_sessions   = 0
        total_txns       = 0

        for site in sites:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'  ▶  {site.name} ({site.code})'))

            # ── 1. Profils du personnel ───────────────────────────────────────
            self.stdout.write('     [1/2] Personnel…')

            # Directeur(trice) du site → DIRECTION
            admin_users = User.objects.filter(user_type='ADMIN', site=site, is_active=True)
            pos_idx = 0

            for admin_user in admin_users:
                profile, created = StaffProfile.objects.get_or_create(
                    user=admin_user,
                    defaults={
                        'employee_id':           self._employee_id(site.code, 'DIR', 1),
                        'department':            'DIRECTION',
                        'position':              'Directeur/Directrice de campus',
                        'hire_date':             date(2020, 9, 1),
                        'contract_type':         'PERMANENT',
                        'site':                  site,
                        'academic_year':         academic_year,
                        'contract_hours_per_week': 45,
                        'bio':                   f"Directeur/Directrice du campus {site.name}.",
                        'is_active':             True,
                    },
                )
                if created:
                    total_profiles += 1
                    # Expérience précédente
                    exp_data = EXPERIENCES_POOL[0]
                    exp_n = self._make_experience(profile, exp_data, pos_idx)
                    total_exp += exp_n
                    self.stdout.write(f'       + Directeur {admin_user.full_name}')

            # Personnel administratif du site
            staff_users = list(
                User.objects.filter(user_type='STAFF', site=site, is_active=True).order_by('last_name')
            )

            for i, staff_user in enumerate(staff_users):
                dept, position, contract_type, hours = STAFF_POSITIONS[pos_idx % len(STAFF_POSITIONS)]
                pos_idx += 1

                emp_id = self._employee_id(site.code, dept[:3], i + 1)

                hire_year  = 2018 + (i % 5)
                hire_month = ((i * 3) % 12) + 1

                profile, created = StaffProfile.objects.get_or_create(
                    user=staff_user,
                    defaults={
                        'employee_id':             emp_id,
                        'department':              dept,
                        'position':                position,
                        'hire_date':               date(hire_year, hire_month, 1),
                        'contract_type':           contract_type,
                        'site':                    site,
                        'academic_year':           academic_year,
                        'contract_hours_per_week': hours,
                        'bio':                     f"{position} au sein du campus {site.name}.",
                        'is_active':               True,
                    },
                )
                if created:
                    total_profiles += 1
                    exp_data = EXPERIENCES_POOL[i % len(EXPERIENCES_POOL)]
                    exp_n = self._make_experience(profile, exp_data, i)
                    total_exp += exp_n
                    self.stdout.write(f'       + {staff_user.full_name} → {dept} / {position}')

            self.stdout.write(f'       {total_profiles} profils, {total_exp} expériences (cumulatif)')

            # ── 2. Caisse ─────────────────────────────────────────────────────
            self.stdout.write('     [2/2] Caisse…')

            cashier = (
                User.objects.filter(user_type='STAFF', site=site, is_active=True).first()
                or User.objects.filter(user_type='ADMIN', site=site, is_active=True).first()
                or super_admin
            )

            register, reg_created = CashRegister.objects.get_or_create(
                code=f'CAISSE-{site.code}',
                site=site,
                defaults={
                    'name':            f'Caisse principale — {site.name}',
                    'current_balance': Decimal('0'),
                    'is_open':         False,
                    'is_active':       True,
                },
            )
            if reg_created:
                total_registers += 1
                self.stdout.write(f'       Caisse créée : {register.name}')
            else:
                self.stdout.write(f'       Caisse existante : {register.name}')

            today = timezone.now().date()
            site_code = site.code.replace('-', '')[:6].upper()

            for sess_tpl in SESSIONS_TEMPLATE:
                n_sessions, n_txns = self._create_session(
                    register=register,
                    cashier=cashier,
                    today=today,
                    template=sess_tpl,
                    site_code=site_code,
                )
                total_sessions += n_sessions
                total_txns     += n_txns

            # Solde final = solde ouverture session 5 + entrées - sorties du jour
            last_closed = SESSIONS_TEMPLATE[-2]  # session 4
            s4_in  = sum(a for t, a, *_ in SESSIONS_TEMPLATE[-2]['transactions'] if t == 'IN')
            s4_out = sum(a for t, a, *_ in SESSIONS_TEMPLATE[-2]['transactions'] if t == 'OUT')
            final_balance = SESSIONS_TEMPLATE[-1]['opening_balance']
            register.current_balance = final_balance
            register.is_open = True
            register.save()

            self.stdout.write(
                f'       {len(SESSIONS_TEMPLATE)} sessions, '
                f'solde courant : {final_balance:,.0f} FCFA'
            )

        # ── Résumé ────────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('══════════════════════════════════════════════'))
        self.stdout.write(self.style.SUCCESS('    SEED TERMINÉ AVEC SUCCÈS'))
        self.stdout.write(self.style.HTTP_INFO('══════════════════════════════════════════════'))
        self.stdout.write(f'  Sites traités          : {len(sites)}')
        self.stdout.write(f'  Profils personnel      : {total_profiles}')
        self.stdout.write(f'  Expériences créées     : {total_exp}')
        self.stdout.write(f'  Caisses créées         : {total_registers}')
        self.stdout.write(f'  Sessions de caisse     : {total_sessions}')
        self.stdout.write(f'  Transactions           : {total_txns}')
        self.stdout.write('')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _employee_id(self, site_code, dept_prefix, index):
        sc = site_code.replace('-', '').upper()[:4]
        return f'EMP-{sc}-{dept_prefix.upper()[:3]}-{index:03d}'

    def _make_experience(self, profile, exp_data, offset):
        """Crée une expérience passée pour un profil. Retourne 1 si créé."""
        company, position, years_start, years_end = exp_data
        today = date.today()
        start = date(today.year - years_start - offset % 2, 1 + (offset % 6) * 2, 1)
        end   = date(today.year - years_end, 6, 30) if years_end else None

        _, created = profile.experiences.get_or_create(
            company=company,
            position=position,
            defaults={
                'start_date':  start,
                'end_date':    end,
                'is_current':  end is None,
                'description': f"Poste de {position} chez {company}.",
                'is_active':   True,
            },
        )
        return 1 if created else 0

    def _create_session(self, register, cashier, today, template, site_code):
        """
        Crée une session de caisse (et ses transactions) depuis un template.
        Renvoie (sessions_créées, transactions_créées).
        """
        from apps.finance.models import CashSession, CashTransaction

        days_ago    = template['days_ago']
        sess_date   = today - timedelta(days=days_ago)
        status      = template['status']
        opening_bal = template['opening_balance']
        txns_tpl    = template['transactions']

        # Vérifier si une session existe déjà pour ce registre + date
        existing = CashSession.objects.filter(
            cash_register=register,
            opened_at__date=sess_date,
        ).first()
        if existing:
            return 0, 0

        # Créer la session
        session = CashSession.objects.create(
            cash_register=register,
            opened_by=cashier,
            opening_balance=opening_bal,
            status='OPEN',
            is_active=True,
        )

        # Backdate opened_at (auto_now_add ne supporte pas le passage en create)
        open_hour = 8 if days_ago > 0 else timezone.now().hour
        open_dt   = timezone.make_aware(
            datetime(sess_date.year, sess_date.month, sess_date.day, open_hour, 0, 0)
        )
        CashSession.objects.filter(pk=session.pk).update(opened_at=open_dt)
        session.refresh_from_db()

        # Créer les transactions
        txn_count = 0
        total_in  = Decimal('0')
        total_out = Decimal('0')
        for txn_type, amount, description, ref_tpl in txns_tpl:
            reference = ref_tpl.format(site=site_code)
            CashTransaction.objects.create(
                session=session,
                transaction_type=txn_type,
                amount=amount,
                description=description,
                reference=reference,
                recorded_by=cashier,
                is_active=True,
            )
            txn_count += 1
            if txn_type == 'IN':
                total_in  += amount
            else:
                total_out += amount

        # Fermer les sessions CLOSED
        if status == 'CLOSED':
            expected = opening_bal + total_in - total_out
            session.closing_balance = expected
            session.expected_balance = expected
            session.difference = Decimal('0')
            session.status = 'CLOSED'
            session.closed_by = cashier
            session.save()
            close_dt = timezone.make_aware(
                datetime(sess_date.year, sess_date.month, sess_date.day, 17, 30, 0)
            )
            CashSession.objects.filter(pk=session.pk).update(closed_at=close_dt)

        return 1, txn_count
