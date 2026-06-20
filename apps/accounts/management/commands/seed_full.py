"""
seed_full.py — Seed multi-campus complet
5 campus : ITA Marcory, Institut des Technologies d'Abidjan,
           ITA 2 Plateaux, PIGIER, ISPA
Usage: python manage.py seed_full
ATTENTION : efface toutes les données existantes avant de seeder.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, datetime

ADMIN_PWD = 'Admin2024!'
DEMO_PWD  = 'Campus2024!'


def _dt(d, h=10, m=0):
    return timezone.make_aware(datetime(d.year, d.month, d.day, h, m))


# ===========================================================================
# DONNEES STATIQUES
# ===========================================================================

SITES_DATA = [
    {
        'code': 'ITA-MARC', 'name': 'ITA Marcory',
        'address': 'Rue des Tulipes, Zone 4, Marcory', 'city': 'Abidjan',
        'phone': '+225 27 21 35 10 00', 'email': 'marcory@ita.ci', 'is_main': True,
    },
    {
        'code': 'ITA-PLAT', 'name': "Institut des Technologies d'Abidjan",
        'address': 'Avenue Joseph Anoma, Plateau', 'city': 'Abidjan',
        'phone': '+225 27 20 31 22 00', 'email': 'plateau@ita.ci', 'is_main': False,
    },
    {
        'code': 'ITA-2PL', 'name': 'ITA 2 Plateaux',
        'address': 'Rue des Jardins, Cocody 2 Plateaux', 'city': 'Abidjan',
        'phone': '+225 27 22 48 05 00', 'email': 'deuxplateaux@ita.ci', 'is_main': False,
    },
    {
        'code': 'PIGIER', 'name': 'PIGIER',
        'address': 'Boulevard Lagunaire, Cocody', 'city': 'Abidjan',
        'phone': '+225 27 22 44 20 00', 'email': 'contact@pigier.ci', 'is_main': False,
    },
    {
        'code': 'ISPA', 'name': 'ISPA',
        'address': 'Avenue de la Paix, Yopougon Niangon Nord', 'city': 'Abidjan',
        'phone': '+225 27 23 50 11 00', 'email': 'contact@ispa.ci', 'is_main': False,
    },
]

# (nom, code, type, durée_ans)
PROGRAMS_DATA = {
    'ITA-MARC': ('Licence Informatique',          'LI-MARC',   'info',    3),
    'ITA-PLAT': ('Licence Informatique',          'LI-PLAT',   'info',    3),
    'ITA-2PL':  ('Licence Informatique',          'LI-2PL',    'info',    3),
    'PIGIER':   ('BTS Comptabilite',              'BTS-PIG',   'gestion', 2),
    'ISPA':     ('BTS Informatique de Gestion',   'BTS-ISPA',  'mixed',   2),
}

SUBJECTS = [
    # code, nom, coefficient, heures/semaine
    ('ALG101', 'Algorithmique et structures de donnees', 4, 4),
    ('PRG101', 'Programmation Python',                   3, 3),
    ('MAT101', 'Mathematiques discretes',                3, 3),
    ('RES101', 'Reseaux informatiques',                  3, 3),
    ('BDD101', 'Bases de donnees relationnelles',        3, 4),
    ('WEB201', 'Developpement web full-stack',           4, 4),
    ('SYS201', "Systemes d'exploitation",                3, 3),
    ('ANG101', 'Anglais technique',                      2, 2),
    ('COM101', 'Communication professionnelle',          2, 2),
    ('GES101', 'Introduction a la gestion',              3, 3),
    ('CPT101', 'Comptabilite generale',                  4, 4),
    ('MKT101', 'Marketing fondamental',                  3, 3),
    ('DRT101', 'Droit des affaires',                     2, 2),
    ('ECO101', 'Economie generale',                      3, 3),
    ('FIN201', "Finance d'entreprise",                   3, 3),
    ('INF101', "Introduction a l'informatique",          3, 3),
    ('RH201',  'Gestion des ressources humaines',        3, 3),
    ('MAT201', 'Analyse et algebre lineaire',            3, 3),
]

SUBJECTS_BY_TYPE = {
    'info':    ['ALG101', 'PRG101', 'MAT101', 'RES101', 'BDD101', 'ANG101', 'COM101'],
    'gestion': ['GES101', 'CPT101', 'MKT101', 'DRT101', 'ECO101', 'ANG101', 'COM101'],
    'mixed':   ['INF101', 'GES101', 'CPT101', 'MAT101', 'ANG101', 'COM101', 'ECO101'],
}

ADMINS_DATA = {
    'ITA-MARC': ('directeur@ita-marc.ci',  'Koffi Emmanuel',  'Yao'),
    'ITA-PLAT': ('directeur@ita-plat.ci',  'Adjoua Patricia', "N'Guessan"),
    'ITA-2PL':  ('directeur@ita-2pl.ci',   'Bernard',         'Atta'),
    'PIGIER':   ('directeur@pigier.ci',    'Aimee Rosette',   'Gbagbo'),
    'ISPA':     ('directeur@ispa.ci',      'Lamine Oumar',    'Diallo'),
}

STAFF_DATA = {
    'ITA-MARC': [
        ('s.koffi@ita-marc.ci',    'Sandrine', 'Koffi'),
        ('p.assouman@ita-marc.ci', 'Pierre',   'Assouman'),
    ],
    'ITA-PLAT': [
        ('f.sery@ita-plat.ci',   'Fatou',  'Sery'),
        ('i.konate@ita-plat.ci', 'Ismael', 'Konate'),
    ],
    'ITA-2PL': [
        ('a.gnagne@ita-2pl.ci', 'Adjoua', 'Gnagne'),
        ('k.lago@ita-2pl.ci',   'Kofi',   'Lago'),
    ],
    'PIGIER': [
        ('n.ble@pigier.ci',  'Nadege',   'Ble'),
        ('a.tape@pigier.ci', 'Aristide', 'Tape'),
    ],
    'ISPA': [
        ('m.guehi@ispa.ci', 'Martine', 'Guehi'),
        ('o.soro@ispa.ci',  'Omar',    'Soro'),
    ],
}

# (email, prenom, nom, specialisation, qualification, date_embauche, contrat, taux_horaire, matricule)
TEACHERS_DATA = {
    'ITA-MARC': [
        ('j.kouassi@ita-marc.ci', 'Jean-Baptiste', 'Kouassi', 'Informatique & Algorithmes',  'Doctorat Informatique',      date(2020, 9,  1), 'PERMANENT', 15000, 'MARC-P001'),
        ('f.bamba@ita-marc.ci',   'Fatoumata',     'Bamba',   'Mathematiques Appliquees',    'Master Mathematiques',       date(2021, 1, 15), 'PERMANENT', 12000, 'MARC-P002'),
        ('e.ngoran@ita-marc.ci',  'Eric',           'Ngoran',  'Reseaux & Securite',          'Ingenieur Reseaux',          date(2022, 9,  1), 'CONTRACT',  10000, 'MARC-P003'),
        ('c.yao@ita-marc.ci',     'Christiane',    'Yao',     'Bases de donnees & Web',      'Master Genie Logiciel',      date(2021, 9,  1), 'PERMANENT', 11000, 'MARC-P004'),
    ],
    'ITA-PLAT': [
        ('m.brou@ita-plat.ci',    'Marc-Antoine', 'Brou',    'Informatique',                 'Doctorat Informatique',      date(2021, 9,  1), 'PERMANENT', 15000, 'PLAT-P001'),
        ('a.diabate@ita-plat.ci', 'Amara',        'Diabate', 'Mathematiques',                'Master Mathematiques Pures', date(2022, 1, 15), 'PERMANENT', 12000, 'PLAT-P002'),
        ('t.kouame@ita-plat.ci',  'Theodore',     'Kouame',  'Systemes & Reseaux',           'Ingenieur Informatique',     date(2022, 9,  1), 'CONTRACT',  10000, 'PLAT-P003'),
    ],
    'ITA-2PL': [
        ('a.kone@ita-2pl.ci',      'Aboubakar', 'Kone',      'Developpement Web & Mobile',  'Master Developpement',       date(2021, 9,  1), 'PERMANENT', 13000, '2PL-P001'),
        ('m.toure@ita-2pl.ci',     'Mariam',    'Toure',     'Mathematiques',                'Licence Math-Info',          date(2022, 9,  1), 'CONTRACT',   9000, '2PL-P002'),
        ('p.ouedraogo@ita-2pl.ci', 'Pascal',    'Ouedraogo', 'Reseaux Informatiques',        'Licence Pro Reseaux',        date(2023, 1,  1), 'CONTRACT',   8000, '2PL-P003'),
    ],
    'PIGIER': [
        ('j.akre@pigier.ci',      'Jocelyne', 'Akre',      'Commerce International',        'Master Commerce',            date(2020, 9,  1), 'PERMANENT', 14000, 'PIG-P001'),
        ('r.bogui@pigier.ci',     'Rodrigue', 'Bogui',     'Gestion Financiere & Comptable','Expert-Comptable',           date(2021, 1,  1), 'PERMANENT', 16000, 'PIG-P002'),
        ('s.coulibaly@pigier.ci', 'Seydou',   'Coulibaly', 'Marketing & Communication',     'Master Marketing',           date(2022, 9,  1), 'CONTRACT',   9000, 'PIG-P003'),
    ],
    'ISPA': [
        ('b.assi@ispa.ci',     'Brigitte', 'Assi',     'Informatique de Gestion',          'Ingenieur Informatique',     date(2021, 9,  1), 'PERMANENT', 12000, 'ISPA-P001'),
        ('m.traore@ispa.ci',   'Moussa',   'Traore',   'Gestion & Administration',         'Master Administration',      date(2021, 9,  1), 'PERMANENT', 11000, 'ISPA-P002'),
        ('c.lokossou@ispa.ci', 'Carine',   'Lokossou', 'Communication & Langues',          'Master Lettres Modernes',    date(2022, 9,  1), 'CONTRACT',   8000, 'ISPA-P003'),
    ],
}

# (email, prenom, nom, genre, naissance, lieu_naissance, matricule)
STUDENTS_DATA = {
    'ITA-MARC': [
        ('i.kone@ita-marc.ci',    'Ibrahim',  'Kone',     'M', date(2003, 1, 22), 'Bouake',      'MARC-2024-001'),
        ('a.traore@ita-marc.ci',  'Aicha',    'Traore',   'F', date(2002, 8, 15), 'Abidjan',     'MARC-2024-002'),
        ('k.kouadio@ita-marc.ci', 'Kevin',    'Kouadio',  'M', date(2003, 5, 10), 'Yamoussoukro','MARC-2024-003'),
        ('r.adjoua@ita-marc.ci',  'Rebecca',  'Adjoua',   'F', date(2002,11,  3), 'Abidjan',     'MARC-2024-004'),
    ],
    'ITA-PLAT': [
        ('m.dosso@ita-plat.ci',   'Mohamed',  'Dosso',   'M', date(2003, 3, 18), 'Korhogo', 'PLAT-2024-001'),
        ('e.gnaoule@ita-plat.ci', 'Estelle',  'Gnaoule', 'F', date(2002, 7, 25), 'Abidjan', 'PLAT-2024-002'),
        ('j.bah@ita-plat.ci',     'Junior',   'Bah',     'M', date(2003, 9, 12), 'Man',     'PLAT-2024-003'),
        ('p.ettien@ita-plat.ci',  'Patricia', 'Ettien',  'F', date(2002, 4,  6), 'Abidjan', 'PLAT-2024-004'),
    ],
    'ITA-2PL': [
        ('s.ouattara@ita-2pl.ci', 'Siaka',    'Ouattara', 'M', date(2003, 2, 14), 'Bouake',      'DEUX-2024-001'),
        ('l.tape@ita-2pl.ci',     'Laurence', 'Tape',     'F', date(2002, 6, 20), 'Abidjan',     'DEUX-2024-002'),
        ('d.yeboua@ita-2pl.ci',   'David',    'Yeboua',   'M', date(2003,10,  8), 'Abengourou',  'DEUX-2024-003'),
        ('c.akpan@ita-2pl.ci',    'Celine',   'Akpan',    'F', date(2002,12,  1), 'Abidjan',     'DEUX-2024-004'),
    ],
    'PIGIER': [
        ('f.diarrassouba@pigier.ci', 'Fanta',   'Diarrassouba', 'F', date(2003, 4, 17), 'Abidjan',   'PIG-2024-001'),
        ('n.guede@pigier.ci',        'Noel',    'Guede',        'M', date(2002, 9, 30), 'San-Pedro', 'PIG-2024-002'),
        ('a.konan@pigier.ci',        'Aminata', 'Konan',        'F', date(2003, 7,  5), 'Abidjan',   'PIG-2024-003'),
        ('b.kouame@pigier.ci',       'Boris',   'Kouame',       'M', date(2002, 3, 22), 'Bouafle',   'PIG-2024-004'),
    ],
    'ISPA': [
        ('r.silue@ispa.ci',   'Rachid',   'Silue',  'M', date(2003, 8, 11), 'Ferkessedougou', 'ISPA-2024-001'),
        ('o.kouakou@ispa.ci', 'Olivia',   'Kouakou','F', date(2002, 5, 28), 'Abidjan',        'ISPA-2024-002'),
        ('t.koffi@ispa.ci',   'Thierry',  'Koffi',  'M', date(2003,11, 15), 'Daloa',          'ISPA-2024-003'),
        ('n.adepe@ispa.ci',   'Nathalie', 'Adepe',  'F', date(2002, 2,  7), 'Abidjan',        'ISPA-2024-004'),
    ],
}

# (email, prenom, nom, profession, employeur, lien_parente)
PARENTS_DATA = {
    'ITA-MARC': [
        ('p.kone@gmail.com',    'Mamadou',   'Kone',      'Ingenieur',     'BNETD',            'FATHER'),
        ('p.traore@gmail.com',  'Rokia',     'Coulibaly', 'Commercante',   'Auto-entrepreneur', 'MOTHER'),
        ('p.kouadio@gmail.com', 'Konan',     'Kouadio',   'Fonctionnaire', 'Min. Education',   'FATHER'),
        ('p.adjoua@gmail.com',  'Yolande',   'Assoumou',  'Infirmiere',    'CHU Cocody',       'MOTHER'),
    ],
    'ITA-PLAT': [
        ('p.dosso@gmail.com',   'Issouf',    'Dosso',    'Commercant',   'Auto-entrepreneur', 'FATHER'),
        ('p.gnaoule@gmail.com', 'Suzanne',   'Gnaoule',  'Enseignante',  'Lycee Technique',   'MOTHER'),
        ('p.bah@gmail.com',     'Alpha',     'Bah',      'Chauffeur',    'SOTRA',             'FATHER'),
        ('p.ettien@gmail.com',  'Clemence',  'Ettien',   'Couturiere',   'Auto-entrepreneur', 'MOTHER'),
    ],
    'ITA-2PL': [
        ('p.ouattara@gmail.com', 'Brahima',    'Ouattara', 'Agriculteur', 'Auto-entrepreneur', 'FATHER'),
        ('p.tape@gmail.com',     'Henriette',  'Tape',     'Secretaire',  'Cabinet Prive',     'MOTHER'),
        ('p.yeboua@gmail.com',   'Augustin',   'Yeboua',   'Technicien',  'CIE',               'FATHER'),
        ('p.akpan@gmail.com',    'Marcelline', 'Akpan',    'Infirmiere',  'Polyclinique',      'MOTHER'),
    ],
    'PIGIER': [
        ('p.diarrassouba@gmail.com', 'Lassina',   'Diarrassouba', 'Transporteur', 'Auto-entrepreneur', 'FATHER'),
        ('p.guede@gmail.com',        'Bernadette','Guede',        'Commercante',  'Marche Cocody',     'MOTHER'),
        ('p.konan@gmail.com',        'Yao',       'Konan',        'Policier',     'DGPN',              'FATHER'),
        ('p.kouame@gmail.com',       'Philomene', 'Kouame',       'Menagere',     '',                  'MOTHER'),
    ],
    'ISPA': [
        ('p.silue@gmail.com',   'Hamidou',   'Silue',    'Commercant',  'Marche Korhogo',    'FATHER'),
        ('p.kouakou@gmail.com', 'Julienne',  'Kouakou',  'Coiffeuse',   'Auto-entrepreneur', 'MOTHER'),
        ('p.koffi@gmail.com',   'Lambert',   'Koffi',    'Menuisier',   'Atelier Koffi',     'FATHER'),
        ('p.adepe@gmail.com',   'Veronique', 'Adepe',    'Couturiere',  'Auto-entrepreneur', 'MOTHER'),
    ],
}

BANK_DATA = {
    'ITA-MARC': ('Compte Principal ITA Marcory',     'BICICI',   'CI93BI0080MARC01134500014944', 9500000),
    'ITA-PLAT': ('Compte Principal ITA Plateau',     'Ecobank',  'CI93EK0080PLAT01134500014944', 12000000),
    'ITA-2PL':  ('Compte Principal ITA 2 Plateaux',  'SGBCI',    'CI93SG0080TWPL01134500014944', 7500000),
    'PIGIER':   ('Compte Principal PIGIER',          'BNI',      'CI93BN0080PIGI01134500014944', 15000000),
    'ISPA':     ('Compte Principal ISPA',            'NSIA Bank','CI93NS0080ISPA01134500014944', 6000000),
}


# ===========================================================================
# COMMANDE
# ===========================================================================

class Command(BaseCommand):
    help = 'Wipe the database and seed all 5 campuses with complete demo data'

    def handle(self, *args, **options):
        print('\n=== NETTOYAGE ===')
        self._clean()

        print('\n=== DONNEES PARTAGEES ===')
        subjs, ay, s1, s2, cc, exam, fee_types, pay_methods = self._shared()

        print('\n=== SUPER ADMIN ===')
        super_admin = self._super_admin()

        all_site_data = {}

        for site_info in SITES_DATA:
            code = site_info['code']
            print(f'\n=== {site_info["name"].upper()} ===')

            site    = self._create_site(site_info)
            prog_type = PROGRAMS_DATA[code][2]
            prog, levels = self._create_program_levels(site, code)
            rooms   = self._create_rooms(site, code)
            admin   = self._create_admin(site, code)
            staff   = self._create_staff(site, code)
            teachers = self._create_teachers(site, code)
            students, parents = self._create_students_parents(site, code)

            s_codes = SUBJECTS_BY_TYPE[prog_type]
            s_map   = {c: subjs[c] for c in s_codes}

            classes  = self._create_classes(site, levels, ay, teachers, code)
            self._create_cst(classes, s_map, teachers)
            sessions = self._create_sessions(classes, s_map, teachers, rooms, code)
            self._create_enrollments(students, classes, ay)
            self._create_finance(site, students, staff, ay, fee_types, pay_methods, code)
            self._create_grades(students, classes[0], s_map, teachers[0], s1, cc, exam)
            self._create_attendance(sessions, students, teachers[0])
            self._create_bank_expenses(site, pay_methods, staff[0], code)

            all_site_data[code] = {
                'site': site, 'admin': admin, 'staff': staff,
                'teachers': teachers, 'students': students, 'parents': parents,
            }
            n_t = len(teachers)
            n_s = len(students)
            print(f'  => {site_info["name"]}: {n_t} enseignants, {n_s} etudiants, {len(sessions)} seances')

        self._summary(all_site_data, super_admin)

    # =========================================================================
    # 1. NETTOYAGE
    # =========================================================================

    def _clean(self):
        from apps.attendance.models import AttendanceRecord, AbsenceRequest, AttendanceSession
        from apps.grades.models import Grade, ReportCard, Evaluation, GradeCategory
        from apps.finance.models import (
            CashTransaction, CashSession, Payment, InvoiceItem, Invoice,
            Expense, CashRegister, BankAccount, PaymentMethod, FeeType,
        )
        from apps.academic.models import (
            Enrollment, ClassSubjectTeacher,
            Session as AcaSession, Room, LevelSubject,
            Class as ClassModel, Semester, TeacherSite, TeacherProfile,
            Level, Subject, Program,
        )
        from apps.students.models import StudentParent, StudentCard, StudentFile, Student, Parent
        from apps.accounts.models import User, UserRole, UserSite
        from apps.core.models import AuditLog, SystemConfig, AcademicYear

        order = [
            AttendanceRecord, AbsenceRequest, AttendanceSession,
            Grade, ReportCard, Evaluation, GradeCategory,
            CashTransaction, CashSession, Payment, InvoiceItem, Invoice,
            Expense, CashRegister, BankAccount, PaymentMethod, FeeType,
            Enrollment, ClassSubjectTeacher, AcaSession, Room, LevelSubject,
            ClassModel, Semester, TeacherSite, TeacherProfile,
            Level, Subject, Program,
            StudentParent, StudentCard, StudentFile, Student, Parent,
            UserRole, UserSite, User,
            AuditLog, SystemConfig, AcademicYear,
        ]
        for model in order:
            try:
                n = model.objects.count()
                model.objects.all().delete()
                if n:
                    print(f'  Supprime {n:>4}  {model.__name__}')
            except Exception as e:
                print(f'  [WARN] {model.__name__}: {e}')

    # =========================================================================
    # 2. DONNEES PARTAGEES
    # =========================================================================

    def _shared(self):
        from apps.academic.models import Subject, Semester
        from apps.core.models import AcademicYear
        from apps.finance.models import FeeType, PaymentMethod
        from apps.grades.models import GradeCategory

        ay = AcademicYear.objects.create(
            name='2024-2025', code='AY-2024-2025',
            start_date=date(2024, 9, 2), end_date=date(2025, 6, 28),
            is_current=True, registration_open=True,
        )
        s1 = Semester.objects.create(
            academic_year=ay, name='S1', label='Semestre 1',
            start_date=date(2024, 9, 2), end_date=date(2025, 1, 31),
            is_current=False,
        )
        s2 = Semester.objects.create(
            academic_year=ay, name='S2', label='Semestre 2',
            start_date=date(2025, 2, 3), end_date=date(2025, 6, 28),
            is_current=True,
        )

        subjs = {}
        for code, name, coef, hpw in SUBJECTS:
            subjs[code] = Subject.objects.create(
                name=name, code=code, coefficient=coef, hours_per_week=hpw,
            )
        print(f'  Matieres: {len(subjs)} | Annee academique: {ay.name}')

        cc   = GradeCategory.objects.create(name='Controle Continu', code='CC',   weight=0.4)
        exam = GradeCategory.objects.create(name='Examen Final',     code='EXAM', weight=0.6)
        print(f'  Categories de notes: CC, EXAM')

        fee_types = {}
        for code, name, amt, recur in [
            ('INSCRIPTION',  "Frais d'inscription",    75000, False),
            ('SCOLARITE-S1', 'Frais de scolarite S1', 300000, True),
            ('SCOLARITE-S2', 'Frais de scolarite S2', 300000, True),
            ('EXAMENS',      "Frais d'examens",         25000, True),
        ]:
            fee_types[code] = FeeType.objects.create(
                name=name, code=code, default_amount=amt, is_recurring=recur,
            )

        pay_methods = {}
        for code, name, online in [
            ('CASH',     'Especes',                   False),
            ('VIREMENT', 'Virement bancaire',          False),
            ('MOBILE',   'Mobile Money (MTN/Orange)',  True),
        ]:
            pay_methods[code] = PaymentMethod.objects.create(
                name=name, code=code, is_online=online,
            )
        print(f'  Types frais: {len(fee_types)} | Modes paiement: {len(pay_methods)}')

        return subjs, ay, s1, s2, cc, exam, fee_types, pay_methods

    def _super_admin(self):
        from apps.accounts.models import User
        u = User.objects.create(
            email='admin@campus.ci',
            first_name='Super', last_name='Admin',
            user_type='ADMIN', is_active=True, is_staff=True, is_superuser=True,
        )
        u.set_password(ADMIN_PWD)
        u.save()
        print(f'  [SUPER]   admin@campus.ci')
        return u

    # =========================================================================
    # 3. CREATION PAR CAMPUS
    # =========================================================================

    def _create_site(self, info):
        from apps.core.models import Site
        site = Site.objects.create(
            code=info['code'], name=info['name'],
            address=info['address'], city=info['city'],
            country='CI', phone=info['phone'], email=info['email'],
            is_main=info['is_main'],
        )
        print(f'  Site: {site.name}')
        return site

    def _create_program_levels(self, site, code):
        from apps.academic.models import Program, Level
        pname, pcode, ptype, pdur = PROGRAMS_DATA[code]

        if pdur == 3:
            levels_def = [('L1', 'Licence 1', 1), ('L2', 'Licence 2', 2), ('L3', 'Licence 3', 3)]
        else:
            levels_def = [('BTS1', 'BTS 1ere annee', 1), ('BTS2', 'BTS 2eme annee', 2)]

        prog = Program.objects.create(
            name=pname, code=pcode,
            description=f'{pname} — {site.name}',
            duration_years=pdur, site=site,
        )
        levels = []
        for lcode, lname, order in levels_def:
            lvl = Level.objects.create(name=lname, code=lcode, order=order, program=prog)
            levels.append(lvl)
        print(f'  Programme: {pcode} ({pdur} ans) | Niveaux: {len(levels)}')
        return prog, levels

    def _create_rooms(self, site, code):
        from apps.academic.models import Room
        pfx = code.replace('-', '')[:4].upper()
        rooms_def = [
            (f'{pfx}-AMPHI', 'Amphitheatre',       150, 'AMPHITHEATER'),
            (f'{pfx}-S101',  'Salle 101',            40, 'CLASSROOM'),
            (f'{pfx}-S102',  'Salle 102',            35, 'CLASSROOM'),
            (f'{pfx}-LABO',  'Laboratoire Info',     30, 'LAB'),
            (f'{pfx}-S201',  'Salle 201',            40, 'CLASSROOM'),
        ]
        rooms = {}
        for rcode, rname, cap, rtype in rooms_def:
            rooms[rcode] = Room.objects.create(
                name=rname, code=rcode, site=site,
                building='Batiment A', floor='RDC',
                capacity=cap, room_type=rtype,
            )
        print(f'  Salles: {len(rooms)}')
        return rooms

    def _make_user(self, site, email, fn, ln, utype, pwd,
                   is_staff=False, is_super=False):
        from apps.accounts.models import User
        u = User.objects.create(
            email=email, first_name=fn, last_name=ln,
            user_type=utype, is_active=True,
            is_staff=is_staff, is_superuser=is_super, site=site,
        )
        u.set_password(pwd)
        u.save()
        return u

    def _create_admin(self, site, code):
        email, fn, ln = ADMINS_DATA[code]
        u = self._make_user(site, email, fn, ln, 'ADMIN', ADMIN_PWD, True, False)
        print(f'  [ADMIN]   {email}')
        return u

    def _create_staff(self, site, code):
        staff = []
        for email, fn, ln in STAFF_DATA[code]:
            u = self._make_user(site, email, fn, ln, 'STAFF', DEMO_PWD)
            print(f'  [STAFF]   {email}')
            staff.append(u)
        return staff

    def _create_teachers(self, site, code):
        from apps.academic.models import TeacherProfile, TeacherSite
        teachers = []
        for email, fn, ln, spec, qual, hire, ctype, rate, emp_id in TEACHERS_DATA[code]:
            u = self._make_user(site, email, fn, ln, 'TEACHER', DEMO_PWD)
            prof = TeacherProfile.objects.create(
                user=u, employee_id=emp_id,
                specialization=spec, qualification=qual,
                hire_date=hire, contract_type=ctype, hourly_rate=rate,
            )
            TeacherSite.objects.create(teacher=prof, site=site, is_primary=True)
            print(f'  [TEACHER] {email}')
            teachers.append(prof)
        return teachers

    def _create_students_parents(self, site, code):
        from apps.students.models import Student, Parent, StudentParent
        students, parents = [], []

        for i, (s_row, p_row) in enumerate(zip(STUDENTS_DATA[code], PARENTS_DATA[code])):
            s_email, s_fn, s_ln, gender, birth_date, birth_place, matricule = s_row
            p_email, p_fn, p_ln, profession, employer, relationship = p_row

            fully_paid = (i % 2 == 1)
            tuition    = 600000
            paid       = tuition if fully_paid else tuition // 2

            su = self._make_user(site, s_email, s_fn, s_ln, 'STUDENT', DEMO_PWD)
            student = Student.objects.create(
                user=su, matricule=matricule, gender=gender,
                birth_date=birth_date, birth_place=birth_place,
                nationality='Ivoirienne',
                address=f'Quartier {i + 1}, Abidjan', city='Abidjan',
                site=site, status='ACTIVE',
                admission_date=date(2024, 9, 2),
                emergency_contact_name=f'{p_fn} {p_ln}',
                emergency_contact_phone=f'+225 07 0{i+1} 0{i+1} 0{i+1} 0{i+1}',
                emergency_contact_relation=relationship,
                registration_fee=75000, registration_fee_paid=True,
                tuition_fee=tuition, total_paid=paid,
                remaining_balance=tuition - paid,
            )
            students.append(student)
            print(f'  [STUDENT] {s_email}')

            pu = self._make_user(site, p_email, p_fn, p_ln, 'PARENT', DEMO_PWD)
            parent = Parent.objects.create(
                user=pu, profession=profession, employer=employer,
                address='Abidjan', city='Abidjan',
                relationship=relationship,
                emergency_contact=f'+225 07 0{i+1} 0{i+1} 0{i+1} 0{i+1}',
            )
            StudentParent.objects.create(
                student=student, parent=parent,
                is_primary=True, can_pickup=True, receives_notifications=True,
            )
            parents.append(parent)
            print(f'  [PARENT]  {p_email}')

        return students, parents

    def _create_classes(self, site, levels, ay, teachers, code):
        from apps.academic.models import Class as ClassModel
        pfx = code.replace('-', '')[:3].upper()
        classes = []
        for lvl in levels[:2]:
            cls = ClassModel.objects.create(
                name=f'{lvl.name} — {site.name[:12]}',
                code=f'{pfx}-{lvl.code}-A',
                level=lvl, academic_year=ay, site=site,
                max_students=40, main_teacher=teachers[0],
            )
            classes.append(cls)
        print(f'  Classes: {[c.code for c in classes]}')
        return classes

    def _create_cst(self, classes, s_map, teachers):
        from apps.academic.models import ClassSubjectTeacher
        s_list = list(s_map.values())
        n_t    = len(teachers)
        for cls in classes:
            for j, subj in enumerate(s_list):
                ClassSubjectTeacher.objects.create(
                    class_obj=cls, subject=subj, teacher=teachers[j % n_t],
                )

    def _create_sessions(self, classes, s_map, teachers, rooms, code):
        from apps.academic.models import Session as AcaSession
        s_list     = list(s_map.values())
        n_t        = len(teachers)
        room_list  = list(rooms.values())
        schedule   = [
            (0, time(8,  0), time(10, 0)),
            (0, time(10,30), time(12,30)),
            (1, time(8,  0), time(10, 0)),
            (1, time(10,30), time(12,30)),
            (2, time(8,  0), time(10, 0)),
            (3, time(8,  0), time(10, 0)),
            (4, time(8,  0), time(10, 0)),
        ]
        all_sessions = []
        cls = classes[0]
        for j, (day, start, end) in enumerate(schedule):
            if j >= len(s_list):
                break
            subj    = s_list[j]
            teacher = teachers[j % n_t]
            room    = room_list[j % len(room_list)]
            sess = AcaSession.objects.create(
                class_obj=cls, subject=subj, teacher=teacher, room=room,
                day_of_week=day, start_time=start, end_time=end,
                is_recurring=True,
            )
            all_sessions.append(sess)
        print(f'  Seances: {len(all_sessions)} (emploi du temps {classes[0].code})')
        return all_sessions

    def _create_enrollments(self, students, classes, ay):
        from apps.academic.models import Enrollment
        cls = classes[0]
        for student in students:
            Enrollment.objects.create(
                student=student, class_obj=cls, academic_year=ay,
                status='ENROLLED',
            )
        print(f'  Inscriptions: {len(students)} -> {cls.code}')

    def _create_finance(self, site, students, staff, ay, fee_types, pay_methods, code):
        from apps.finance.models import Invoice, InvoiceItem, Payment
        receiver = staff[1] if len(staff) > 1 else staff[0]
        pfx      = code.replace('-', '')[:4].upper()

        for i, student in enumerate(students):
            fully_paid = (i % 2 == 1)

            # Facture 1 : Inscription + S1
            inv1 = Invoice.objects.create(
                student=student, site=site, academic_year=ay,
                invoice_number=f'FAC-{pfx}-{i+1:03d}',
                due_date=date(2024, 9, 30),
                amount_paid=375000, created_by=receiver,
            )
            InvoiceItem.objects.create(
                invoice=inv1, fee_type=fee_types['INSCRIPTION'],
                description="Frais d'inscription 2024-2025",
                quantity=1, unit_price=75000, total=75000,
            )
            InvoiceItem.objects.create(
                invoice=inv1, fee_type=fee_types['SCOLARITE-S1'],
                description='Frais de scolarite Semestre 1',
                quantity=1, unit_price=300000, total=300000,
            )
            inv1.save()
            Invoice.objects.filter(pk=inv1.pk).update(issue_date=date(2024, 9, 2))

            p1 = Payment.objects.create(
                payment_number=f'PAY-{pfx}-{i*10+1:04d}',
                invoice=inv1, payment_method=pay_methods['CASH'],
                amount=375000, status='SUCCESS',
                reference=f'REF-{pfx}-S1-{i+1:03d}',
                received_by=receiver, validated_by=receiver,
                validated_at=_dt(date(2024, 9, 5)),
            )
            Payment.objects.filter(pk=p1.pk).update(payment_date=_dt(date(2024, 9, 5)))

            # Facture 2 : S2
            s2_paid = 300000 if fully_paid else 150000
            inv2 = Invoice.objects.create(
                student=student, site=site, academic_year=ay,
                invoice_number=f'FAC-{pfx}-S2-{i+1:03d}',
                due_date=date(2025, 2, 15),
                amount_paid=s2_paid, created_by=receiver,
            )
            InvoiceItem.objects.create(
                invoice=inv2, fee_type=fee_types['SCOLARITE-S2'],
                description='Frais de scolarite Semestre 2',
                quantity=1, unit_price=300000, total=300000,
            )
            inv2.status = 'DRAFT'
            inv2.save()
            Invoice.objects.filter(pk=inv2.pk).update(issue_date=date(2025, 1, 20))

            p2 = Payment.objects.create(
                payment_number=f'PAY-{pfx}-{i*10+2:04d}',
                invoice=inv2, payment_method=pay_methods['MOBILE'],
                amount=s2_paid, status='SUCCESS',
                reference=f'REF-{pfx}-S2-{i+1:03d}',
                received_by=receiver, validated_by=receiver,
                validated_at=_dt(date(2025, 2, 1)),
            )
            Payment.objects.filter(pk=p2.pk).update(payment_date=_dt(date(2025, 2, 1)))

        print(f'  Finance: {len(students)*2} factures, {len(students)*2} paiements')

    def _create_grades(self, students, cls, s_map, teacher, s1, cc, exam):
        from apps.grades.models import Evaluation, Grade, ReportCard
        s_list = list(s_map.values())
        n      = len(students)

        for subj in s_list:
            ev_cc = Evaluation.objects.create(
                title=f'CC1 — {subj.name[:35]}',
                eval_type='DEVOIR', subject=subj, class_group=cls,
                semester=s1, date=date(2024, 11, 15),
                max_score=20, coefficient=1, is_locked=True,
                created_by=teacher.user,
            )
            ev_ex = Evaluation.objects.create(
                title=f'Examen S1 — {subj.name[:30]}',
                eval_type='EXAMEN', subject=subj, class_group=cls,
                semester=s1, date=date(2025, 1, 20),
                max_score=20, coefficient=2, is_locked=True,
                created_by=teacher.user,
            )
            for i, student in enumerate(students):
                base = 12 + (i * 2) % 6
                Grade.objects.create(
                    student=student, subject=subj, class_group=cls,
                    semester=s1, evaluation=ev_cc, category=cc,
                    score=base, max_score=20, date=date(2024, 11, 15),
                    comment='Bon travail' if base >= 14 else 'Peut mieux faire',
                    entered_by=teacher.user,
                )
                Grade.objects.create(
                    student=student, subject=subj, class_group=cls,
                    semester=s1, evaluation=ev_ex, category=exam,
                    score=max(base - 1, 8), max_score=20,
                    date=date(2025, 1, 20),
                    comment='Resultats satisfaisants',
                    entered_by=teacher.user,
                )

        for i, student in enumerate(students):
            base = 12 + (i * 2) % 6
            avg  = round(base * 0.4 + max(base - 1, 8) * 0.6, 2)
            st   = 'HONORS' if avg >= 16 else ('PASS' if avg >= 10 else 'FAIL')
            ReportCard.objects.create(
                student=student, class_group=cls, semester=s1,
                average=str(avg), rank=i + 1, total_students=n,
                status=st,
                subject_averages={
                    str(s.id): {
                        'subject_id': s.id,
                        'subject_name': s.name,
                        'subject_code': s.code,
                        'coefficient': float(s.coefficient),
                        'grades': [],
                        'average': round(avg, 2),
                    }
                    for s in s_list
                },
                teacher_comment='Bon travail. Continuez sur cette lancee.',
                principal_comment='Resultats encourageants.',
                is_published=True,
            )
        print(f'  Notes: {n * len(s_list) * 2} notes | {len(s_list) * 2} evaluations | {n} bulletins')

    def _create_attendance(self, sessions, students, main_teacher):
        from apps.attendance.models import AttendanceSession, AttendanceRecord
        att_dates = [
            date(2025, 5, 5), date(2025, 5, 7), date(2025, 5, 9),
            date(2025, 5, 12), date(2025, 5, 14),
        ]
        records = 0
        for idx, (sess, d) in enumerate(zip(sessions[:5], att_dates)):
            att_sess = AttendanceSession.objects.create(
                session=sess, date=d, status='CLOSED',
                opened_by=main_teacher.user,
            )
            for si, student in enumerate(students):
                is_absent = (si == 0 and idx == 2)
                AttendanceRecord.objects.create(
                    attendance_session=att_sess, student=student,
                    status='ABSENT' if is_absent else 'PRESENT',
                    check_in_method='MANUAL',
                    marked_by=main_teacher.user,
                )
                records += 1
        print(f'  Presences: {records} enregistrements')

    def _create_bank_expenses(self, site, pay_methods, approver, code):
        from apps.finance.models import BankAccount, Expense, CashRegister
        pfx = code.replace('-', '')[:4].upper()

        bname, bbank, bacct, bbal = BANK_DATA[code]
        BankAccount.objects.create(
            name=bname, bank_name=bbank,
            account_number=bacct,
            account_type='CHECKING', balance=bbal,
            currency='XOF', site=site,
        )

        expenses = [
            ('Salaires enseignants — Mai 2025',      'SALARY',      2500000, date(2025, 5, 31)),
            ('Salaires personnel administratif',     'SALARY',       800000, date(2025, 5, 31)),
            ("Facture electricite — Mai 2025",       'UTILITIES',    150000, date(2025, 5, 15)),
            ('Fournitures de bureau',                'SUPPLIES',      45000, date(2025, 5, 10)),
            ('Maintenance informatique',             'MAINTENANCE',  180000, date(2025, 4, 20)),
            ('Abonnement Internet et telephonie',    'UTILITIES',     75000, date(2025, 5,  1)),
            ('Nettoyage et entretien des locaux',    'MAINTENANCE',   60000, date(2025, 4,  8)),
        ]
        for label, cat, amt, d in expenses:
            Expense.objects.create(
                site=site, label=label, category=cat, amount=amt, date=d,
                payment_method=pay_methods['VIREMENT'],
                status='PAID', approved_by=approver,
            )

        CashRegister.objects.create(
            name=f'Caisse Scolarite {site.name[:15]}',
            code=f'CAISSE-{pfx}',
            site=site, current_balance=350000, is_open=True,
        )
        print(f'  Banque: 1 compte | Depenses: {len(expenses)} | Caisse: 1')

    # =========================================================================
    # 4. RESUME FINAL
    # =========================================================================

    def _summary(self, all_site_data, super_admin):
        from apps.accounts.models import User
        from apps.grades.models import Grade, Evaluation
        from apps.attendance.models import AttendanceRecord
        from apps.finance.models import Payment, Invoice

        sep = '=' * 88
        print('\n' + sep)
        print('SEED COMPLET — COMPTES PAR CAMPUS')
        print(sep)
        print(f'  {"Role":<14} {"Email":<40} {"Mot de passe":<14}')
        print(f'  {"-"*13} {"-"*39} {"-"*13}')

        print(f'\n  [SUPER ADMIN]')
        print(f'  {"Super Admin":<14} {"admin@campus.ci":<40} {ADMIN_PWD:<14}')

        for code, data in all_site_data.items():
            site_name = data["site"].name
            print(f'\n  [{site_name.upper()}]')

            email, fn, ln = ADMINS_DATA[code]
            print(f'  {"Admin":<14} {email:<40} {ADMIN_PWD:<14}')

            for email, fn, ln in STAFF_DATA[code]:
                print(f'  {"Staff":<14} {email:<40} {DEMO_PWD:<14}')

            for row in TEACHERS_DATA[code]:
                print(f'  {"Enseignant":<14} {row[0]:<40} {DEMO_PWD:<14}')

            for row in STUDENTS_DATA[code]:
                print(f'  {"Etudiant":<14} {row[0]:<40} {DEMO_PWD:<14}')

            for row in PARENTS_DATA[code]:
                print(f'  {"Parent":<14} {row[0]:<40} {DEMO_PWD:<14}')

        print('\n' + sep)
        print('STATISTIQUES GLOBALES')
        print(sep)
        print(f'  Utilisateurs  : {User.objects.count()}')
        print(f'  Notes         : {Grade.objects.count()}')
        print(f'  Evaluations   : {Evaluation.objects.count()}')
        print(f'  Presences     : {AttendanceRecord.objects.count()}')
        print(f'  Paiements     : {Payment.objects.count()}')
        print(f'  Factures      : {Invoice.objects.count()}')
        print(sep + '\n')
