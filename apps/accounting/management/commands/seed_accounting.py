"""
seed_accounting.py
------------------
Initialise le module comptabilité avec :
  1. Plan comptable OHADA pour tous les sites
  2. Dépenses exemples (PENDING, APPROVED, PAID — variées)
  3. Écritures comptables journal exemples liées au plan OHADA

Usage:
    python manage.py seed_accounting
    python manage.py seed_accounting --wipe   # supprime les données avant de recréer
"""
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone


OHADA_ACCOUNTS = [
    # Trésorerie & banque (ASSET)
    {'code': '571',  'name': 'Caisse',                            'account_type': 'ASSET'},
    {'code': '521',  'name': 'Banque',                            'account_type': 'ASSET'},
    # Créances clients (ASSET)
    {'code': '411',  'name': 'Etudiants - creances scolarite',    'account_type': 'ASSET'},
    {'code': '412',  'name': 'Clients douteux',                   'account_type': 'ASSET'},
    # Passif
    {'code': '401',  'name': 'Fournisseurs',                      'account_type': 'LIABILITY'},
    {'code': '421',  'name': 'Personnel - remunerations dues',    'account_type': 'LIABILITY'},
    # Capitaux propres
    {'code': '101',  'name': 'Capital social',                    'account_type': 'EQUITY'},
    {'code': '111',  'name': 'Reserves legales',                  'account_type': 'EQUITY'},
    # Produits (REVENUE)
    {'code': '706',  'name': 'Frais de scolarite',                'account_type': 'REVENUE'},
    {'code': '7061', 'name': "Frais d'inscription",               'account_type': 'REVENUE'},
    {'code': '708',  'name': "Autres produits d'activite",        'account_type': 'REVENUE'},
    # Charges (EXPENSE)
    {'code': '621',  'name': 'Remunerations - personnel enseignant',   'account_type': 'EXPENSE'},
    {'code': '622',  'name': 'Remunerations - personnel administratif','account_type': 'EXPENSE'},
    {'code': '631',  'name': 'Loyers et charges locatives',            'account_type': 'EXPENSE'},
    {'code': '635',  'name': 'Entretien et reparations',               'account_type': 'EXPENSE'},
    {'code': '641',  'name': 'Fournitures scolaires et bureautiques',  'account_type': 'EXPENSE'},
    {'code': '651',  'name': 'Marketing et publicite',                 'account_type': 'EXPENSE'},
    {'code': '671',  'name': 'Charges exceptionnelles',                'account_type': 'EXPENSE'},
]

EXPENSES_SEED = [
    # (label, category, amount, days_ago, status)
    ('Salaires enseignants - Janvier 2026',   'SALARY',         850000, 50, 'PAID'),
    ('Salaires personnels administratifs',     'SALARY',         320000, 50, 'PAID'),
    ('Loyer batiment principal - Fev 2026',   'INFRASTRUCTURE', 180000, 45, 'PAID'),
    ('Facture electricite et eau - Janv',      'UTILITIES',       28500, 48, 'PAID'),
    ('Achat fournitures de bureau',            'SUPPLIES',        15200, 40, 'PAID'),
    ('Maintenance serveurs et reseau',         'MAINTENANCE',     45000, 35, 'APPROVED'),
    ('Fournitures peda - TP Informatique',     'SUPPLIES',        62000, 30, 'APPROVED'),
    ('Campagne pub reseaux sociaux',           'MARKETING',       35000, 25, 'APPROVED'),
    ('Salaires enseignants - Fev 2026',       'SALARY',         850000, 20, 'PENDING'),
    ('Transport materiel pedagogique',         'TRANSPORT',       12500, 15, 'PENDING'),
    ('Renouvellement licence antivirus',       'SUPPLIES',        18000, 10, 'PENDING'),
    ('Travaux peinture salle de cours',        'MAINTENANCE',     75000,  5, 'PENDING'),
    ('Achat imprimante laser',                 'INFRASTRUCTURE',  95000,  3, 'PENDING'),
]

JOURNAL_ENTRIES_SEED = [
    # (description, reference, days_ago, status, lines)
    # lines: list of (account_code, debit, credit, libelle)
    {
        'description': 'Encaissement frais scolarite - L1-INFO-2526',
        'reference': 'PAY-2026-000001',
        'days_ago': 60,
        'status': 'POSTED',
        'lines': [
            ('571', 150000, 0,      'Caisse - encaissement scolarite'),
            ('706', 0,      150000, 'Frais de scolarite S1'),
        ],
    },
    {
        'description': 'Encaissement frais inscription nouveaux etudiants',
        'reference': 'PAY-2026-000002',
        'days_ago': 58,
        'status': 'POSTED',
        'lines': [
            ('571', 250000,  0,      'Caisse - frais inscription'),
            ('7061', 0,     250000, "Frais d'inscription 2025-2026"),
        ],
    },
    {
        'description': 'Virement loyer batiment - Janvier',
        'reference': 'VIR-2026-001',
        'days_ago': 55,
        'status': 'POSTED',
        'lines': [
            ('631', 180000, 0,      'Loyer batiment principal janv'),
            ('521', 0,      180000, 'Banque - virement loyer'),
        ],
    },
    {
        'description': 'Paiement salaires personnel enseignant janv',
        'reference': 'SAL-2026-001',
        'days_ago': 50,
        'status': 'POSTED',
        'lines': [
            ('621', 850000, 0,      'Remuneration enseignants janv'),
            ('421', 0,      850000, 'Personnel - salaires dus'),
        ],
    },
    {
        'description': 'Reglement salaires via banque janv',
        'reference': 'SAL-2026-001B',
        'days_ago': 49,
        'status': 'POSTED',
        'lines': [
            ('421', 850000, 0,      'Reglement salaires enseignants'),
            ('521', 0,      850000, 'Banque - virement salaires'),
        ],
    },
    {
        'description': 'Encaissement scolarite - L2-GESTION-2526',
        'reference': 'PAY-2026-000015',
        'days_ago': 40,
        'status': 'POSTED',
        'lines': [
            ('521', 200000, 0,      'Banque - scolarite L2'),
            ('706', 0,      200000, 'Frais de scolarite S1 L2'),
        ],
    },
    {
        'description': 'Achat fournitures bureau et pedagogiques',
        'reference': 'FACT-FOUR-001',
        'days_ago': 38,
        'status': 'POSTED',
        'lines': [
            ('641', 62000, 0,      'Fournitures TP informatique'),
            ('401', 0,     62000,  'Fournisseur - SOCOBIM'),
        ],
    },
    {
        'description': 'Encaissement multiple scolarites batch fev',
        'reference': 'BATCH-FEV-001',
        'days_ago': 20,
        'status': 'POSTED',
        'lines': [
            ('571', 420000, 0,      'Caisse - batch scolarites fev'),
            ('706', 0,      420000, 'Frais de scolarite S2 batch'),
        ],
    },
    {
        'description': 'Depense maintenance reseau et serveurs',
        'reference': 'EXP-MAINT-001',
        'days_ago': 15,
        'status': 'DRAFT',
        'lines': [
            ('635', 45000, 0,      'Maintenance serveurs'),
            ('401', 0,     45000,  'Fournisseur - TechSolutions'),
        ],
    },
    {
        'description': 'Campagne marketing reseaux sociaux mars',
        'reference': 'MARK-2026-001',
        'days_ago': 10,
        'status': 'DRAFT',
        'lines': [
            ('651', 35000, 0,      'Pub Facebook / Instagram'),
            ('521', 0,     35000,  'Banque - paiement marketing'),
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed accounting module: OHADA chart of accounts + sample expenses + journal entries'

    def add_arguments(self, parser):
        parser.add_argument('--wipe', action='store_true',
                            help='Supprime les donnees existantes avant de recréer')

    def handle(self, *args, **options):
        from apps.core.models import Site
        from apps.accounting.models import AccountingAccount, JournalEntry, JournalLine
        from apps.finance.models import Expense
        from apps.accounts.models import User

        sites = list(Site.objects.filter(is_active=True))
        if not sites:
            self.stderr.write('Aucun site actif trouve.')
            return

        admin = User.objects.filter(user_type='ADMIN', is_active=True).first() or \
                User.objects.filter(is_superuser=True).first()

        if options['wipe']:
            JournalLine.objects.all().delete()
            JournalEntry.objects.all().delete()
            AccountingAccount.objects.all().delete()
            Expense.objects.all().delete()
            self.stdout.write(self.style.WARNING('  Donnees comptables supprimees (--wipe)'))

        # 1. Plan comptable OHADA pour chaque site
        self.stdout.write('  [1/3] Initialisation plan comptable OHADA...')
        total_accounts = 0
        for site in sites:
            created_count = 0
            for acc_data in OHADA_ACCOUNTS:
                _, created = AccountingAccount.objects.get_or_create(
                    code=acc_data['code'], site=site,
                    defaults={**acc_data, 'is_system': True, 'is_active': True, 'description': ''}
                )
                if created:
                    created_count += 1
            total_accounts += created_count
            self.stdout.write(f'    OK {site.name} : {created_count} comptes')

        self.stdout.write(self.style.SUCCESS(f'  => {total_accounts} comptes crees au total'))

        # 2. Depenses
        self.stdout.write('  [2/3] Creation des depenses exemples...')
        site = sites[0]
        today = timezone.now().date()
        dep_created = 0
        for label, category, amount, days_ago, status in EXPENSES_SEED:
            exp_date = today - timedelta(days=days_ago)
            exp, created = Expense.objects.get_or_create(
                label=label,
                site=site,
                defaults={
                    'category': category,
                    'amount': Decimal(str(amount)),
                    'date': exp_date,
                    'status': status,
                    'approved_by': admin if status in ('APPROVED', 'PAID') else None,
                }
            )
            if created:
                dep_created += 1
        self.stdout.write(self.style.SUCCESS(f'  => {dep_created} depenses creees'))

        # 3. Ecritures comptables
        self.stdout.write('  [3/3] Creation des ecritures journal...')
        je_created = 0
        for entry_data in JOURNAL_ENTRIES_SEED:
            entry_date = today - timedelta(days=entry_data['days_ago'])

            # Skip si une ecriture avec meme reference existe deja
            if JournalEntry.objects.filter(
                reference=entry_data['reference'], site=site
            ).exists():
                continue

            entry = JournalEntry.objects.create(
                site=site,
                entry_date=entry_date,
                description=entry_data['description'],
                reference=entry_data['reference'],
                status='DRAFT',
                created_by=admin,
                is_active=True,
            )

            for acc_code, debit, credit, libelle in entry_data['lines']:
                try:
                    account = AccountingAccount.objects.get(code=acc_code, site=site)
                except AccountingAccount.DoesNotExist:
                    continue
                JournalLine.objects.create(
                    journal_entry=entry,
                    account=account,
                    debit_amount=Decimal(str(debit)),
                    credit_amount=Decimal(str(credit)),
                    description=libelle,
                    is_active=True,
                )

            # Valider les ecritures marquees POSTED
            if entry_data['status'] == 'POSTED' and admin:
                entry.post(admin)

            je_created += 1

        self.stdout.write(self.style.SUCCESS(f'  => {je_created} ecritures creees'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Comptabilite initialisee avec succes !'
        ))
        self.stdout.write(f'  - {total_accounts} comptes OHADA')
        self.stdout.write(f'  - {dep_created} depenses')
        self.stdout.write(f'  - {je_created} ecritures journal')
