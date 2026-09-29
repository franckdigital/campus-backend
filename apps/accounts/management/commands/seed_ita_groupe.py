"""
seed_ita_groupe.py — Seed complet du groupe ITA (6 campus)
Siege : ITA Marcory (site principal)
Autres campus : ITA 2 Plateaux, ITA Yopougon, ITA Abobo, ITA Bouake, ITA San-Pedro

Cree pour chaque site : filiere/niveaux, salles, admin, personnel, enseignants,
etudiants + parents (annees academiques 2025-2026 ET 2026-2027, avec progression
de promotion d'une annee a l'autre), inscriptions, baremes de scolarite +
echeanciers, factures/paiements (certains etudiants a jour, d'autres non),
notes/evaluations/bulletins, cours classiques (chapitres/lecons), quiz, devoirs
+ soumissions, examens securises + sessions, et un peu de presence.

Usage: python manage.py seed_ita_groupe [--reset]
ATTENTION : --reset efface toutes les donnees pedagogiques/financieres existantes.
"""
import random
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

ADMIN_PWD = 'Admin2025!'
DEMO_PWD = 'Campus2025!'

RNG = random.Random(42)


def _dt(d, h=10, m=0):
    return timezone.make_aware(datetime(d.year, d.month, d.day, h, m))


# ===========================================================================
# DONNEES STATIQUES
# ===========================================================================

SITES_DATA = [
    {'code': 'ITA-MARC', 'name': 'ITA Marcory', 'address': 'Rue des Tulipes, Zone 4, Marcory',
     'city': 'Abidjan', 'phone': '+225 27 21 35 10 00', 'email': 'marcory@ita.ci', 'is_main': True},
    {'code': 'ITA-2PL', 'name': 'ITA 2 Plateaux', 'address': 'Rue des Jardins, Cocody 2 Plateaux',
     'city': 'Abidjan', 'phone': '+225 27 22 48 05 00', 'email': 'deuxplateaux@ita.ci', 'is_main': False},
    {'code': 'ITA-YOPO', 'name': 'ITA Yopougon', 'address': 'Boulevard du Banco, Yopougon Niangon',
     'city': 'Abidjan', 'phone': '+225 27 23 40 15 00', 'email': 'yopougon@ita.ci', 'is_main': False},
    {'code': 'ITA-ABOB', 'name': 'ITA Abobo', 'address': 'Avenue Emile Timothee, Abobo',
     'city': 'Abidjan', 'phone': '+225 27 24 50 20 00', 'email': 'abobo@ita.ci', 'is_main': False},
    {'code': 'ITA-BOUA', 'name': 'ITA Bouake', 'address': 'Rue du Commerce, Centre-ville',
     'city': 'Bouake', 'phone': '+225 31 63 25 10 00', 'email': 'bouake@ita.ci', 'is_main': False},
    {'code': 'ITA-SANP', 'name': 'ITA San-Pedro', 'address': 'Avenue du Port, San-Pedro',
     'city': 'San-Pedro', 'phone': '+225 34 71 12 40 00', 'email': 'sanpedro@ita.ci', 'is_main': False},
]

SUBJECTS = [
    # code, nom, coefficient, heures/semaine
    ('ALG101', 'Algorithmique et structures de donnees', 4, 4),
    ('PRG101', 'Programmation Python', 3, 3),
    ('PRG201', 'Programmation Java', 3, 3),
    ('MAT101', 'Mathematiques discretes', 3, 3),
    ('MAT201', 'Analyse et algebre lineaire', 3, 3),
    ('RES101', 'Reseaux informatiques', 3, 3),
    ('BDD101', 'Bases de donnees relationnelles', 3, 4),
    ('WEB201', 'Developpement web full-stack', 4, 4),
    ('SYS201', "Systemes d'exploitation", 3, 3),
    ('SEC101', 'Securite informatique', 3, 3),
    ('ANG101', 'Anglais technique', 2, 2),
    ('COM101', 'Communication professionnelle', 2, 2),
    ('GES101', 'Introduction a la gestion', 3, 3),
    ('PRJ101', 'Gestion de projets informatiques', 3, 3),
]

# 7 matieres par site (piochees dans le pool ci-dessus)
SUBJECTS_BY_SITE = {
    'ITA-MARC': ['ALG101', 'PRG101', 'MAT101', 'RES101', 'BDD101', 'ANG101', 'COM101'],
    'ITA-2PL': ['SYS201', 'PRG201', 'MAT201', 'BDD101', 'PRJ101', 'ANG101', 'COM101'],
    'ITA-YOPO': ['ALG101', 'PRG101', 'PRG201', 'MAT101', 'WEB201', 'ANG101', 'COM101'],
    'ITA-ABOB': ['ALG101', 'MAT101', 'RES101', 'GES101', 'BDD101', 'ANG101', 'COM101'],
    'ITA-BOUA': ['ALG101', 'MAT201', 'SYS201', 'BDD101', 'SEC101', 'ANG101', 'COM101'],
    'ITA-SANP': ['PRG101', 'MAT101', 'WEB201', 'GES101', 'PRJ101', 'ANG101', 'COM101'],
}

ADMINS_DATA = {
    'ITA-MARC': ('directeur@ita-marc.ci', 'Koffi Emmanuel', 'Yao'),
    'ITA-2PL': ('directeur@ita-2pl.ci', 'Bernard', 'Atta'),
    'ITA-YOPO': ('directeur@ita-yopo.ci', 'Bamba', 'Diomande'),
    'ITA-ABOB': ('directeur@ita-abob.ci', 'Solange', "N'Dri"),
    'ITA-BOUA': ('directeur@ita-boua.ci', 'Kouassi', 'Yao'),
    'ITA-SANP': ('directeur@ita-sanp.ci', 'Firmin', 'Gogoua'),
}

STAFF_DATA = {
    'ITA-MARC': [('s.koffi@ita-marc.ci', 'Sandrine', 'Koffi', 'SCOLARITE'),
                 ('p.assouman@ita-marc.ci', 'Pierre', 'Assouman', 'COMPTABILITE')],
    'ITA-2PL': [('a.gnagne@ita-2pl.ci', 'Adjoua', 'Gnagne', 'SCOLARITE'),
                ('k.lago@ita-2pl.ci', 'Kofi', 'Lago', 'COMPTABILITE')],
    'ITA-YOPO': [('f.coulibaly@ita-yopo.ci', 'Fatou', 'Coulibaly', 'SCOLARITE'),
                 ('m.kone@ita-yopo.ci', 'Moussa', 'Kone', 'COMPTABILITE')],
    'ITA-ABOB': [('r.gohi@ita-abob.ci', 'Raissa', 'Gohi', 'SCOLARITE'),
                 ('e.oura@ita-abob.ci', 'Eric', 'Oura', 'COMPTABILITE')],
    'ITA-BOUA': [('a.traore@ita-boua.ci', 'Aminata', 'Traore', 'SCOLARITE'),
                 ('b.kouyate@ita-boua.ci', 'Boubacar', 'Kouyate', 'COMPTABILITE')],
    'ITA-SANP': [('c.digbeu@ita-sanp.ci', 'Clarisse', 'Digbeu', 'SCOLARITE'),
                 ('y.zadi@ita-sanp.ci', 'Yannick', 'Zadi', 'COMPTABILITE')],
}

TEACHERS_DATA = {
    'ITA-MARC': [
        ('j.kouassi@ita-marc.ci', 'Jean-Baptiste', 'Kouassi', 'Informatique & Algorithmes', 'Doctorat Informatique', date(2019, 9, 1), 'PERMANENT', 15000, 'MARC-P001'),
        ('f.bamba@ita-marc.ci', 'Fatoumata', 'Bamba', 'Mathematiques Appliquees', 'Master Mathematiques', date(2020, 1, 15), 'PERMANENT', 12000, 'MARC-P002'),
        ('e.ngoran@ita-marc.ci', 'Eric', 'Ngoran', 'Reseaux & Securite', 'Ingenieur Reseaux', date(2021, 9, 1), 'CONTRACT', 10000, 'MARC-P003'),
        ('c.yao@ita-marc.ci', 'Christiane', 'Yao', 'Bases de donnees & Web', 'Master Genie Logiciel', date(2020, 9, 1), 'PERMANENT', 11000, 'MARC-P004'),
    ],
    'ITA-2PL': [
        ('a.kone@ita-2pl.ci', 'Aboubakar', 'Kone', 'Developpement Web & Mobile', 'Master Developpement', date(2020, 9, 1), 'PERMANENT', 13000, '2PL-P001'),
        ('m.toure@ita-2pl.ci', 'Mariam', 'Toure', 'Mathematiques', 'Licence Math-Info', date(2021, 9, 1), 'CONTRACT', 9000, '2PL-P002'),
        ('p.ouedraogo@ita-2pl.ci', 'Pascal', 'Ouedraogo', 'Reseaux Informatiques', 'Licence Pro Reseaux', date(2022, 1, 1), 'CONTRACT', 8000, '2PL-P003'),
        ('l.aka@ita-2pl.ci', 'Larissa', 'Aka', 'Gestion de projets', 'Master Management IT', date(2022, 9, 1), 'PERMANENT', 12000, '2PL-P004'),
    ],
    'ITA-YOPO': [
        ('k.bamba@ita-yopo.ci', 'Karim', 'Bamba', 'Algorithmique & Programmation', 'Doctorat Informatique', date(2021, 9, 1), 'PERMANENT', 14000, 'YOPO-P001'),
        ('r.coulibaly@ita-yopo.ci', 'Rodrigue', 'Coulibaly', 'Bases de donnees & Web', 'Master Informatique', date(2022, 1, 1), 'PERMANENT', 12000, 'YOPO-P002'),
        ('n.diallo@ita-yopo.ci', 'Nathalie', 'Diallo', 'Reseaux & Systemes', 'Ingenieur Informatique', date(2022, 9, 1), 'CONTRACT', 10000, 'YOPO-P003'),
        ('s.yao@ita-yopo.ci', 'Sylvain', 'Yao', 'Anglais technique', 'Master LEA', date(2023, 1, 1), 'CONTRACT', 8000, 'YOPO-P004'),
    ],
    'ITA-ABOB': [
        ('d.kadio@ita-abob.ci', 'Didier', 'Kadio', 'Algorithmique', 'Master Informatique', date(2021, 9, 1), 'PERMANENT', 12000, 'ABOB-P001'),
        ('h.gnahore@ita-abob.ci', 'Henriette', 'Gnahore', 'Mathematiques', 'Licence Math-Info', date(2022, 9, 1), 'CONTRACT', 9000, 'ABOB-P002'),
        ('o.silue@ita-abob.ci', 'Ousmane', 'Silue', 'Reseaux & Gestion', 'Ingenieur Reseaux', date(2022, 9, 1), 'CONTRACT', 9500, 'ABOB-P003'),
        ('v.aya@ita-abob.ci', 'Viviane', 'Aya', 'Bases de donnees', 'Master Genie Logiciel', date(2023, 9, 1), 'PERMANENT', 11500, 'ABOB-P004'),
    ],
    'ITA-BOUA': [
        ('s.ouattara@ita-boua.ci', 'Seydou', 'Ouattara', 'Securite & Reseaux', 'Master Informatique', date(2020, 9, 1), 'PERMANENT', 13000, 'BOUA-P001'),
        ('d.yao@ita-boua.ci', 'Delphine', 'Yao', 'Mathematiques & Systemes', 'Licence Pro Informatique', date(2021, 9, 1), 'PERMANENT', 11000, 'BOUA-P002'),
        ('m.toure@ita-boua.ci', 'Mamadou', 'Toure', 'Programmation & Algorithmique', 'Ingenieur Logiciel', date(2022, 1, 1), 'CONTRACT', 9000, 'BOUA-P003'),
        ('n.kra@ita-boua.ci', 'Nadege', 'Kra', 'Anglais technique', 'Master LEA', date(2022, 9, 1), 'CONTRACT', 8000, 'BOUA-P004'),
    ],
    'ITA-SANP': [
        ('g.pehe@ita-sanp.ci', 'Guy', 'Pehe', 'Developpement Web', 'Master Developpement', date(2021, 9, 1), 'PERMANENT', 12500, 'SANP-P001'),
        ('m.doukoure@ita-sanp.ci', 'Mireille', 'Doukoure', 'Mathematiques & Gestion', 'Master Gestion', date(2022, 1, 1), 'CONTRACT', 9500, 'SANP-P002'),
        ('j.gadou@ita-sanp.ci', 'Jonas', 'Gadou', 'Gestion de projets', 'Ingenieur Informatique', date(2022, 9, 1), 'CONTRACT', 9000, 'SANP-P003'),
        ('a.kessy@ita-sanp.ci', 'Adele', 'Kessy', 'Anglais technique', 'Licence LEA', date(2023, 1, 1), 'CONTRACT', 8000, 'SANP-P004'),
    ],
}

MALE_FIRST = ['Ibrahim', 'Kevin', 'Yannick', 'Mohamed', 'Junior', 'Abdoul', 'Siaka', 'David',
              'Amani', 'Cheick', 'Evariste', 'Gontran', 'Ibrahim', 'Franck', 'Steve', 'Arnaud',
              'Wilfried', 'Herve', 'Lassina', 'Boris']
FEMALE_FIRST = ['Aicha', 'Rebecca', 'Mariam', 'Estelle', 'Patricia', 'Laurence', 'Celine',
                'Brigitte', 'Danielle', 'Fatima', 'Hermine', 'Juliette', 'Nadia', 'Solange',
                'Grace', 'Vanessa', 'Christelle', 'Ornella', 'Prisca', 'Audrey']
LAST_NAMES = ['Kone', 'Traore', 'Kouadio', 'Adjoua', 'Bile', 'Ake', 'Dosso', 'Gnaoule', 'Bah',
              'Ettien', 'Sylla', 'Ouattara', 'Tape', 'Yeboua', 'Akpan', 'Konan', 'Toure',
              'Diomande', 'Koffi', 'Berte', 'Bamba', 'Sanogo', 'Diallo', 'Yao', 'Kra', 'Gadou',
              'Digbeu', 'Zadi', 'Silue', 'Gohi']
BIRTH_PLACES = ['Abidjan', 'Bouake', 'Yamoussoukro', 'Daloa', 'Korhogo', 'Man', 'San-Pedro',
                'Abengourou', 'Gagnoa', 'Divo']
PROFESSIONS = [('Ingenieur', 'BNETD'), ('Commercante', 'Auto-entrepreneur'),
               ('Fonctionnaire', 'Min. Education'), ('Infirmiere', 'CHU'),
               ('Enseignant', 'Lycee Technique'), ('Chauffeur', 'SOTRA'),
               ('Technicien', 'CIE'), ('Menagere', ''), ('Gendarme', 'FACI'),
               ('Agriculteur', 'Auto-entrepreneur')]

BANK_DATA = {
    'ITA-MARC': ('Compte Principal ITA Marcory', 'BICICI', 'CI93BI0080MARC01134500014944', 9500000),
    'ITA-2PL': ('Compte Principal ITA 2 Plateaux', 'SGBCI', 'CI93SG0080TWPL01134500014944', 7500000),
    'ITA-YOPO': ('Compte Principal ITA Yopougon', 'Ecobank', 'CI93EK0080YOPO01134500014944', 8500000),
    'ITA-ABOB': ('Compte Principal ITA Abobo', 'NSIA Banque', 'CI93NS0080ABOB01134500014944', 6000000),
    'ITA-BOUA': ('Compte Principal ITA Bouake', 'SGBCI', 'CI93SG0080BOUA01134500014944', 7000000),
    'ITA-SANP': ('Compte Principal ITA San-Pedro', 'Ecobank', 'CI93EK0080SANP01134500014944', 5500000),
}

# Nombre de nouveaux etudiants L1 crees a chaque annee academique, par site
NEW_L1_PER_SITE = {
    'ITA-MARC': 8, 'ITA-2PL': 6, 'ITA-YOPO': 6, 'ITA-ABOB': 5, 'ITA-BOUA': 5, 'ITA-SANP': 5,
}

TUITION_BY_LEVEL = {'L1': 550000, 'L2': 600000, 'L3': 650000}


# ===========================================================================
# COMMANDE
# ===========================================================================

class Command(BaseCommand):
    help = "Seed complet du groupe ITA : 6 campus, 2 annees academiques, tout le contenu"

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Efface les donnees existantes avant de seeder')

    def handle(self, *args, **options):
        if options['reset']:
            print('\n=== NETTOYAGE ===')
            self._clean()

        print('\n=== DONNEES PARTAGEES ===')
        subjs, ay1, ay2, sems, cc, exam_cat, pay_methods, fee_type_scol = self._shared()

        print('\n=== SUPER ADMIN ===')
        self._super_admin()

        all_stats = []
        for site_info in SITES_DATA:
            code = site_info['code']
            print(f'\n=== {site_info["name"].upper()} ===')

            site = self._create_site(site_info)
            prog, levels = self._create_program_levels(site, code)
            rooms = self._create_rooms(site, code)
            self._create_admin(site, code)
            staff = self._create_staff(site, code)
            teachers = self._create_teachers(site, code)

            s_codes = SUBJECTS_BY_SITE[code]
            s_map = {c: subjs[c] for c in s_codes}

            fee_configs = self._create_fee_configs(site, prog, levels, ay1, ay2)

            # --- Annee 1 : 2025-2026 --------------------------------------
            classes_ay1 = self._create_classes(site, levels, ay1, teachers, code)
            self._create_cst(classes_ay1, s_map, teachers)
            sessions_ay1 = self._create_sessions(classes_ay1, s_map, teachers, rooms, code)

            students_l1_ay1, parents_l1 = self._create_cohort(site, code, levels[0], 'A25', NEW_L1_PER_SITE[code], 2025)
            students_l2_ay1, parents_l2 = self._create_cohort(site, code, levels[1], 'A24', max(NEW_L1_PER_SITE[code] - 2, 3), 2024)
            students_l3_ay1, parents_l3 = self._create_cohort(site, code, levels[2], 'A23', max(NEW_L1_PER_SITE[code] - 3, 3), 2023)

            # L'annee "courante" pilote le signal d'auto-facturation
            # (ensure_student_invoices resout toujours le bareme de
            # l'AcademicYear.is_current=True) : on la bascule sur AY1 le
            # temps de cette section pour que les factures auto-creees a
            # l'inscription tombent sur le bon bareme/la bonne annee.
            self._set_current_year(ay1)

            self._enroll(students_l1_ay1, classes_ay1[0], ay1)
            self._enroll(students_l2_ay1, classes_ay1[1], ay1)
            self._enroll(students_l3_ay1, classes_ay1[2], ay1)

            self._create_finance(site, students_l1_ay1, staff, ay1, fee_configs['L1'], pay_methods, fee_type_scol, code, 'L1')
            self._create_finance(site, students_l2_ay1, staff, ay1, fee_configs['L2'], pay_methods, fee_type_scol, code, 'L2')
            self._create_finance(site, students_l3_ay1, staff, ay1, fee_configs['L3'], pay_methods, fee_type_scol, code, 'L3')

            self._create_grades(students_l1_ay1, classes_ay1[0], s_map, teachers[0], sems['ay1_s1'], sems['ay1_s2'], cc, exam_cat)
            self._create_grades(students_l2_ay1, classes_ay1[1], s_map, teachers[1 % len(teachers)], sems['ay1_s1'], sems['ay1_s2'], cc, exam_cat)
            self._create_grades(students_l3_ay1, classes_ay1[2], s_map, teachers[2 % len(teachers)], sems['ay1_s1'], sems['ay1_s2'], cc, exam_cat)

            elearn = self._create_elearning(classes_ay1[0], s_map, teachers, students_l1_ay1, code)
            self._create_attendance(sessions_ay1, students_l1_ay1, teachers[0])
            self._create_bank_expenses(site, pay_methods, staff[0], code)

            # --- Annee 2 : 2026-2027 (progression de promotion) ----------
            classes_ay2 = self._create_classes(site, levels, ay2, teachers, code)
            self._create_cst(classes_ay2, s_map, teachers)

            # L3 -> diplomes (ne progressent pas), L2 -> L3, L1 -> L2, + nouveaux L1
            for st in students_l3_ay1:
                st.status = 'GRADUATED'
                st.graduation_date = date(2026, 6, 30)
                st.save(update_fields=['status', 'graduation_date'])

            students_l2_ay2 = students_l1_ay1  # promotion L1 -> L2
            students_l3_ay2 = students_l2_ay1  # promotion L2 -> L3
            students_l1_ay2, parents_l1b = self._create_cohort(site, code, levels[0], 'A26', NEW_L1_PER_SITE[code], 2026)

            self._set_current_year(ay2)

            self._enroll(students_l1_ay2, classes_ay2[0], ay2)
            self._enroll(students_l2_ay2, classes_ay2[1], ay2)
            self._enroll(students_l3_ay2, classes_ay2[2], ay2)

            self._create_finance(site, students_l1_ay2, staff, ay2, fee_configs['L1'], pay_methods, fee_type_scol, code, 'L1')
            self._create_finance(site, students_l2_ay2, staff, ay2, fee_configs['L2'], pay_methods, fee_type_scol, code, 'L2')
            self._create_finance(site, students_l3_ay2, staff, ay2, fee_configs['L3'], pay_methods, fee_type_scol, code, 'L3')

            self._create_grades(students_l1_ay2, classes_ay2[0], s_map, teachers[0], sems['ay2_s1'], None, cc, exam_cat)

            n_students_total = len(students_l1_ay1) + len(students_l2_ay1) + len(students_l3_ay1) + len(students_l1_ay2)
            print(f'  => {site_info["name"]}: {len(teachers)} enseignants, {n_students_total} etudiants (2 annees), {len(sessions_ay1)} seances')
            all_stats.append((site_info['name'], len(teachers), n_students_total))

        self._summary(all_stats)

    # =========================================================================
    # NETTOYAGE
    # =========================================================================

    def _clean(self):
        from apps.attendance.models import AttendanceRecord, AbsenceRequest, AttendanceSession
        from apps.grades.models import Grade, ReportCard, Evaluation, GradeCategory
        from apps.elearning.models import (
            ExamSession, SecureExam, AssignmentCorrection, AssignmentSubmission, Assignment,
            AttemptAnswer, QuizAttempt, Choice, Question, Quiz, LessonProgress,
            LessonAttachment, Lesson, Chapter,
        )
        from apps.finance.models import (
            CashTransaction, CashSession, Payment, InvoiceItem, Invoice,
            Expense, CashRegister, BankAccount, PaymentMethod, FeeType,
            FeeInstallment, FeeConfiguration,
        )
        from apps.academic.models import (
            Enrollment, ClassSubjectTeacher, Session as AcaSession, Room, LevelSubject,
            Class as ClassModel, Semester, TeacherSite, TeacherProfile, Level, Subject, Program,
        )
        from apps.students.models import StudentParent, StudentCard, StudentFile, Student, Parent
        from apps.staff.models import StaffProfile
        from apps.accounts.models import User, UserRole, UserSite
        from apps.core.models import AuditLog, SystemConfig, AcademicYear

        order = [
            ExamSession, SecureExam, AssignmentCorrection, AssignmentSubmission, Assignment,
            AttemptAnswer, QuizAttempt, Choice, Question, Quiz, LessonProgress,
            LessonAttachment, Lesson, Chapter,
            AttendanceRecord, AbsenceRequest, AttendanceSession,
            Grade, ReportCard, Evaluation, GradeCategory,
            CashTransaction, CashSession, Payment, InvoiceItem, Invoice,
            Expense, CashRegister, BankAccount, PaymentMethod, FeeType,
            FeeInstallment, FeeConfiguration,
            Enrollment, ClassSubjectTeacher, AcaSession, Room, LevelSubject,
            ClassModel, Semester, TeacherSite, TeacherProfile, Level, Subject, Program,
            StudentParent, StudentCard, StudentFile, Student, Parent, StaffProfile,
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
    # DONNEES PARTAGEES
    # =========================================================================

    def _shared(self):
        from apps.academic.models import Subject, Semester
        from apps.core.models import AcademicYear
        from apps.finance.models import FeeType, PaymentMethod
        from apps.grades.models import GradeCategory

        # is_current sera bascule pendant le seed (voir _set_current_year) pour que
        # le signal d'auto-facturation resolve le bon bareme par annee ; la valeur
        # posee ici ne sert que de defaut initial avant le premier site traite.
        ay1, _ = AcademicYear.objects.get_or_create(
            code='AY-2025-2026',
            defaults=dict(name='2025-2026', start_date=date(2025, 9, 1), end_date=date(2026, 6, 30),
                          is_current=False, registration_open=False),
        )
        ay2, _ = AcademicYear.objects.get_or_create(
            code='AY-2026-2027',
            defaults=dict(name='2026-2027', start_date=date(2026, 9, 1), end_date=date(2027, 6, 30),
                          is_current=True, registration_open=True),
        )

        sems = {}
        sems['ay1_s1'] = Semester.objects.create(academic_year=ay1, name='S1', label='Semestre 1',
                                                   start_date=date(2025, 9, 1), end_date=date(2026, 1, 31), is_current=False)
        sems['ay1_s2'] = Semester.objects.create(academic_year=ay1, name='S2', label='Semestre 2',
                                                   start_date=date(2026, 2, 2), end_date=date(2026, 6, 30), is_current=True)
        sems['ay2_s1'] = Semester.objects.create(academic_year=ay2, name='S1', label='Semestre 1',
                                                   start_date=date(2026, 9, 1), end_date=date(2027, 1, 31), is_current=False)
        sems['ay2_s2'] = Semester.objects.create(academic_year=ay2, name='S2', label='Semestre 2',
                                                   start_date=date(2027, 2, 1), end_date=date(2027, 6, 30), is_current=False)

        subjs = {}
        for code, name, coef, hpw in SUBJECTS:
            subjs[code], _ = Subject.objects.get_or_create(
                code=code, defaults=dict(name=name, coefficient=coef, hours_per_week=hpw),
            )
        print(f'  Matieres: {len(subjs)} | Annees academiques: {ay1.name}, {ay2.name}')

        cc, _ = GradeCategory.objects.get_or_create(code='CC', defaults=dict(name='Controle Continu', weight=0.4))
        exam_cat, _ = GradeCategory.objects.get_or_create(code='EXAM', defaults=dict(name='Examen Final', weight=0.6))

        fee_type_scol, _ = FeeType.objects.get_or_create(
            code='SCOLARITE', defaults=dict(name='Frais de scolarite', default_amount=0, is_recurring=True),
        )

        pay_methods = {}
        for pcode, name, online in [
            ('CASH', 'Especes', False),
            ('VIREMENT', 'Virement bancaire', False),
            ('MOBILE', 'Mobile Money (MTN/Orange)', True),
        ]:
            pay_methods[pcode], _ = PaymentMethod.objects.get_or_create(
                code=pcode, defaults=dict(name=name, is_online=online),
            )
        print(f'  Modes de paiement: {len(pay_methods)} | Categories de notes: CC, EXAM')

        return subjs, ay1, ay2, sems, cc, exam_cat, pay_methods, fee_type_scol

    def _super_admin(self):
        from apps.accounts.models import User
        u, created = User.objects.get_or_create(
            email='admin@campus.ci',
            defaults=dict(first_name='Super', last_name='Admin', user_type='ADMIN',
                           is_active=True, is_staff=True, is_superuser=True),
        )
        if created:
            u.set_password(ADMIN_PWD)
            u.save()
        print('  [SUPER]   admin@campus.ci')
        return u

    # =========================================================================
    # CREATION PAR CAMPUS — structure
    # =========================================================================

    def _create_site(self, info):
        from apps.core.models import Site
        site, _ = Site.objects.get_or_create(
            code=info['code'],
            defaults=dict(name=info['name'], address=info['address'], city=info['city'],
                           phone=info['phone'], email=info['email'], is_main=info['is_main'], is_active=True),
        )
        print(f'  Site: {site.name}')
        return site

    def _create_program_levels(self, site, code):
        from apps.academic.models import Program, Level
        prog, _ = Program.objects.get_or_create(
            code=f'LI-{code}',
            defaults=dict(name='Licence Informatique', description=f'Licence Informatique — {site.name}',
                          duration_years=3, site=site),
        )
        levels = []
        for lcode, lname, order in [('L1', 'Licence 1', 1), ('L2', 'Licence 2', 2), ('L3', 'Licence 3', 3)]:
            lvl, _ = Level.objects.get_or_create(program=prog, code=lcode, defaults=dict(name=lname, order=order))
            levels.append(lvl)
        print(f'  Programme: {prog.code} | Niveaux: {[l.code for l in levels]}')
        return prog, levels

    def _create_rooms(self, site, code):
        from apps.academic.models import Room
        pfx = code.replace('-', '')[:4].upper()
        rooms_def = [
            (f'{pfx}-AMPHI', 'Amphitheatre', 150, 'AMPHITHEATER'),
            (f'{pfx}-S101', 'Salle 101', 40, 'CLASSROOM'),
            (f'{pfx}-S102', 'Salle 102', 35, 'CLASSROOM'),
            (f'{pfx}-LABO', 'Laboratoire Info', 30, 'LAB'),
            (f'{pfx}-S201', 'Salle 201', 40, 'CLASSROOM'),
        ]
        rooms = {}
        for rcode, rname, cap, rtype in rooms_def:
            rooms[rcode], _ = Room.objects.get_or_create(
                code=rcode, site=site,
                defaults=dict(name=rname, building='Batiment A', floor='RDC', capacity=cap, room_type=rtype),
            )
        print(f'  Salles: {len(rooms)}')
        return rooms

    def _make_user(self, site, email, fn, ln, utype, pwd, is_staff=False, is_super=False):
        from apps.accounts.models import User
        u, created = User.objects.get_or_create(
            email=email,
            defaults=dict(first_name=fn, last_name=ln, user_type=utype, is_active=True,
                          is_staff=is_staff, is_superuser=is_super, site=site),
        )
        if created:
            u.set_password(pwd)
            u.save()
        return u

    def _create_admin(self, site, code):
        email, fn, ln = ADMINS_DATA[code]
        self._make_user(site, email, fn, ln, 'ADMIN', ADMIN_PWD, True, False)
        print(f'  [ADMIN]   {email}')

    def _create_staff(self, site, code):
        from apps.staff.models import StaffProfile
        staff = []
        for email, fn, ln, dept in STAFF_DATA[code]:
            u = self._make_user(site, email, fn, ln, 'STAFF', DEMO_PWD)
            StaffProfile.objects.get_or_create(
                user=u, defaults=dict(employee_id=f'{code}-STF-{email[:3].upper()}',
                                       department=dept, position='Agent', hire_date=date(2023, 9, 1),
                                       contract_type='PERMANENT', site=site),
            )
            staff.append(u)
        print(f'  Personnel: {len(staff)}')
        return staff

    def _create_teachers(self, site, code):
        from apps.academic.models import TeacherProfile, TeacherSite
        teachers = []
        for email, fn, ln, spec, qual, hire, ctype, rate, emp_id in TEACHERS_DATA[code]:
            u = self._make_user(site, email, fn, ln, 'TEACHER', DEMO_PWD)
            prof, created = TeacherProfile.objects.get_or_create(
                user=u, defaults=dict(employee_id=emp_id, specialization=spec, qualification=qual,
                                       hire_date=hire, contract_type=ctype, hourly_rate=rate),
            )
            TeacherSite.objects.get_or_create(teacher=prof, site=site, defaults=dict(is_primary=True))
            teachers.append(prof)
        print(f'  Enseignants: {len(teachers)}')
        return teachers

    def _set_current_year(self, ay):
        """Bascule quelle AcademicYear est is_current=True. Le signal
        finance.on_enrollment_save (ensure_student_invoices) resout
        TOUJOURS le bareme via AcademicYear.get_current() quelle que soit
        l'annee de l'Enrollment cree — sans ce bascule, les factures
        auto-creees pour l'annee 2 tomberaient sur le bareme de l'annee 1."""
        from apps.core.models import AcademicYear
        AcademicYear.objects.exclude(pk=ay.pk).update(is_current=False)
        AcademicYear.objects.filter(pk=ay.pk).update(is_current=True)

    # =========================================================================
    # BAREME / ECHEANCIER
    # =========================================================================

    def _create_fee_configs(self, site, prog, levels, ay1, ay2):
        from apps.finance.models import FeeConfiguration, FeeInstallment
        configs = {}
        for lvl in levels:
            amount = TUITION_BY_LEVEL[lvl.code]
            for ay, year_start in [(ay1, ay1.start_date.year), (ay2, ay2.start_date.year)]:
                cfg, created = FeeConfiguration.objects.get_or_create(
                    site=site, program=prog, level=lvl, academic_year=ay, fee_category='SCOLARITE',
                    defaults=dict(amount=amount, label=f'Scolarite {lvl.name} {ay.name}', is_active=True),
                )
                if created:
                    tranche = amount // 4
                    dates = [date(year_start, 10, 5), date(year_start, 12, 5),
                             date(year_start + 1, 2, 5), date(year_start + 1, 4, 5)]
                    for i, d in enumerate(dates):
                        amt = tranche if i < 3 else amount - tranche * 3
                        FeeInstallment.objects.create(
                            fee_configuration=cfg, label=f'Tranche {i + 1}', due_date=d, amount=amt, order=i,
                        )
                if lvl.code not in configs:
                    configs[lvl.code] = {}
                configs[lvl.code][ay.code] = cfg
        print(f'  Baremes: {len(levels) * 2} (avec echeancier 4 tranches)')
        return {k: v for k, v in configs.items()}

    # =========================================================================
    # CLASSES / EMPLOI DU TEMPS
    # =========================================================================

    def _create_classes(self, site, levels, ay, teachers, code):
        from apps.academic.models import Class as ClassModel
        pfx = code.replace('-', '')[:3].upper()
        classes = []
        for lvl in levels:
            cls, _ = ClassModel.objects.get_or_create(
                code=f'{pfx}-{lvl.code}-{ay.code[-4:]}', academic_year=ay, site=site,
                defaults=dict(name=f'{lvl.name} — {site.code} ({ay.name})', level=lvl,
                              max_students=45, main_teacher=teachers[0]),
            )
            classes.append(cls)
        print(f'  Classes {ay.name}: {[c.code for c in classes]}')
        return classes

    def _create_cst(self, classes, s_map, teachers):
        from apps.academic.models import ClassSubjectTeacher
        s_list = list(s_map.values())
        n_t = len(teachers)
        for cls in classes:
            for j, subj in enumerate(s_list):
                ClassSubjectTeacher.objects.get_or_create(
                    class_obj=cls, subject=subj, defaults=dict(teacher=teachers[j % n_t]),
                )

    def _create_sessions(self, classes, s_map, teachers, rooms, code):
        from apps.academic.models import Session as AcaSession
        s_list = list(s_map.values())
        n_t = len(teachers)
        room_list = list(rooms.values())
        schedule = [
            (0, time(8, 0), time(10, 0)), (0, time(10, 30), time(12, 30)),
            (1, time(8, 0), time(10, 0)), (1, time(10, 30), time(12, 30)),
            (2, time(8, 0), time(10, 0)), (3, time(8, 0), time(10, 0)), (4, time(8, 0), time(10, 0)),
        ]
        all_sessions = []
        cls = classes[0]
        for j, (day, start, end) in enumerate(schedule):
            if j >= len(s_list):
                break
            subj = s_list[j]
            teacher = teachers[j % n_t]
            room = room_list[j % len(room_list)]
            sess = AcaSession.objects.create(
                class_obj=cls, subject=subj, teacher=teacher, room=room,
                day_of_week=day, start_time=start, end_time=end, is_recurring=True,
            )
            all_sessions.append(sess)
        print(f'  Seances: {len(all_sessions)} (emploi du temps {cls.code})')
        return all_sessions

    # =========================================================================
    # ETUDIANTS / PARENTS
    # =========================================================================

    def _create_cohort(self, site, code, level, tag, n, admission_year):
        """Cree n etudiants (+ 1 parent chacun) pour un niveau donne."""
        from apps.students.models import Student, Parent, StudentParent
        students, parents = [], []
        pfx = code.replace('-', '')[:4].upper()

        for i in range(n):
            gender = 'M' if RNG.random() < 0.5 else 'F'
            fn = RNG.choice(MALE_FIRST if gender == 'M' else FEMALE_FIRST)
            ln = RNG.choice(LAST_NAMES)
            slug = f'{fn.lower()[0]}.{ln.lower()}{i}'
            s_email = f'{slug}.{tag.lower()}@{code.lower().replace("ita-", "ita-")}.ci'.replace('--', '-')
            matricule = f'{pfx}-{tag}-{level.code}-{i + 1:03d}'
            birth_year = admission_year - 19 - (0 if level.code == 'L1' else (1 if level.code == 'L2' else 2))
            birth_date = date(birth_year, RNG.randint(1, 12), RNG.randint(1, 28))

            fully_paid = (i % 3 != 0)  # ~2/3 a jour, 1/3 pas a jour
            tuition = TUITION_BY_LEVEL[level.code]

            su = self._make_user(site, s_email, fn, ln, 'STUDENT', DEMO_PWD)
            student, created = Student.objects.get_or_create(
                user=su,
                defaults=dict(
                    matricule=matricule, gender=gender, birth_date=birth_date,
                    birth_place=RNG.choice(BIRTH_PLACES), nationality='Ivoirienne',
                    address=f'Quartier {i + 1}', city=site.city, site=site, status='ACTIVE',
                    modality='PRESENTIEL' if RNG.random() > 0.15 else 'ELEARNING',
                    affectation_status='AFFECTE' if RNG.random() > 0.5 else 'NON_AFFECTE',
                    admission_date=date(admission_year, 9, 1),
                    emergency_contact_name=f'Parent de {fn}',
                    emergency_contact_phone=f'+225 07 0{i + 1:02d} 0{i + 1:02d} 0{i + 1:02d}',
                    emergency_contact_relation='FATHER' if gender == 'M' else 'MOTHER',
                    registration_fee=75000, is_enrolled=fully_paid,
                    tuition_fee=tuition, total_paid=0, remaining_balance=tuition,
                    echeance_override=(i == n - 1 and n > 4),  # un cas d'exemption admin par cohorte
                ),
            )
            students.append(student)

            if created:
                p_fn = RNG.choice(MALE_FIRST if student.emergency_contact_relation == 'FATHER' else FEMALE_FIRST)
                p_ln = ln
                p_email = f'p.{p_fn.lower()}.{p_ln.lower()}{i}.{tag.lower()}@gmail.com'
                profession, employer = RNG.choice(PROFESSIONS)
                pu = self._make_user(site, p_email, p_fn, p_ln, 'PARENT', DEMO_PWD)
                parent = Parent.objects.create(
                    user=pu, profession=profession, employer=employer,
                    address=site.city, city=site.city,
                    relationship=student.emergency_contact_relation,
                    emergency_contact=student.emergency_contact_phone,
                )
                StudentParent.objects.create(student=student, parent=parent, is_primary=True,
                                              can_pickup=True, receives_notifications=True)
                parents.append(parent)

        print(f'  Cohorte {level.code} ({tag}): {len(students)} etudiants + parents')
        return students, parents

    def _enroll(self, students, cls, ay):
        from apps.academic.models import Enrollment
        for student in students:
            Enrollment.objects.get_or_create(
                student=student, academic_year=ay, defaults=dict(class_obj=cls, status='ENROLLED'),
            )

    # =========================================================================
    # FINANCE
    # =========================================================================

    def _create_finance(self, site, students, staff, ay, fee_config, pay_methods, fee_type_scol, code, level_code):
        """N'invente jamais de Invoice/InvoiceItem a la main : l'Enrollment
        cree juste avant (voir _enroll) a deja declenche le signal
        finance.on_enrollment_save -> ensure_student_invoices, qui a
        auto-cree LA facture SCOLARITE de l'etudiant au bon montant (bareme
        resolu). Creer une 2e facture manuellement ici doublerait le total
        affiche (vu en prod : "1 300 000" au lieu de "650 000"). On se
        contente donc de retrouver cette facture auto-creee et d'y attacher
        les paiements — Payment.save() (signal on_payment_save) resynchronise
        alors amount_paid/balance/status de la facture et is_enrolled de
        l'etudiant tout seul."""
        from apps.finance.models import Invoice, Payment, ensure_student_invoices, sync_enrollment_status
        receiver = staff[1] if len(staff) > 1 else staff[0]
        pfx = code.replace('-', '')[:4].upper()
        cfg = fee_config[ay.code]
        amount = cfg.amount
        year_start = ay.start_date.year
        n_invoiced = 0

        for i, student in enumerate(students):
            fully_paid = (i % 3 != 0)
            paid_amount = amount if fully_paid else (amount // 2 if i % 3 == 1 else amount // 5)

            _, invoices = ensure_student_invoices(student, created_by=receiver)
            inv = (
                invoices.filter(academic_year=ay).exclude(status='CANCELLED').order_by('-created_at').first()
                or invoices.exclude(status='CANCELLED').order_by('-created_at').first()
            )
            if not inv:
                continue  # pas de bareme resolu pour ce site/niveau/annee — rien a facturer
            n_invoiced += 1

            Invoice.objects.filter(pk=inv.pk).update(issue_date=date(year_start, 9, 5), due_date=date(year_start, 10, 10))

            if paid_amount > 0:
                method = pay_methods['CASH'] if i % 2 == 0 else pay_methods['MOBILE']
                p = Payment.objects.create(
                    payment_number=f'PAY-{pfx}-{level_code}-{ay.code[-4:]}-{i + 1:04d}',
                    invoice=inv, payment_method=method, amount=paid_amount, status='SUCCESS',
                    reference=f'REF-{pfx}-{level_code}-{i + 1:03d}',
                    received_by=receiver, validated_by=receiver, validated_at=_dt(date(year_start, 9, 20)),
                )
                Payment.objects.filter(pk=p.pk).update(payment_date=_dt(date(year_start, 9, 20)))
                # Le signal on_payment_save vient de resynchroniser inv.amount_paid/balance/status.

            inv.refresh_from_db()
            student.tuition_fee = inv.total
            student.total_paid = inv.amount_paid
            student.remaining_balance = max(inv.total - inv.amount_paid, 0)
            student.save(update_fields=['tuition_fee', 'total_paid', 'remaining_balance'])
            sync_enrollment_status(student)

        # Un paiement PENDING de reliquat (frais divers, distinct de la
        # scolarite) pour tester la validation admin -> notif push
        if students and code == 'ITA-MARC' and level_code == 'L1':
            from apps.finance.models import InvoiceItem, FeeType
            fee_type_divers, _ = FeeType.objects.get_or_create(
                code='DIVERS', defaults=dict(name='Frais divers', default_amount=0, is_recurring=False),
            )
            reliquat = amount // 4
            st = students[0]
            inv_notif = Invoice.objects.create(
                student=st, site=site, academic_year=ay,
                invoice_number=f'FAC-{pfx}-{level_code}-{ay.code[-4:]}-TEST', due_date=date(year_start + 1, 4, 30),
                amount_paid=0, created_by=receiver,
            )
            InvoiceItem.objects.create(
                invoice=inv_notif, fee_type=fee_type_divers,
                description='Frais divers — test notification push',
                quantity=1, unit_price=reliquat, total=reliquat,
            )
            Invoice.objects.filter(pk=inv_notif.pk).update(issue_date=date(year_start + 1, 4, 1))
            Payment.objects.create(
                payment_number=f'PAY-{pfx}-{level_code}-{ay.code[-4:]}-TEST', invoice=inv_notif,
                payment_method=pay_methods['MOBILE'], amount=reliquat, status='PENDING',
                reference=f'REF-{pfx}-{level_code}-{ay.code[-4:]}-TEST', received_by=receiver,
            )

        print(f'  Finance {level_code} {ay.name}: {n_invoiced} factures/paiements')

    # =========================================================================
    # NOTES / BULLETINS
    # =========================================================================

    def _create_grades(self, students, cls, s_map, teacher, sem1, sem2, cc, exam_cat):
        from apps.grades.models import Evaluation, Grade, ReportCard
        if not students:
            return
        s_list = list(s_map.values())
        n = len(students)
        sem1_start = sem1.start_date

        for subj in s_list:
            ev_cc = Evaluation.objects.create(
                title=f'CC1 — {subj.name[:35]}', eval_type='DEVOIR', subject=subj, class_group=cls,
                semester=sem1, date=sem1_start + timedelta(days=70),
                max_score=20, coefficient=1, is_locked=True, created_by=teacher.user,
            )
            ev_ex = Evaluation.objects.create(
                title=f'Examen S1 — {subj.name[:30]}', eval_type='EXAMEN', subject=subj, class_group=cls,
                semester=sem1, date=sem1_start + timedelta(days=130),
                max_score=20, coefficient=2, is_locked=True, created_by=teacher.user,
            )
            for i, student in enumerate(students):
                base = 8 + (i * 3) % 12
                Grade.objects.create(
                    student=student, subject=subj, class_group=cls, semester=sem1,
                    evaluation=ev_cc, category=cc, score=base, max_score=20,
                    date=ev_cc.date, comment='Bon travail' if base >= 14 else 'Peut mieux faire',
                    entered_by=teacher.user,
                )
                Grade.objects.create(
                    student=student, subject=subj, class_group=cls, semester=sem1,
                    evaluation=ev_ex, category=exam_cat, score=max(base - 1, 5), max_score=20,
                    date=ev_ex.date, comment='Resultats notes', entered_by=teacher.user,
                )

        for i, student in enumerate(students):
            base = 8 + (i * 3) % 12
            avg = round(base * 0.4 + max(base - 1, 5) * 0.6, 2)
            st = 'HONORS' if avg >= 16 else ('PASS' if avg >= 10 else 'FAIL')
            ReportCard.objects.get_or_create(
                student=student, class_group=cls, semester=sem1,
                defaults=dict(
                    average=str(avg), rank=i + 1, total_students=n, status=st,
                    subject_averages={
                        str(s.id): {
                            'subject_id': str(s.id), 'subject_name': s.name, 'subject_code': s.code,
                            'coefficient': float(s.coefficient), 'grades': [], 'average': round(avg, 2),
                        } for s in s_list
                    },
                    teacher_comment='Bon travail, continuez ainsi.' if avg >= 10 else 'Des efforts sont attendus.',
                    principal_comment='Resultats encourageants.' if avg >= 10 else 'Suivi renforce necessaire.',
                    is_published=True,
                ),
            )
        print(f'  Notes {cls.code}: {n * len(s_list) * 2} notes | {n} bulletins')

    # =========================================================================
    # E-LEARNING : chapitres/lecons, quiz, devoirs, examens securises
    # =========================================================================

    def _create_elearning(self, cls, s_map, teachers, students, code):
        from apps.elearning.models import (
            Chapter, Lesson, Quiz, Question, Choice, Assignment, AssignmentSubmission,
            SecureExam, ExamSession, QuizAttempt,
        )
        s_list = list(s_map.values())[:3]  # 3 matieres avec contenu e-learning complet
        n_t = len(teachers)
        created_lessons = 0
        created_chapters = 0

        for j, subj in enumerate(s_list):
            teacher = teachers[j % n_t]
            chapter = Chapter.objects.create(
                title=f'Chapitre 1 — {subj.name[:40]}', description=f'Introduction a {subj.name}',
                class_obj=cls, subject=subj, order=1, is_published=True,
            )
            created_chapters += 1
            lessons = []
            for k in range(2):
                lesson = Lesson.objects.create(
                    title=f'Lecon {k + 1} — {subj.name[:30]}',
                    description='Contenu de cours', content=f'Support de cours pour {subj.name}, lecon {k + 1}.',
                    class_obj=cls, subject=subj, teacher=teacher, chapter=chapter,
                    order=k + 1, is_published=True, published_at=timezone.now(),
                )
                lessons.append(lesson)
                created_lessons += 1

            # Quiz sur la matiere
            quiz = Quiz.objects.create(
                title=f'Quiz — {subj.name[:35]}', description='Quiz d\'evaluation des connaissances',
                class_obj=cls, subject=subj, lesson=lessons[0],
                time_limit_minutes=20, max_attempts=2, pass_score_percent=50, is_published=True,
            )
            q1 = Question.objects.create(quiz=quiz, question_type='QCU', text=f'Question de base sur {subj.name}',
                                          points=2, order=1)
            Choice.objects.create(question=q1, text='Reponse correcte', is_correct=True, order=1)
            Choice.objects.create(question=q1, text='Reponse incorrecte', is_correct=False, order=2)
            q2 = Question.objects.create(quiz=quiz, question_type='TRUEFALSE', text=f'Vrai ou faux sur {subj.name}',
                                          points=1, order=2)
            Choice.objects.create(question=q2, text='Vrai', is_correct=True, order=1)
            Choice.objects.create(question=q2, text='Faux', is_correct=False, order=2)

            for i, student in enumerate(students[:5]):
                percent = 40 + (i * 12) % 60
                QuizAttempt.objects.create(
                    quiz=quiz, student=student, score=percent * 3 / 100, max_score=3,
                    percent=percent, is_passed=percent >= 50, is_graded=True,
                    submitted_at=timezone.now(),
                )

            # Devoir + soumissions
            assignment = Assignment.objects.create(
                title=f'Devoir maison — {subj.name[:30]}', description=f'Exercices sur {subj.name}',
                instructions='Rendre en PDF avant la date limite.', class_obj=cls, subject=subj, teacher=teacher,
                lesson=lessons[0], due_date=timezone.now() + timedelta(days=14),
                max_score=20, status='PUBLISHED', published_at=timezone.now(),
            )
            for i, student in enumerate(students[:6]):
                AssignmentSubmission.objects.get_or_create(
                    assignment=assignment, student=student,
                    defaults=dict(content=f'Reponse de {student.user.first_name} au devoir.', status='SUBMITTED'),
                )

            # Examen securise (uniquement 1ere matiere pour ne pas surcharger)
            if j == 0:
                exam_quiz = Quiz.objects.create(
                    title=f'Sujet examen — {subj.name[:30]}', description='Examen final securise',
                    class_obj=cls, subject=subj, time_limit_minutes=60, max_attempts=1,
                    pass_score_percent=50, is_published=True,
                )
                eq1 = Question.objects.create(quiz=exam_quiz, question_type='QCU',
                                               text=f'Question examen 1 — {subj.name}', points=10, order=1)
                Choice.objects.create(question=eq1, text='Bonne reponse', is_correct=True, order=1)
                Choice.objects.create(question=eq1, text='Mauvaise reponse', is_correct=False, order=2)
                eq2 = Question.objects.create(quiz=exam_quiz, question_type='QCU',
                                               text=f'Question examen 2 — {subj.name}', points=10, order=2)
                Choice.objects.create(question=eq2, text='Bonne reponse', is_correct=True, order=1)
                Choice.objects.create(question=eq2, text='Mauvaise reponse', is_correct=False, order=2)

                secure_exam = SecureExam.objects.create(
                    title=f'Examen final — {subj.name[:35]}', description='Examen surveille de fin de semestre',
                    class_obj=cls, subject=subj, teacher=teacher, quiz=exam_quiz,
                    exam_type='FINAL', duration_minutes=60,
                    start_date=timezone.now() + timedelta(days=30), end_date=timezone.now() + timedelta(days=31),
                    max_attempts=1, is_published=True, pass_score_percent=50, coefficient=2, max_score=20,
                )
                for i, student in enumerate(students[:4]):
                    percent = 45 + (i * 15) % 55
                    attempt = QuizAttempt.objects.create(
                        quiz=exam_quiz, student=student, score=percent * 20 / 100, max_score=20,
                        percent=percent, is_passed=percent >= 50, is_graded=True, submitted_at=timezone.now(),
                    )
                    ExamSession.objects.create(
                        exam=secure_exam, student=student, quiz_attempt=attempt,
                        status='SUBMITTED', submitted_at=timezone.now(),
                    )

        print(f'  E-learning: {created_chapters} chapitres, {created_lessons} lecons, quiz/devoirs/examens')
        return {'chapters': created_chapters, 'lessons': created_lessons}

    # =========================================================================
    # PRESENCE
    # =========================================================================

    def _create_attendance(self, sessions, students, main_teacher):
        from apps.attendance.models import AttendanceSession, AttendanceRecord
        if not sessions or not students:
            return
        att_dates = [date(2025, 10, 6), date(2025, 10, 8), date(2025, 10, 10),
                     date(2025, 10, 13), date(2025, 10, 15)]
        records = 0
        for idx, (sess, d) in enumerate(zip(sessions[:5], att_dates)):
            att_sess = AttendanceSession.objects.create(
                session=sess, date=d, status='CLOSED', opened_by=main_teacher.user,
            )
            for si, student in enumerate(students):
                is_absent = (si % 5 == idx % 5)
                AttendanceRecord.objects.create(
                    attendance_session=att_sess, student=student,
                    status='ABSENT' if is_absent else 'PRESENT',
                    check_in_method='MANUAL', marked_by=main_teacher.user,
                )
                records += 1
        print(f'  Presences: {records} enregistrements')

    # =========================================================================
    # BANQUE / DEPENSES
    # =========================================================================

    def _create_bank_expenses(self, site, pay_methods, approver, code):
        from apps.finance.models import BankAccount, Expense, CashRegister
        pfx = code.replace('-', '')[:4].upper()
        bname, bbank, bacct, bbal = BANK_DATA[code]
        BankAccount.objects.get_or_create(
            account_number=bacct, defaults=dict(name=bname, bank_name=bbank, account_type='CHECKING',
                                                  balance=bbal, currency='XOF', site=site),
        )
        expenses = [
            ('Salaires enseignants — Septembre', 'SALARY', 2500000, date(2025, 9, 30)),
            ('Salaires personnel administratif', 'SALARY', 800000, date(2025, 9, 30)),
            ('Facture electricite', 'UTILITIES', 150000, date(2025, 9, 15)),
            ('Fournitures de bureau', 'SUPPLIES', 45000, date(2025, 9, 10)),
            ('Maintenance informatique', 'MAINTENANCE', 180000, date(2025, 9, 20)),
        ]
        for label, cat, amt, d in expenses:
            Expense.objects.create(site=site, label=label, category=cat, amount=amt, date=d,
                                    payment_method=pay_methods['VIREMENT'], status='PAID', approved_by=approver)
        CashRegister.objects.get_or_create(
            code=f'CAISSE-{pfx}', site=site, defaults=dict(name=f'Caisse Scolarite {site.name[:15]}',
                                                             current_balance=350000, is_open=True),
        )
        print(f'  Banque: 1 compte | Depenses: {len(expenses)} | Caisse: 1')

    # =========================================================================
    # RESUME
    # =========================================================================

    def _summary(self, all_stats):
        from apps.accounts.models import User
        from apps.students.models import Student
        from apps.grades.models import Grade
        from apps.finance.models import Payment, Invoice
        from apps.elearning.models import Chapter, Lesson, Assignment, SecureExam

        sep = '=' * 88
        print('\n' + sep)
        print('SEED GROUPE ITA — TERMINE')
        print(sep)
        print(f'  Super Admin   : admin@campus.ci / {ADMIN_PWD}')
        print(f'  Mot de passe demo (etudiants/enseignants/staff/parents) : {DEMO_PWD}')
        print()
        for name, n_t, n_s in all_stats:
            print(f'  [{name}] {n_t} enseignants, {n_s} etudiants (2025-2026 + 2026-2027)')
        print('\n' + sep)
        print('STATISTIQUES GLOBALES')
        print(sep)
        print(f'  Utilisateurs    : {User.objects.count()}')
        print(f'  Etudiants       : {Student.objects.count()}')
        print(f'  Notes           : {Grade.objects.count()}')
        print(f'  Chapitres       : {Chapter.objects.count()}')
        print(f'  Lecons          : {Lesson.objects.count()}')
        print(f'  Devoirs         : {Assignment.objects.count()}')
        print(f'  Examens securises: {SecureExam.objects.count()}')
        print(f'  Factures        : {Invoice.objects.count()}')
        print(f'  Paiements       : {Payment.objects.count()}')
        print(sep + '\n')
