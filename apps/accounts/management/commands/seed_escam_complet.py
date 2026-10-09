"""
seed_escam_complet.py — Seed complet du groupe ESCAM (site unique, Abidjan)

Cree la structure academique (filieres/niveaux/classes/matieres), le personnel,
les enseignants, les etudiants + parents, les inscriptions, les baremes de
scolarite + echeancier, les factures/paiements (certains etudiants a jour,
d'autres non), les notes/evaluations/bulletins — puis enchaine automatiquement
sur `seed_elearning_complet` pour alimenter TOUT le module e-learning (cours
autonomes MOOC, chapitres/lecons, quiz, devoirs, examens securises, laboratoires
virtuels, videotheque, classes virtuelles, bibliotheque numerique, conversations
IA) sur les classes et etudiants qui viennent d'etre crees.

Usage: python manage.py seed_escam_complet [--reset]
--reset efface les donnees academiques/financieres/etudiants existantes avant
de reseeder (ne touche pas aux autres groupes scolaires eventuels).
"""
import random
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone

ADMIN_PWD = 'esc@m2026'
DEMO_PWD = 'Escam2026!'

RNG = random.Random(7)


def _dt(d, h=10, m=0):
    return timezone.make_aware(datetime(d.year, d.month, d.day, h, m))


# ===========================================================================
# DONNEES STATIQUES
# ===========================================================================

SITE_DATA = {
    'code': 'ESCAM-ABJ', 'name': 'ESCAM Abidjan',
    'address': 'Boulevard Latrille, Cocody', 'city': 'Abidjan',
    'phone': '+225 27 22 44 10 00', 'email': 'contact@escam.net', 'is_main': True,
}

# (nom, code, duree_ans)
PROGRAMS_DATA = [
    ('Informatique de Gestion', 'INFO', 3),
    ('Gestion Administrative', 'GESTADM', 3),
    ('Comptabilite et Gestion', 'CPTGES', 3),
]

SUBJECTS = [
    # code, nom, coefficient, heures/semaine
    ('ALG101', 'Algorithmique et structures de donnees', 4, 4),
    ('PRG101', 'Programmation Python', 3, 3),
    ('BDD101', 'Bases de donnees relationnelles', 3, 4),
    ('WEB201', 'Developpement web full-stack', 4, 4),
    ('RES101', 'Reseaux informatiques', 3, 3),
    ('TDA101', 'Traitement des documents administratifs', 4, 4),
    ('SEC101', 'Secretariat et bureautique', 3, 3),
    ('COM101', 'Communication professionnelle', 2, 2),
    ('DRT101', 'Droit des affaires', 2, 2),
    ('RH201', 'Gestion des ressources humaines', 3, 3),
    ('CPT101', 'Comptabilite generale', 4, 4),
    ('CPT201', 'Comptabilite analytique', 4, 4),
    ('FIN201', "Finance d'entreprise", 3, 3),
    ('FIS101', 'Fiscalite', 3, 3),
    ('MAT101', 'Mathematiques appliquees', 3, 3),
    ('ECO101', 'Economie generale', 3, 3),
    ('ANG101', 'Anglais professionnel', 2, 2),
    ('GES101', 'Introduction a la gestion', 3, 3),
]

SUBJECTS_BY_PROGRAM = {
    'INFO': ['ALG101', 'PRG101', 'BDD101', 'WEB201', 'RES101', 'MAT101', 'ANG101'],
    'GESTADM': ['TDA101', 'SEC101', 'COM101', 'DRT101', 'RH201', 'GES101', 'ANG101'],
    'CPTGES': ['CPT101', 'CPT201', 'FIN201', 'FIS101', 'DRT101', 'ECO101', 'ANG101'],
}

ADMIN_DATA = ('direction@escam.net', 'Jean-Marie', 'Kouassi')

STAFF_DATA = [
    ('s.yao@escam.net', 'Solange', 'Yao', 'SCOLARITE'),
    ('p.diaby@escam.net', 'Patrick', 'Diaby', 'COMPTABILITE'),
]

TEACHERS_DATA = {
    'INFO': [
        ('k.n_dri@escam.net', 'Kouadio', "N'Dri", 'Informatique & Algorithmes', 'Master Informatique', date(2021, 9, 1), 'PERMANENT', 13000, 'ESCAM-P001'),
        ('a.toure@escam.net', 'Awa', 'Toure', 'Developpement Web', 'Master Genie Logiciel', date(2022, 9, 1), 'CONTRACT', 10000, 'ESCAM-P002'),
    ],
    'GESTADM': [
        ('m.kone@escam.net', 'Marceline', 'Kone', 'Secretariat & Bureautique', 'Licence Pro Secretariat', date(2020, 9, 1), 'PERMANENT', 11000, 'ESCAM-P003'),
        ('f.gnahore@escam.net', 'Felix', 'Gnahore', 'Droit & Communication', 'Master Droit des Affaires', date(2022, 1, 1), 'CONTRACT', 10500, 'ESCAM-P004'),
    ],
    'CPTGES': [
        ('r.assamoi@escam.net', 'Rosine', 'Assamoi', 'Comptabilite & Fiscalite', 'Master CCA', date(2021, 1, 1), 'PERMANENT', 12500, 'ESCAM-P005'),
        ('d.silue@escam.net', 'Daouda', 'Silue', 'Finance & Economie', 'Master Finance', date(2022, 9, 1), 'CONTRACT', 10500, 'ESCAM-P006'),
    ],
}

MALE_FIRST = ['Ibrahim', 'Kevin', 'Yannick', 'Mohamed', 'Junior', 'Abdoul', 'Siaka', 'David',
              'Amani', 'Cheick', 'Evariste', 'Gontran', 'Franck', 'Steve', 'Arnaud',
              'Wilfried', 'Herve', 'Lassina', 'Boris', 'Armand']
FEMALE_FIRST = ['Aicha', 'Rebecca', 'Mariam', 'Estelle', 'Patricia', 'Laurence', 'Celine',
                'Brigitte', 'Danielle', 'Fatima', 'Hermine', 'Juliette', 'Nadia', 'Solange',
                'Grace', 'Vanessa', 'Christelle', 'Ornella', 'Prisca', 'Audrey']
LAST_NAMES = ['Kone', 'Traore', 'Kouadio', 'Adjoua', 'Bile', 'Ake', 'Dosso', 'Gnaoule', 'Bah',
              'Ettien', 'Sylla', 'Ouattara', 'Tape', 'Yeboua', 'Akpan', 'Konan', 'Toure',
              'Diomande', 'Koffi', 'Berte', 'Bamba', 'Sanogo', 'Diallo', 'Yao', 'Kra', 'Gadou',
              'Digbeu', 'Zadi', 'Silue', 'Gohi', 'Assamoi', 'N\'Dri']
BIRTH_PLACES = ['Abidjan', 'Bouake', 'Yamoussoukro', 'Daloa', 'Korhogo', 'Man', 'San-Pedro',
                'Abengourou', 'Gagnoa', 'Divo']
PROFESSIONS = [('Ingenieur', 'BNETD'), ('Commercante', 'Auto-entrepreneur'),
               ('Fonctionnaire', 'Min. Education'), ('Infirmiere', 'CHU'),
               ('Enseignant', 'Lycee Technique'), ('Chauffeur', 'SOTRA'),
               ('Technicien', 'CIE'), ('Menagere', ''), ('Gendarme', 'FACI'),
               ('Agriculteur', 'Auto-entrepreneur')]

TUITION_BY_LEVEL = {'L1': 500000, 'L2': 550000, 'L3': 600000}
STUDENTS_PER_LEVEL = 8


# ===========================================================================
# COMMANDE
# ===========================================================================

class Command(BaseCommand):
    help = "Seed complet du groupe ESCAM (academique, finance, notes) puis alimente tout le e-learning"

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Efface les donnees existantes avant de seeder')
        parser.add_argument('--skip-elearning', action='store_true', help='Ne pas enchainer sur seed_elearning_complet')

    def handle(self, *args, **options):
        if options['reset']:
            print('\n=== NETTOYAGE ===')
            self._clean()

        print('\n=== DONNEES PARTAGEES ===')
        subjs, ay, sem1, sem2, cc, exam_cat, pay_methods, fee_type_scol = self._shared()

        print('\n=== SUPER ADMIN ===')
        self._super_admin()

        print('\n=== ESCAM ABIDJAN ===')
        site = self._create_site()
        self._create_admin(site)
        staff = self._create_staff(site)

        all_students = []
        for prog_name, prog_code, prog_dur in PROGRAMS_DATA:
            print(f'\n--- Filiere {prog_name} ---')
            prog, levels = self._create_program_levels(site, prog_name, prog_code, prog_dur)
            rooms = self._create_rooms(site, prog_code)
            teachers = self._create_teachers(site, prog_code)
            s_codes = SUBJECTS_BY_PROGRAM[prog_code]
            s_map = {c: subjs[c] for c in s_codes}

            classes = self._create_classes(site, levels, ay, teachers, prog_code)
            self._create_cst(classes, s_map, teachers)
            sessions = self._create_sessions(classes, s_map, teachers, rooms, prog_code)

            fee_configs = self._create_fee_configs(site, prog, levels, ay)

            for cls, lvl in zip(classes, levels):
                students, parents = self._create_cohort(site, prog_code, lvl, 'A26', STUDENTS_PER_LEVEL, 2026)
                self._enroll(students, cls, ay)
                self._create_finance(site, students, staff, ay, fee_configs[lvl.code], pay_methods, fee_type_scol, prog_code, lvl.code)
                self._create_grades(students, cls, s_map, teachers[0], sem1, cc, exam_cat)
                self._create_attendance(sessions, students, teachers[0])
                all_students.extend(students)

            self._create_bank_expenses(site, pay_methods, staff[0], prog_code)

        print(f'\n=== RESUME ACADEMIQUE/FINANCE ===')
        print(f'  Site: {site.name} | Filieres: {len(PROGRAMS_DATA)} | Etudiants: {len(all_students)}')

        if not options['skip_elearning']:
            print('\n=== ENCHAINEMENT E-LEARNING (seed_elearning_complet) ===')
            call_command('seed_elearning_complet')

        self._summary(site, all_students)

    # =========================================================================
    # NETTOYAGE
    # =========================================================================

    def _clean(self):
        from apps.attendance.models import AttendanceRecord, AbsenceRequest, AttendanceSession
        from apps.grades.models import Grade, ReportCard, Evaluation, GradeCategory
        from apps.elearning.models import (
            ExamSession, SecureExam, AssignmentCorrection, AssignmentSubmission, Assignment,
            AttemptAnswer, QuizAttempt, Choice, Question, Quiz, LessonProgress,
            LessonAttachment, Lesson, Chapter, CourseLesson, CourseChapter, CourseSection, Course,
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
        from apps.payments.models import CinetPayTransaction
        from apps.accounting.models import JournalLine, JournalEntry

        order = [
            ExamSession, SecureExam, AssignmentCorrection, AssignmentSubmission, Assignment,
            AttemptAnswer, QuizAttempt, Choice, Question, Quiz, LessonProgress,
            LessonAttachment, Lesson, Chapter, CourseLesson, CourseChapter, CourseSection, Course,
            AttendanceRecord, AbsenceRequest, AttendanceSession,
            Grade, ReportCard, Evaluation, GradeCategory,
            CinetPayTransaction, JournalLine, JournalEntry,
            CashTransaction, CashSession, Payment, InvoiceItem, Invoice,
            Expense, CashRegister, BankAccount, PaymentMethod, FeeType,
            FeeInstallment, FeeConfiguration,
            Enrollment, ClassSubjectTeacher, AcaSession, Room, LevelSubject,
            ClassModel, Semester, TeacherSite, TeacherProfile, Level, Subject, Program,
            StudentParent, StudentCard, StudentFile, Student, Parent, StaffProfile,
            UserRole, UserSite, User,
            AuditLog, SystemConfig, AcademicYear,
        ]
        failures = []
        for model in order:
            try:
                n = model.objects.count()
                model.objects.all().delete()
                if n:
                    print(f'  Supprime {n:>4}  {model.__name__}')
            except Exception as e:
                print(f'  [ECHEC] {model.__name__}: {e}')
                failures.append(model.__name__)

        if failures:
            raise RuntimeError(
                'Le nettoyage a echoue pour : ' + ', '.join(failures) +
                ' — des donnees residuelles subsistent. Corrigez la cause (FK PROTECT non geree) avant de relancer.'
            )

    # =========================================================================
    # DONNEES PARTAGEES
    # =========================================================================

    def _shared(self):
        from apps.academic.models import Subject, Semester
        from apps.core.models import AcademicYear
        from apps.finance.models import FeeType, PaymentMethod
        from apps.grades.models import GradeCategory

        ay, _ = AcademicYear.objects.get_or_create(
            code='AY-2026-2027',
            defaults=dict(name='2026-2027', start_date=date(2026, 9, 1), end_date=date(2027, 6, 30),
                          is_current=True, registration_open=True),
        )
        sem1 = Semester.objects.create(academic_year=ay, name='S1', label='Semestre 1',
                                        start_date=date(2026, 9, 1), end_date=date(2027, 1, 31), is_current=True)
        sem2 = Semester.objects.create(academic_year=ay, name='S2', label='Semestre 2',
                                        start_date=date(2027, 2, 1), end_date=date(2027, 6, 30), is_current=False)

        subjs = {}
        for code, name, coef, hpw in SUBJECTS:
            subjs[code], _ = Subject.objects.get_or_create(
                code=code, defaults=dict(name=name, coefficient=coef, hours_per_week=hpw),
            )
        print(f'  Matieres: {len(subjs)} | Annee academique: {ay.name}')

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

        return subjs, ay, sem1, sem2, cc, exam_cat, pay_methods, fee_type_scol

    def _super_admin(self):
        from apps.accounts.models import User
        u, created = User.objects.get_or_create(
            email='admin@escam.net',
            defaults=dict(first_name='Super', last_name='Admin', user_type='ADMIN',
                           is_active=True, is_staff=True, is_superuser=True),
        )
        if created:
            u.set_password(ADMIN_PWD)
            u.save()
        print('  [SUPER]   admin@escam.net')

    # =========================================================================
    # STRUCTURE
    # =========================================================================

    def _create_site(self):
        from apps.core.models import Site
        info = SITE_DATA
        site, _ = Site.objects.get_or_create(
            code=info['code'],
            defaults=dict(name=info['name'], address=info['address'], city=info['city'],
                           phone=info['phone'], email=info['email'], is_main=info['is_main'], is_active=True),
        )
        print(f'  Site: {site.name}')
        return site

    def _create_program_levels(self, site, name, code, dur):
        from apps.academic.models import Program, Level
        prog, _ = Program.objects.get_or_create(
            code=code, defaults=dict(name=name, description=f'{name} — ESCAM Abidjan', duration_years=dur, site=site),
        )
        levels = []
        for lcode, lname, order in [('L1', f'{name} 1', 1), ('L2', f'{name} 2', 2), ('L3', f'{name} 3', 3)]:
            lvl, _ = Level.objects.get_or_create(program=prog, code=lcode, defaults=dict(name=lname, order=order))
            levels.append(lvl)
        print(f'  Programme: {prog.code} | Niveaux: {[l.code for l in levels]}')
        return prog, levels

    def _create_rooms(self, site, prog_code):
        from apps.academic.models import Room
        pfx = prog_code[:4].upper()
        rooms_def = [
            (f'{pfx}-AMPHI', 'Amphitheatre', 150, 'AMPHITHEATER'),
            (f'{pfx}-S101', 'Salle 101', 40, 'CLASSROOM'),
            (f'{pfx}-LABO', 'Laboratoire', 30, 'LAB'),
        ]
        rooms = {}
        for rcode, rname, cap, rtype in rooms_def:
            rooms[rcode], _ = Room.objects.get_or_create(
                code=rcode, site=site,
                defaults=dict(name=rname, building='Batiment ESCAM', floor='RDC', capacity=cap, room_type=rtype),
            )
        return rooms

    def _make_user(self, site, email, fn, ln, utype, pwd, is_staff=False, is_super=False, phone=''):
        from apps.accounts.models import User
        u, created = User.objects.get_or_create(
            email=email,
            defaults=dict(first_name=fn, last_name=ln, user_type=utype, is_active=True,
                          is_staff=is_staff, is_superuser=is_super, site=site, phone=phone),
        )
        if created:
            u.set_password(pwd)
            u.save()
        return u

    def _create_admin(self, site):
        email, fn, ln = ADMIN_DATA
        self._make_user(site, email, fn, ln, 'ADMIN', ADMIN_PWD, True, False)
        print(f'  [ADMIN]   {email}')

    def _create_staff(self, site):
        from apps.staff.models import StaffProfile
        staff = []
        for email, fn, ln, dept in STAFF_DATA:
            u = self._make_user(site, email, fn, ln, 'STAFF', DEMO_PWD)
            StaffProfile.objects.get_or_create(
                user=u, defaults=dict(employee_id=f'ESCAM-STF-{email[:3].upper()}',
                                       department=dept, position='Agent', hire_date=date(2023, 9, 1),
                                       contract_type='PERMANENT', site=site),
            )
            staff.append(u)
        print(f'  Personnel: {len(staff)}')
        return staff

    def _create_teachers(self, site, prog_code):
        from apps.academic.models import TeacherProfile, TeacherSite
        teachers = []
        for email, fn, ln, spec, qual, hire, ctype, rate, emp_id in TEACHERS_DATA[prog_code]:
            u = self._make_user(site, email, fn, ln, 'TEACHER', DEMO_PWD)
            prof, created = TeacherProfile.objects.get_or_create(
                user=u, defaults=dict(employee_id=emp_id, specialization=spec, qualification=qual,
                                       hire_date=hire, contract_type=ctype, hourly_rate=rate),
            )
            TeacherSite.objects.get_or_create(teacher=prof, site=site, defaults=dict(is_primary=True))
            teachers.append(prof)
        print(f'  Enseignants: {len(teachers)}')
        return teachers

    # =========================================================================
    # BAREME / ECHEANCIER
    # =========================================================================

    def _create_fee_configs(self, site, prog, levels, ay):
        from apps.finance.models import FeeConfiguration, FeeInstallment
        configs = {}
        year_start = ay.start_date.year
        for lvl in levels:
            amount = TUITION_BY_LEVEL[lvl.code]
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
            configs[lvl.code] = cfg
        print(f'  Baremes: {len(levels)} (avec echeancier 4 tranches)')
        return configs

    # =========================================================================
    # CLASSES / EMPLOI DU TEMPS
    # =========================================================================

    def _create_classes(self, site, levels, ay, teachers, prog_code):
        from apps.academic.models import Class as ClassModel
        pfx = prog_code[:4].upper()
        classes = []
        for lvl in levels:
            cls, _ = ClassModel.objects.get_or_create(
                code=f'{pfx}-{lvl.code}-{ay.code[-4:]}', academic_year=ay, site=site,
                defaults=dict(name=f'{lvl.name} ({ay.name})', level=lvl, max_students=45, main_teacher=teachers[0]),
            )
            classes.append(cls)
        print(f'  Classes: {[c.code for c in classes]}')
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

    def _create_sessions(self, classes, s_map, teachers, rooms, prog_code):
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
        print(f'  Seances: {len(all_sessions)}')
        return all_sessions

    # =========================================================================
    # ETUDIANTS / PARENTS
    # =========================================================================

    def _create_cohort(self, site, prog_code, level, tag, n, admission_year):
        from apps.students.models import Student, Parent, StudentParent
        students, parents = [], []
        pfx = prog_code[:4].upper()

        for i in range(n):
            gender = 'M' if RNG.random() < 0.5 else 'F'
            fn = RNG.choice(MALE_FIRST if gender == 'M' else FEMALE_FIRST)
            ln = RNG.choice(LAST_NAMES)
            slug = f'{fn.lower()[0]}.{ln.lower()}{i}'
            s_email = f'{slug}.{tag.lower()}.{pfx.lower()}@escam-student.ci'
            matricule = f'ESCAM-{pfx}-{tag}-{level.code}-{i + 1:03d}'
            birth_year = admission_year - 19 - (0 if level.code == 'L1' else (1 if level.code == 'L2' else 2))
            birth_date = date(birth_year, RNG.randint(1, 12), RNG.randint(1, 28))

            fully_paid = (i % 3 != 0)
            tuition = TUITION_BY_LEVEL[level.code]
            phone = '07' + f'{abs(hash(matricule)) % 10**8:08d}'

            su = self._make_user(site, s_email, fn, ln, 'STUDENT', DEMO_PWD, phone=phone)
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
                    echeance_override=(i == n - 1 and n > 4),
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

        print(f'  Cohorte {level.code}: {len(students)} etudiants + parents')
        return students, parents

    def _enroll(self, students, cls, ay):
        from apps.academic.models import Enrollment
        for student in students:
            Enrollment.objects.get_or_create(
                student=student, academic_year=ay, defaults=dict(class_obj=cls, status='ENROLLED'),
            )

    # =========================================================================
    # FINANCE — s'appuie sur ensure_student_invoices (auto-cree via le signal
    # d'inscription), ne cree JAMAIS de 2e facture manuellement : voir le
    # commentaire detaille dans seed_ita_groupe.py (campus-backend, branche
    # master) pour le bug que ca evite (facture SCOLARITE dupliquee).
    # =========================================================================

    def _create_finance(self, site, students, staff, ay, fee_config, pay_methods, fee_type_scol, prog_code, level_code):
        from apps.finance.models import Invoice, Payment, ensure_student_invoices, sync_enrollment_status
        from apps.students.models import Student as StudentModel
        receiver = staff[1] if len(staff) > 1 else staff[0]
        pfx = prog_code[:4].upper()
        amount = fee_config.amount
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
                continue
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

            inv.refresh_from_db()
            StudentModel.objects.filter(pk=student.pk).update(
                tuition_fee=inv.total, total_paid=inv.amount_paid,
                remaining_balance=max(inv.total - inv.amount_paid, 0),
            )
            sync_enrollment_status(student)

        print(f'  Finance {level_code}: {n_invoiced} factures/paiements')

    # =========================================================================
    # NOTES / BULLETINS
    # =========================================================================

    def _create_grades(self, students, cls, s_map, teacher, sem1, cc, exam_cat):
        from apps.grades.models import Evaluation, Grade, ReportCard
        if not students:
            return
        s_list = list(s_map.values())
        n = len(students)
        sem1_start = sem1.start_date

        for subj in s_list:
            ev_cc = Evaluation.objects.create(
                title=f'CC1 — {subj.name[:35]}', eval_type='DEVOIR', subject=subj, class_group=cls,
                semester=sem1, date=sem1_start + timedelta(days=50),
                max_score=20, coefficient=1, is_locked=True, created_by=teacher.user,
            )
            ev_ex = Evaluation.objects.create(
                title=f'Examen S1 — {subj.name[:30]}', eval_type='EXAMEN', subject=subj, class_group=cls,
                semester=sem1, date=sem1_start + timedelta(days=110),
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
    # PRESENCE
    # =========================================================================

    def _create_attendance(self, sessions, students, main_teacher):
        from apps.attendance.models import AttendanceSession, AttendanceRecord
        if not sessions or not students:
            return
        att_dates = [date(2026, 10, 5), date(2026, 10, 7), date(2026, 10, 9),
                     date(2026, 10, 12), date(2026, 10, 14)]
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

    def _create_bank_expenses(self, site, pay_methods, approver, prog_code):
        from apps.finance.models import BankAccount, Expense, CashRegister
        pfx = prog_code[:4].upper()
        BankAccount.objects.get_or_create(
            account_number=f'CI93BI0080{pfx}01134500014944',
            defaults=dict(name=f'Compte {prog_code} ESCAM', bank_name='BICICI', account_type='CHECKING',
                          balance=6000000, currency='XOF', site=site),
        )
        expenses = [
            ('Salaires enseignants', 'SALARY', 2000000, date(2026, 9, 30)),
            ('Salaires personnel administratif', 'SALARY', 700000, date(2026, 9, 30)),
            ('Facture electricite', 'UTILITIES', 130000, date(2026, 9, 15)),
            ('Fournitures de bureau', 'SUPPLIES', 40000, date(2026, 9, 10)),
        ]
        for label, cat, amt, d in expenses:
            Expense.objects.create(site=site, label=f'{label} — {prog_code}', category=cat, amount=amt, date=d,
                                    payment_method=pay_methods['VIREMENT'], status='PAID', approved_by=approver)
        CashRegister.objects.get_or_create(
            code=f'CAISSE-{pfx}', site=site, defaults=dict(name=f'Caisse {prog_code}',
                                                            current_balance=300000, is_open=True),
        )

    # =========================================================================
    # RESUME
    # =========================================================================

    def _summary(self, site, all_students):
        from apps.accounts.models import User
        from apps.grades.models import Grade
        from apps.finance.models import Payment, Invoice
        from apps.elearning.models import Chapter, Lesson, Assignment, SecureExam, Course, Quiz

        sep = '=' * 88
        print('\n' + sep)
        print('SEED ESCAM — TERMINE')
        print(sep)
        print(f'  Super Admin   : admin@escam.net / {ADMIN_PWD}')
        print(f'  Admin ESCAM   : {ADMIN_DATA[0]} / {ADMIN_PWD}')
        print(f'  Mot de passe demo (etudiants/enseignants/staff/parents) : {DEMO_PWD}')
        print('\n' + sep)
        print('STATISTIQUES GLOBALES')
        print(sep)
        print(f'  Utilisateurs     : {User.objects.count()}')
        print(f'  Etudiants        : {len(all_students)}')
        print(f'  Notes            : {Grade.objects.count()}')
        print(f'  Factures         : {Invoice.objects.count()}')
        print(f'  Paiements        : {Payment.objects.count()}')
        print(f'  Chapitres        : {Chapter.objects.count()}')
        print(f'  Lecons           : {Lesson.objects.count()}')
        print(f'  Cours MOOC       : {Course.objects.count()}')
        print(f'  Quiz             : {Quiz.objects.count()}')
        print(f'  Devoirs          : {Assignment.objects.count()}')
        print(f'  Examens securises: {SecureExam.objects.count()}')
        print(sep + '\n')
