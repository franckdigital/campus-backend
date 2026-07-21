"""
Seed complet de tous les modules académiques.

Usage:
    python manage.py seed_academic              # seed idempotent (get_or_create)
    python manage.py seed_academic --reset      # supprime et recrée tout
    python manage.py seed_academic --only core  # seed seulement un groupe

Groupes disponibles: core, programs, subjects, teachers, students, finance, grades, attendance
"""
import datetime
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction


# ── Données de référence ──────────────────────────────────────────────────────

SITE_DATA = {
    'name': 'ITA Abidjan',
    'code': 'ITA-ABJ',
    'address': 'Rue des Jardins, Zone 4, Marcory',
    'city': 'Abidjan',
    'country': 'Côte d\'Ivoire',
    'phone': '+225 27 21 35 80 00',
    'email': 'contact@ita-abidjan.ci',
    'is_main': True,
}

ACADEMIC_YEAR_DATA = {
    'name': '2025-2026',
    'code': '2025-2026',
    'start_date': datetime.date(2025, 9, 1),
    'end_date': datetime.date(2026, 7, 31),
    'is_current': True,
    'registration_open': True,
}

PROGRAMS = [
    {
        'name': 'Informatique et Réseaux',
        'code': 'INFO',
        'description': 'Formation en informatique, réseaux et génie logiciel',
        'duration_years': 3,
        'levels': [
            {'name': 'Licence 1', 'code': 'L1', 'order': 1},
            {'name': 'Licence 2', 'code': 'L2', 'order': 2},
            {'name': 'Licence 3', 'code': 'L3', 'order': 3},
        ],
    },
    {
        'name': 'Gestion des Entreprises',
        'code': 'GEST',
        'description': 'Formation en management, comptabilité et finance d\'entreprise',
        'duration_years': 3,
        'levels': [
            {'name': 'Licence 1', 'code': 'L1', 'order': 1},
            {'name': 'Licence 2', 'code': 'L2', 'order': 2},
            {'name': 'Licence 3', 'code': 'L3', 'order': 3},
        ],
    },
    {
        'name': 'Droit des Affaires',
        'code': 'DROIT',
        'description': 'Formation juridique orientée business et droit OHADA',
        'duration_years': 3,
        'levels': [
            {'name': 'Licence 1', 'code': 'L1', 'order': 1},
            {'name': 'Licence 2', 'code': 'L2', 'order': 2},
            {'name': 'Licence 3', 'code': 'L3', 'order': 3},
        ],
    },
]

SUBJECTS = [
    # Informatique
    {'name': 'Algorithmique et Structures de données', 'code': 'ALGO',    'coeff': 3.0, 'hpw': 4.0},
    {'name': 'Programmation Java',                     'code': 'JAVA',    'coeff': 2.5, 'hpw': 3.0},
    {'name': 'Bases de données',                       'code': 'BDD',     'coeff': 3.0, 'hpw': 3.0},
    {'name': 'Réseaux et Télécommunications',          'code': 'RESEAUX', 'coeff': 2.0, 'hpw': 3.0},
    {'name': 'Développement Web',                      'code': 'WEB',     'coeff': 2.5, 'hpw': 3.0},
    {'name': 'Programmation Python',                   'code': 'PYTHON',  'coeff': 2.0, 'hpw': 2.0},
    {'name': 'Systèmes d\'exploitation',               'code': 'SYSEXP',  'coeff': 2.0, 'hpw': 2.0},
    {'name': 'Sécurité Informatique',                  'code': 'SECU',    'coeff': 2.0, 'hpw': 2.0},
    # Gestion
    {'name': 'Comptabilité générale',                  'code': 'COMPTA',  'coeff': 3.0, 'hpw': 3.0},
    {'name': 'Management des organisations',           'code': 'MGMT',    'coeff': 2.5, 'hpw': 3.0},
    {'name': 'Marketing et Communication',             'code': 'MKT',     'coeff': 2.0, 'hpw': 2.0},
    {'name': 'Finance d\'entreprise',                  'code': 'FINANCE', 'coeff': 2.5, 'hpw': 2.0},
    {'name': 'Droit des affaires OHADA',               'code': 'OHADA',   'coeff': 2.0, 'hpw': 2.0},
    {'name': 'Économie générale',                      'code': 'ECO',     'coeff': 2.0, 'hpw': 2.0},
    # Commun
    {'name': 'Mathématiques appliquées',               'code': 'MATHS',   'coeff': 2.5, 'hpw': 2.0},
    {'name': 'Anglais professionnel',                  'code': 'ANGLAIS', 'coeff': 1.5, 'hpw': 2.0},
    {'name': 'Expression française',                   'code': 'FRANÇAIS','coeff': 1.5, 'hpw': 2.0},
    {'name': 'Méthodologie de recherche',              'code': 'METHODO', 'coeff': 1.0, 'hpw': 1.5},
]

# Affectation sujets → niveaux par programme
LEVEL_SUBJECTS = {
    'INFO': {
        'L1': ['ALGO', 'JAVA', 'MATHS', 'ANGLAIS', 'FRANÇAIS', 'BDD', 'WEB'],
        'L2': ['ALGO', 'JAVA', 'BDD', 'RESEAUX', 'WEB', 'PYTHON', 'SYSEXP', 'ANGLAIS'],
        'L3': ['RESEAUX', 'SECU', 'BDD', 'WEB', 'PYTHON', 'METHODO', 'ANGLAIS', 'MATHS'],
    },
    'GEST': {
        'L1': ['COMPTA', 'MGMT', 'ECO', 'MATHS', 'ANGLAIS', 'FRANÇAIS', 'OHADA'],
        'L2': ['COMPTA', 'MGMT', 'MKT', 'FINANCE', 'OHADA', 'ECO', 'ANGLAIS'],
        'L3': ['FINANCE', 'MKT', 'MGMT', 'OHADA', 'METHODO', 'COMPTA', 'ANGLAIS'],
    },
    'DROIT': {
        'L1': ['OHADA', 'ECO', 'MATHS', 'ANGLAIS', 'FRANÇAIS', 'COMPTA'],
        'L2': ['OHADA', 'FINANCE', 'ECO', 'MGMT', 'ANGLAIS', 'METHODO'],
        'L3': ['OHADA', 'FINANCE', 'MGMT', 'METHODO', 'ANGLAIS', 'MKT'],
    },
}

ROOMS = [
    {'name': 'Amphi A',    'code': 'AMPH-A', 'room_type': 'AMPHITHEATER', 'capacity': 150, 'building': 'Bâtiment A', 'floor': 'RDC'},
    {'name': 'Amphi B',    'code': 'AMPH-B', 'room_type': 'AMPHITHEATER', 'capacity': 120, 'building': 'Bâtiment A', 'floor': 'RDC'},
    {'name': 'Salle 101',  'code': 'S-101',  'room_type': 'CLASSROOM',    'capacity': 40,  'building': 'Bâtiment B', 'floor': '1'},
    {'name': 'Salle 102',  'code': 'S-102',  'room_type': 'CLASSROOM',    'capacity': 40,  'building': 'Bâtiment B', 'floor': '1'},
    {'name': 'Salle 201',  'code': 'S-201',  'room_type': 'CLASSROOM',    'capacity': 35,  'building': 'Bâtiment B', 'floor': '2'},
    {'name': 'Salle 202',  'code': 'S-202',  'room_type': 'CLASSROOM',    'capacity': 35,  'building': 'Bâtiment B', 'floor': '2'},
    {'name': 'Labo Info 1','code': 'LABO-1', 'room_type': 'LAB',          'capacity': 25,  'building': 'Bâtiment C', 'floor': '1'},
    {'name': 'Labo Info 2','code': 'LABO-2', 'room_type': 'LAB',          'capacity': 25,  'building': 'Bâtiment C', 'floor': '1'},
    {'name': 'Salle de conf.', 'code': 'CONF', 'room_type': 'MEETING',    'capacity': 20,  'building': 'Bâtiment A', 'floor': '2'},
]

TEACHERS = [
    {
        'first_name': 'Kouadio',  'last_name': 'MENSAH',
        'email': 'k.mensah@ita-abidjan.ci',   'phone': '+22507112233',
        'employee_id': 'ENS-001',
        'specialization': 'Algorithmique & Structures de données',
        'qualification': 'Doctorat en Informatique — Université FHB',
        'contract_type': 'PERMANENT',   'hourly_rate': 12000,
        'bio': 'Enseignant-chercheur spécialisé en algorithmique depuis 2015. Auteur de plusieurs publications en IA appliquée.',
        'subjects': ['ALGO', 'PYTHON', 'MATHS'],
    },
    {
        'first_name': 'Aissatou', 'last_name': 'DIABATE',
        'email': 'a.diabate@ita-abidjan.ci',  'phone': '+22507445566',
        'employee_id': 'ENS-002',
        'specialization': 'Bases de données & Systèmes distribués',
        'qualification': 'Master en Génie Logiciel — INSA Lyon',
        'contract_type': 'PERMANENT',   'hourly_rate': 10000,
        'bio': 'Experte en conception de systèmes d\'information et administration de bases de données. Consultante freelance.',
        'subjects': ['BDD', 'RESEAUX', 'SYSEXP'],
    },
    {
        'first_name': 'Thierry',  'last_name': 'KOUAME',
        'email': 't.kouame@ita-abidjan.ci',   'phone': '+22507778899',
        'employee_id': 'ENS-003',
        'specialization': 'Développement Java & Web',
        'qualification': 'Ingénieur en Génie Logiciel — Polytech Abidjan',
        'contract_type': 'CONTRACT',    'hourly_rate': 8000,
        'bio': 'Développeur senior avec 8 ans d\'expérience en entreprise. Spécialiste des architectures microservices.',
        'subjects': ['JAVA', 'WEB', 'SECU'],
    },
    {
        'first_name': 'Aminata',  'last_name': 'TRAORE',
        'email': 'a.traore@ita-abidjan.ci',   'phone': '+22507223344',
        'employee_id': 'ENS-004',
        'specialization': 'Finance & Comptabilité',
        'qualification': 'Doctorat en Sciences de Gestion — Université de Bouaké',
        'contract_type': 'PERMANENT',   'hourly_rate': 11000,
        'bio': 'Maître de conférences en finance d\'entreprise. Expert-comptable agréé OHADA.',
        'subjects': ['COMPTA', 'FINANCE', 'OHADA'],
    },
    {
        'first_name': 'Serge',    'last_name': 'BAMBA',
        'email': 's.bamba@ita-abidjan.ci',    'phone': '+22507556677',
        'employee_id': 'ENS-005',
        'specialization': 'Management & Marketing',
        'qualification': 'MBA — École de Commerce de Dakar',
        'contract_type': 'CONTRACT',    'hourly_rate': 9000,
        'bio': 'Directeur marketing dans le secteur bancaire pendant 10 ans. Intervenant académique depuis 2020.',
        'subjects': ['MGMT', 'MKT', 'ECO'],
    },
    {
        'first_name': 'Marie-Claire', 'last_name': 'BROU',
        'email': 'm.brou@ita-abidjan.ci',     'phone': '+22507001122',
        'employee_id': 'ENS-006',
        'specialization': 'Langues & Communication',
        'qualification': 'CAPES Lettres Modernes — Université d\'Abidjan',
        'contract_type': 'VISITING',    'hourly_rate': 6000,
        'bio': 'Professeure certifiée en langues et communication professionnelle. Traductrice assermentée.',
        'subjects': ['ANGLAIS', 'FRANÇAIS', 'METHODO'],
    },
]

# Prénoms et noms ivoiriens/ouest-africains réalistes
FIRST_NAMES_M = [
    'Yao', 'Koffi', 'Kouadio', 'Ange', 'Serge', 'Didier', 'Olivier', 'Patrick',
    'Jean-Baptiste', 'Mamadou', 'Ibrahim', 'Moussa', 'Abdou', 'Issouf', 'Drissa',
    'Kobenan', 'Kan', 'N\'Guessan', 'Félix', 'Arsène', 'Romuald', 'Hermann',
]
FIRST_NAMES_F = [
    'Aya', 'Adjoua', 'Aminata', 'Fatou', 'Mariam', 'Djeneba', 'Rokia', 'Nathalie',
    'Christelle', 'Mireille', 'Roseline', 'Marie-Claire', 'Aissatou', 'Kadiatou',
    'Bintou', 'Yolande', 'Henriette', 'Florence', 'Edwige', 'Albertine',
]
LAST_NAMES = [
    'KONAN', 'COULIBALY', 'DIABATE', 'TRAORE', 'KONE', 'BAMBA', 'TOURE',
    'OUATTARA', 'DIALLO', 'KONATE', 'SANGARE', 'DEMBELE', 'CISSE', 'CAMARA',
    'DOSSO', 'FOFANA', 'SIDIBE', 'SORO', 'YAPI', 'BROU', 'ETTIEN', 'NIANGORAN',
    'AHOUA', 'ANOH', 'ASSOUMOU', 'BILE', 'BOGUI', 'EHUI', 'KASSI', 'KOUAKOU',
]
CITIES = ['Abidjan', 'Bouaké', 'Yamoussoukro', 'San-Pédro', 'Daloa', 'Korhogo', 'Man']

FEE_TYPES = [
    {'code': 'INSCRIPTION', 'name': "Frais d'inscription",   'amount': 150000, 'recurring': False},
    {'code': 'SCOLARITE_S1','name': 'Scolarité Semestre 1',  'amount': 900000, 'recurring': True},
    {'code': 'SCOLARITE_S2','name': 'Scolarité Semestre 2',  'amount': 900000, 'recurring': True},
    {'code': 'EXAMEN',      'name': "Frais d'examen",        'amount': 50000,  'recurring': True},
    {'code': 'BIBLIO',      'name': 'Bibliothèque',          'amount': 25000,  'recurring': False},
]

PAYMENT_METHODS = [
    {'code': 'ESPECES',   'name': 'Espèces',             'is_online': False},
    {'code': 'VIREMENT',  'name': 'Virement bancaire',   'is_online': False},
    {'code': 'MOMO',      'name': 'Mobile Money (MTN)',  'is_online': True},
    {'code': 'WAVE',      'name': 'Wave',                'is_online': True},
    {'code': 'CHEQUE',    'name': 'Chèque',              'is_online': False},
]

GRADE_CATEGORIES = [
    {'code': 'CC',   'name': 'Contrôle Continu',   'weight': 0.40},
    {'code': 'EXAM', 'name': 'Examen Final',        'weight': 0.60},
    {'code': 'TP',   'name': 'Travaux Pratiques',   'weight': 0.30},
]


class Command(BaseCommand):
    help = 'Seed complet de tous les modules académiques (site, programmes, enseignants, étudiants, notes, finances)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Supprime toutes les données existantes avant de reseeder'
        )
        parser.add_argument(
            '--only', type=str, default='all',
            help='Groupe à seeder: all|core|programs|subjects|teachers|students|finance|grades|attendance'
        )

    def handle(self, *args, **options):
        only = options.get('only', 'all')
        do_reset = options.get('reset', False)

        self.stdout.write(self.style.MIGRATE_HEADING(
            '===================================================\n'
            '  Seed academique complet -- CampusLMS\n'
            '==================================================='
        ))

        with transaction.atomic():
            if do_reset:
                self._reset()

            if only in ('all', 'core'):
                site, academic_year = self._seed_core()
            else:
                from apps.core.models import Site, AcademicYear
                site = Site.objects.filter(is_active=True).first()
                academic_year = AcademicYear.objects.filter(is_current=True).first()
                if not site or not academic_year:
                    self.stdout.write(self.style.ERROR('Site ou année académique introuvable. Lancez sans --only d\'abord.'))
                    return

            if only in ('all', 'programs'):
                programs_map = self._seed_programs(site)
            else:
                from apps.academic.models import Program, Level
                programs_map = {p.code: p for p in Program.objects.filter(site=site)}

            if only in ('all', 'subjects'):
                subjects_map = self._seed_subjects()
                self._seed_level_subjects(programs_map, subjects_map)
            else:
                from apps.academic.models import Subject
                subjects_map = {s.code: s for s in Subject.objects.all()}

            if only in ('all', 'programs', 'subjects'):
                rooms_map = self._seed_rooms(site)
                semesters = self._seed_semesters(academic_year)
                classes_map = self._seed_classes(site, academic_year, programs_map)
            else:
                from apps.academic.models import Room, Semester, Class
                rooms_map = {r.code: r for r in Room.objects.filter(site=site)}
                semesters = list(Semester.objects.filter(academic_year=academic_year).order_by('start_date'))
                classes_map = {c.code: c for c in Class.objects.filter(site=site, academic_year=academic_year)}

            if only in ('all', 'teachers'):
                teachers_map = self._seed_teachers(site, classes_map, subjects_map, rooms_map)
            else:
                from apps.academic.models import TeacherProfile
                teachers_map = {t.employee_id: t for t in TeacherProfile.objects.select_related('user').all()}

            if only in ('all', 'students'):
                students = self._seed_students(site, academic_year, classes_map)
            else:
                from apps.students.models import Student
                students = list(Student.objects.filter(site=site))

            if only in ('all', 'finance'):
                self._seed_finance(site, academic_year, students)

            if only in ('all', 'grades'):
                self._seed_grades(site, academic_year, students, classes_map, subjects_map, semesters)

            if only in ('all', 'attendance'):
                self._seed_attendance(site, academic_year, students, classes_map)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Seed termine avec succes !'))
        self.stdout.write('')
        self.stdout.write('Comptes (mot de passe: campus2025):')
        self.stdout.write('  Admin:      admin@ita-abidjan.ci')
        self.stdout.write('  Enseignant: k.mensah@ita-abidjan.ci')
        self.stdout.write('  Etudiant:   voir console ci-dessus')

    # ─────────────────────────────────────────────────────────────────────────
    def _reset(self):
        self.stdout.write(self.style.WARNING('  [RESET] Suppression des donnees existantes...'))
        from apps.grades.models import Grade, Evaluation, ReportCard
        from apps.attendance.models import AttendanceRecord, AttendanceSession
        from apps.finance.models import Payment, Invoice, InvoiceItem
        from apps.academic.models import (
            Session, ClassSubjectTeacher, Enrollment, Class,
            TeacherSite, TeacherProfile, LevelSubject, Level, Program, Room, Semester
        )
        from apps.students.models import StudentParent, StudentCard, StudentFile, Student
        from apps.accounts.models import User

        ReportCard.objects.all().delete()
        Grade.objects.all().delete()
        Evaluation.objects.filter(is_locked=False).delete()
        AttendanceRecord.objects.all().delete()
        AttendanceSession.objects.all().delete()
        Payment.objects.all().delete()
        Invoice.objects.all().delete()
        Session.objects.all().delete()
        ClassSubjectTeacher.objects.all().delete()
        Enrollment.objects.all().delete()
        Class.objects.all().delete()
        TeacherSite.objects.all().delete()
        TeacherProfile.objects.all().delete()
        LevelSubject.objects.all().delete()
        Level.objects.all().delete()
        Program.objects.all().delete()
        Room.objects.filter(is_active=True).delete()
        Semester.objects.all().delete()
        StudentCard.objects.all().delete()
        StudentFile.objects.all().delete()
        StudentParent.objects.all().delete()
        User.objects.filter(user_type__in=['TEACHER', 'STUDENT', 'PARENT']).delete()
        self.stdout.write(self.style.WARNING('  [RESET] OK\n'))

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_core(self):
        from apps.core.models import Site, AcademicYear

        self._section('CORE — Site & Année académique')

        site, created = Site.objects.get_or_create(
            code=SITE_DATA['code'],
            defaults={k: v for k, v in SITE_DATA.items() if k != 'code'},
        )
        self._log('Site', site.name, created)

        ay, created = AcademicYear.objects.get_or_create(
            code=ACADEMIC_YEAR_DATA['code'],
            defaults={k: v for k, v in ACADEMIC_YEAR_DATA.items() if k != 'code'},
        )
        if created:
            AcademicYear.objects.exclude(pk=ay.pk).update(is_current=False)
        self._log('Année', ay.name, created)

        # Admin user
        from apps.accounts.models import User
        admin, created = User.objects.get_or_create(
            email='admin@ita-abidjan.ci',
            defaults={
                'first_name': 'Administrateur',
                'last_name': 'ITA',
                'user_type': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'site': site,
            }
        )
        if created:
            admin.set_password('campus2025')
            admin.save()
        self._log('Admin', admin.email, created)

        return site, ay

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_programs(self, site):
        from apps.academic.models import Program, Level

        self._section('PROGRAMMES & NIVEAUX')
        programs_map = {}

        for pdata in PROGRAMS:
            prog, created = Program.objects.get_or_create(
                code=pdata['code'],
                defaults={
                    'name': pdata['name'],
                    'description': pdata['description'],
                    'duration_years': pdata['duration_years'],
                    'site': site,
                }
            )
            self._log('Programme', f"{prog.code} — {prog.name}", created)
            programs_map[prog.code] = prog

            for ldata in pdata['levels']:
                lvl, created = Level.objects.get_or_create(
                    program=prog,
                    code=ldata['code'],
                    defaults={'name': ldata['name'], 'order': ldata['order']},
                )
                self._log('  Niveau', f"{prog.code}/{lvl.code} {lvl.name}", created)

        return programs_map

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_subjects(self):
        from apps.academic.models import Subject

        self._section('MATIÈRES')
        subjects_map = {}

        for sdata in SUBJECTS:
            subj, created = Subject.objects.get_or_create(
                code=sdata['code'],
                defaults={
                    'name': sdata['name'],
                    'coefficient': Decimal(str(sdata['coeff'])),
                    'hours_per_week': Decimal(str(sdata['hpw'])),
                }
            )
            self._log('Matière', f"{subj.code} — {subj.name}", created)
            subjects_map[subj.code] = subj

        return subjects_map

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_level_subjects(self, programs_map, subjects_map):
        from apps.academic.models import LevelSubject, Level

        self._section('MATIÈRES PAR NIVEAU')
        count = 0

        for prog_code, levels in LEVEL_SUBJECTS.items():
            prog = programs_map.get(prog_code)
            if not prog:
                continue
            for level_code, subj_codes in levels.items():
                try:
                    level = prog.levels.get(code=level_code)
                except Exception:
                    continue
                for subj_code in subj_codes:
                    subj = subjects_map.get(subj_code)
                    if not subj:
                        continue
                    ls, created = LevelSubject.objects.get_or_create(
                        level=level,
                        subject=subj,
                        defaults={
                            'coefficient': subj.coefficient,
                            'hours_per_week': subj.hours_per_week,
                            'is_mandatory': True,
                        }
                    )
                    if created:
                        count += 1

        self.stdout.write(f'  -> {count} associations matiere-niveau creees')

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_rooms(self, site):
        from apps.academic.models import Room

        self._section('SALLES')
        rooms_map = {}

        for rdata in ROOMS:
            room, created = Room.objects.get_or_create(
                code=rdata['code'],
                site=site,
                defaults={
                    'name': rdata['name'],
                    'room_type': rdata['room_type'],
                    'capacity': rdata['capacity'],
                    'building': rdata['building'],
                    'floor': rdata['floor'],
                }
            )
            self._log('Salle', f"{room.code} — {room.name} ({room.capacity} places)", created)
            rooms_map[room.code] = room

        return rooms_map

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_semesters(self, academic_year):
        from apps.academic.models import Semester

        self._section('SEMESTRES')
        semesters = []

        semester_data = [
            {'name': 'S1', 'label': 'Semestre 1 — 2025-2026',
             'start': datetime.date(2025, 9, 1), 'end': datetime.date(2026, 1, 31), 'is_current': False},
            {'name': 'S2', 'label': 'Semestre 2 — 2025-2026',
             'start': datetime.date(2026, 2, 1), 'end': datetime.date(2026, 7, 31), 'is_current': True},
        ]

        for sd in semester_data:
            sem, created = Semester.objects.get_or_create(
                academic_year=academic_year,
                name=sd['name'],
                defaults={
                    'label': sd['label'],
                    'start_date': sd['start'],
                    'end_date': sd['end'],
                    'is_current': sd['is_current'],
                }
            )
            self._log('Semestre', sem.label or sem.name, created)
            semesters.append(sem)

        return semesters

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_classes(self, site, academic_year, programs_map):
        from apps.academic.models import Class, Level

        self._section('CLASSES')
        classes_map = {}

        # On crée une classe par niveau (L1, L2, L3) × programme (INFO, GEST, DROIT)
        class_defs = []
        ay_short = '2526'
        for prog_code, prog in programs_map.items():
            for ldata in PROGRAMS[[p['code'] for p in PROGRAMS].index(prog_code)]['levels']:
                level_code = ldata['code']
                try:
                    level = prog.levels.get(code=level_code)
                except Exception:
                    continue
                code = f"{level_code}-{prog_code}-{ay_short}"
                name = f"{ldata['name']} {prog.name[:20]} {academic_year.name}"
                class_defs.append({
                    'code': code, 'name': name, 'level': level,
                    'max_students': 35 if prog_code == 'INFO' else 45,
                })

        for cdef in class_defs:
            cls, created = Class.objects.get_or_create(
                code=cdef['code'],
                academic_year=academic_year,
                site=site,
                defaults={
                    'name': cdef['name'],
                    'level': cdef['level'],
                    'max_students': cdef['max_students'],
                }
            )
            self._log('Classe', f"{cls.code} — {cls.level.program.code}/{cls.level.code}", created)
            classes_map[cls.code] = cls

        return classes_map

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_teachers(self, site, classes_map, subjects_map, rooms_map):
        from apps.accounts.models import User
        from apps.academic.models import TeacherProfile, TeacherSite, ClassSubjectTeacher, Session, Level

        self._section('ENSEIGNANTS')
        teachers_map = {}
        rooms = list(rooms_map.values())
        room_cycle = rooms[2:]  # skip amphi for teacher sessions

        # Build subject → classes mapping for assignments
        subj_to_classes = {}
        for cls in classes_map.values():
            level = cls.level
            prog_code = level.program.code
            level_code = level.code
            subj_codes = LEVEL_SUBJECTS.get(prog_code, {}).get(level_code, [])
            for sc in subj_codes:
                subj_to_classes.setdefault(sc, []).append(cls)

        time_slots = [
            (datetime.time(7, 30),  datetime.time(9, 30)),
            (datetime.time(9, 30),  datetime.time(11, 30)),
            (datetime.time(11, 30), datetime.time(13, 30)),
            (datetime.time(14, 0),  datetime.time(16, 0)),
            (datetime.time(16, 0),  datetime.time(18, 0)),
        ]
        day_slot_counter = {}  # (day, slot_idx) → used

        for i, tdata in enumerate(TEACHERS):
            user, created = User.objects.get_or_create(
                email=tdata['email'],
                defaults={
                    'first_name': tdata['first_name'],
                    'last_name': tdata['last_name'],
                    'phone': tdata['phone'],
                    'user_type': 'TEACHER',
                    'site': site,
                    'is_active': True,
                }
            )
            if created:
                user.set_password('campus2025')
                user.save()

            profile, pcreated = TeacherProfile.objects.get_or_create(
                user=user,
                defaults={
                    'employee_id': tdata['employee_id'],
                    'specialization': tdata['specialization'],
                    'qualification': tdata['qualification'],
                    'contract_type': tdata['contract_type'],
                    'hire_date': datetime.date(2022, 9, 1),
                    'hourly_rate': tdata['hourly_rate'],
                    'bio': tdata.get('bio', ''),
                }
            )
            if not pcreated:
                # Update bio if added later
                if tdata.get('bio') and not profile.bio:
                    profile.bio = tdata['bio']
                    profile.save()

            TeacherSite.objects.get_or_create(
                teacher=profile, site=site,
                defaults={'is_primary': True}
            )

            # Affectations et séances
            aff_count = 0
            sess_count = 0

            for subj_code in tdata['subjects']:
                subj = subjects_map.get(subj_code)
                if not subj:
                    continue
                target_classes = subj_to_classes.get(subj_code, [])[:2]  # max 2 classes par matière
                for cls in target_classes:
                    cst, _ = ClassSubjectTeacher.objects.get_or_create(
                        class_obj=cls,
                        subject=subj,
                        defaults={'teacher': profile}
                    )
                    aff_count += 1

                    # Créer une séance récurrente si pas déjà existante
                    if not Session.objects.filter(class_obj=cls, subject=subj, teacher=profile).exists():
                        # Chercher un créneau libre
                        slot_found = False
                        for day in range(6):  # Lundi-Samedi
                            for si, (start, end) in enumerate(time_slots):
                                key = (day, si)
                                if day_slot_counter.get(key, 0) < 3:  # max 3 cours par créneau
                                    room = room_cycle[(day * 5 + si) % len(room_cycle)]
                                    Session.objects.create(
                                        class_obj=cls,
                                        subject=subj,
                                        teacher=profile,
                                        room=room,
                                        day_of_week=day,
                                        start_time=start,
                                        end_time=end,
                                        is_recurring=True,
                                    )
                                    day_slot_counter[key] = day_slot_counter.get(key, 0) + 1
                                    sess_count += 1
                                    slot_found = True
                                    break
                            if slot_found:
                                break

            self._log(
                'Enseignant',
                f"{profile.employee_id} {user.full_name} ({tdata['contract_type']}) "
                f"— {aff_count} affectations, {sess_count} séances",
                pcreated
            )
            teachers_map[profile.employee_id] = profile

        return teachers_map

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_students(self, site, academic_year, classes_map):
        from apps.accounts.models import User
        from apps.students.models import Student, Parent, StudentParent
        from apps.academic.models import Enrollment

        self._section('ÉTUDIANTS & INSCRIPTIONS')

        students_all = []
        random.seed(42)  # reproducible

        # Distribuer les étudiants : 8 par classe INFO-L1, 6 par L2, 5 par L3 ; pareils pour GEST et DROIT
        distribution = {}
        for code, cls in classes_map.items():
            prog = cls.level.program.code
            level = cls.level.code
            if prog == 'INFO':
                n = 8 if level == 'L1' else (6 if level == 'L2' else 5)
            elif prog == 'GEST':
                n = 7 if level == 'L1' else (5 if level == 'L2' else 4)
            else:  # DROIT
                n = 6 if level == 'L1' else (4 if level == 'L2' else 3)
            distribution[code] = n

        first_student_email = None
        student_idx = 0

        for class_code, n_students in distribution.items():
            cls = classes_map[class_code]

            for j in range(n_students):
                gender = 'M' if random.random() > 0.45 else 'F'
                first_names = FIRST_NAMES_M if gender == 'M' else FIRST_NAMES_F
                fname = first_names[(student_idx * 3 + j) % len(first_names)]
                lname = LAST_NAMES[(student_idx + j * 2) % len(LAST_NAMES)]
                email = f"{fname.lower().replace('-', '.').replace(' ', '.')}.{lname.lower()}.{student_idx+1:02d}@ita-abidjan.ci"
                birth_year = random.randint(2000, 2004)
                city = CITIES[student_idx % len(CITIES)]

                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': fname,
                        'last_name': lname,
                        'phone': f"+2250{random.randint(7,9)}{random.randint(10000000, 99999999)}",
                        'user_type': 'STUDENT',
                        'site': site,
                        'is_active': True,
                    }
                )
                if created:
                    user.set_password('campus2025')
                    user.save()

                student, scr = Student.objects.get_or_create(
                    user=user,
                    defaults={
                        'site': site,
                        'gender': gender,
                        'birth_date': datetime.date(birth_year, random.randint(1, 12), random.randint(1, 28)),
                        'birth_place': city,
                        'nationality': 'Ivoirienne',
                        'address': f"Quartier {random.choice(['Cocody', 'Yopougon', 'Adjamé', 'Marcory', 'Treichville'])}, {city}",
                        'city': city,
                        'status': 'ACTIVE',
                        'admission_date': datetime.date(2025, 9, 1),
                        'registration_fee': 150000,
                        'is_enrolled': random.random() > 0.1,
                        'tuition_fee': 1800000,
                        'total_paid': random.randint(900000, 1800000),
                        'remaining_balance': 0,
                    }
                )
                if not scr:
                    student.total_paid = min(student.tuition_fee, student.total_paid or 900000)
                    student.remaining_balance = max(0, int(student.tuition_fee) - int(student.total_paid))
                    student.save()

                # Enrollment
                Enrollment.objects.get_or_create(
                    student=student,
                    academic_year=academic_year,
                    defaults={
                        'class_obj': cls,
                        'status': 'ENROLLED',
                    }
                )

                if first_student_email is None and scr:
                    first_student_email = email

                students_all.append(student)
                student_idx += 1

            self.stdout.write(f'  Classe {class_code}: {n_students} étudiants')

        # Créer un parent pour les 3 premiers étudiants
        for stu in students_all[:3]:
            parent_user, _ = User.objects.get_or_create(
                email=f"parent.{stu.user.last_name.lower()}.{stu.user.first_name.lower()}@ita-abidjan.ci",
                defaults={
                    'first_name': random.choice(['Jean', 'Kofi', 'Mamadou', 'Suzanne', 'Marie']),
                    'last_name': stu.user.last_name,
                    'user_type': 'PARENT',
                    'site': site,
                    'is_active': True,
                }
            )
            if parent_user.pk and not hasattr(parent_user, '_pw_set'):
                parent_user.set_password('campus2025')
                parent_user.save()

            from apps.students.models import Parent
            parent, _ = Parent.objects.get_or_create(
                user=parent_user,
                defaults={
                    'relationship': 'FATHER',
                    'profession': random.choice(['Ingénieur', 'Commerçant', 'Fonctionnaire', 'Médecin']),
                    'city': stu.city,
                    'emergency_contact': parent_user.phone or '+22507000000',
                }
            )
            StudentParent.objects.get_or_create(
                student=stu,
                parent=parent,
                defaults={'is_primary': True, 'can_pickup': True}
            )

        self.stdout.write(f'  -> {len(students_all)} etudiants au total')
        if first_student_email:
            self.stdout.write(f'  Premier étudiant créé : {first_student_email}')

        return students_all

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_finance(self, site, academic_year, students):
        from apps.finance.models import FeeType, Invoice, InvoiceItem, PaymentMethod, Payment

        self._section('FINANCE — Frais & Paiements')

        # Fee types
        fee_types = {}
        for ftd in FEE_TYPES:
            ft, _ = FeeType.objects.get_or_create(
                code=ftd['code'],
                defaults={
                    'name': ftd['name'],
                    'default_amount': ftd['amount'],
                    'is_recurring': ftd['recurring'],
                }
            )
            fee_types[ft.code] = ft

        # Payment methods
        pay_methods = {}
        for pmd in PAYMENT_METHODS:
            pm, _ = PaymentMethod.objects.get_or_create(
                code=pmd['code'],
                defaults={'name': pmd['name'], 'is_online': pmd['is_online']}
            )
            pay_methods[pm.code] = pm

        invoice_count = 0
        payment_count = 0
        random.seed(99)

        for student in students[:20]:  # 20 premiers étudiants
            # Vérifier si l'étudiant a déjà une facture
            if Invoice.objects.filter(student=student, academic_year=academic_year).exists():
                continue

            due = datetime.date(2025, 10, 31)
            invoice = Invoice(
                student=student,
                site=site,
                academic_year=academic_year,
                due_date=due,
                status='DRAFT',
            )
            invoice.save()  # auto-generates invoice_number

            # Items
            total = Decimal('0')
            for ft_code in ['INSCRIPTION', 'SCOLARITE_S1', 'EXAMEN']:
                ft = fee_types.get(ft_code)
                if not ft:
                    continue
                item_total = Decimal(str(ft.default_amount))
                InvoiceItem.objects.create(
                    invoice=invoice,
                    fee_type=ft,
                    description=ft.name,
                    quantity=1,
                    unit_price=item_total,
                    total=item_total,
                )
                total += item_total

            invoice.subtotal = total
            invoice.total = total
            invoice.balance = total
            invoice.status = 'SENT'
            invoice.save()

            # Paiement partiel ou total (aléatoire)
            paid_ratio = random.choice([0.5, 0.75, 1.0])
            paid_amount = int(float(total) * paid_ratio)
            if paid_amount > 0:
                payment = Payment(
                    invoice=invoice,
                    payment_method=pay_methods.get('ESPECES') or list(pay_methods.values())[0],
                    amount=Decimal(str(paid_amount)),
                    status='SUCCESS',
                )
                payment.save()
                invoice.amount_paid = Decimal(str(paid_amount))
                invoice.balance = total - Decimal(str(paid_amount))
                invoice.status = 'PAID' if paid_ratio == 1.0 else 'PARTIAL'
                invoice.save()
                payment_count += 1

            invoice_count += 1

        self.stdout.write(f'  -> {invoice_count} factures, {payment_count} paiements crees')

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_grades(self, site, academic_year, students, classes_map, subjects_map, semesters):
        from apps.grades.models import GradeCategory, Evaluation, Grade, ReportCard
        from apps.academic.models import Enrollment

        self._section('ÉVALUATIONS & NOTES')

        # Catégories
        cats = {}
        for gcd in GRADE_CATEGORIES:
            cat, _ = GradeCategory.objects.get_or_create(
                code=gcd['code'],
                defaults={'name': gcd['name'], 'weight': gcd['weight']}
            )
            cats[cat.code] = cat

        sem1 = semesters[0] if semesters else None
        if not sem1:
            self.stdout.write('  Aucun semestre trouvé, skip')
            return

        eval_count = 0
        grade_count = 0
        random.seed(77)

        # Pour chaque classe, créer des évaluations pour les matières principales
        for class_code, cls in list(classes_map.items())[:4]:  # 4 premières classes
            prog_code = cls.level.program.code
            level_code = cls.level.code
            subj_codes = LEVEL_SUBJECTS.get(prog_code, {}).get(level_code, [])[:4]  # 4 matières max

            enrolled_students = [
                e.student for e in cls.enrollments.select_related('student').filter(is_active=True)
            ]
            if not enrolled_students:
                continue

            for subj_code in subj_codes:
                subj = subjects_map.get(subj_code)
                if not subj:
                    continue

                # Contrôle continu S1
                ev_cc, created = Evaluation.objects.get_or_create(
                    title=f'CC1 {subj.code} — {cls.code}',
                    subject=subj,
                    class_group=cls,
                    semester=sem1,
                    defaults={
                        'eval_type': 'DEVOIR',
                        'date': datetime.date(2025, 11, 15),
                        'max_score': Decimal('20'),
                        'coefficient': Decimal('1'),
                    }
                )
                if created:
                    eval_count += 1

                # Examen final S1
                ev_ex, created = Evaluation.objects.get_or_create(
                    title=f'EXAM S1 {subj.code} — {cls.code}',
                    subject=subj,
                    class_group=cls,
                    semester=sem1,
                    defaults={
                        'eval_type': 'EXAMEN',
                        'date': datetime.date(2026, 1, 20),
                        'max_score': Decimal('20'),
                        'coefficient': Decimal('2'),
                    }
                )
                if created:
                    eval_count += 1

                for stu in enrolled_students:
                    for ev, cat_code in [(ev_cc, 'CC'), (ev_ex, 'EXAM')]:
                        if not Grade.objects.filter(student=stu, evaluation=ev).exists():
                            score = Decimal(str(round(random.uniform(7.0, 19.5), 2)))
                            Grade.objects.create(
                                student=stu,
                                subject=subj,
                                class_group=cls,
                                semester=sem1,
                                evaluation=ev,
                                category=cats.get(cat_code),
                                score=score,
                                max_score=Decimal('20'),
                                date=ev.date,
                            )
                            grade_count += 1

        # Bulletin pour les 5 premiers étudiants
        rc_count = 0
        for student in students[:5]:
            enr = student.enrollments.filter(academic_year=academic_year, is_active=True).first()
            if not enr:
                continue
            cls = enr.class_obj
            if not ReportCard.objects.filter(student=student, class_group=cls, semester=sem1).exists():
                grades = Grade.objects.filter(student=student, class_group=cls, semester=sem1)
                if grades.exists():
                    avg = sum(float(g.score) for g in grades) / grades.count()
                    rc = ReportCard.objects.create(
                        student=student,
                        class_group=cls,
                        semester=sem1,
                        average=Decimal(str(round(avg, 2))),
                        total_students=cls.enrollments.filter(is_active=True).count(),
                        status='PASS' if avg >= 10 else 'FAIL',
                        teacher_comment='Bon travail, continuez ainsi.' if avg >= 12 else 'Des efforts supplémentaires sont nécessaires.',
                        is_published=True,
                    )
                    rc_count += 1

        self.stdout.write(f'  -> {eval_count} evaluations, {grade_count} notes, {rc_count} bulletins crees')

    # ─────────────────────────────────────────────────────────────────────────
    def _seed_attendance(self, site, academic_year, students, classes_map):
        from apps.attendance.models import AttendanceSession, AttendanceRecord
        from apps.academic.models import Session as AcademicSession

        self._section('PRÉSENCES')
        random.seed(55)

        att_sess_count = 0
        att_rec_count = 0

        # Prendre les 3 premières classes et leurs sessions
        for class_code in list(classes_map.keys())[:3]:
            cls = classes_map[class_code]
            sessions = AcademicSession.objects.filter(class_obj=cls, is_active=True)[:4]
            enrolled = list(
                cls.enrollments.select_related('student').filter(is_active=True)
            )
            if not enrolled:
                continue

            for sess in sessions:
                # 3 occurrences de cette séance (3 semaines)
                for week_offset in range(3):
                    sess_date = sess.specific_date or (
                        datetime.date(2025, 10, 6) + datetime.timedelta(weeks=week_offset, days=sess.day_of_week)
                    )

                    att_sess, created = AttendanceSession.objects.get_or_create(
                        session=sess,
                        date=sess_date,
                        defaults={'status': 'CLOSED'}
                    )
                    if created:
                        att_sess_count += 1

                    for enr in enrolled:
                        stu = enr.student
                        if AttendanceRecord.objects.filter(attendance_session=att_sess, student=stu).exists():
                            continue
                        status = random.choices(
                            ['PRESENT', 'ABSENT', 'LATE'],
                            weights=[75, 15, 10], k=1
                        )[0]
                        AttendanceRecord.objects.create(
                            attendance_session=att_sess,
                            student=stu,
                            status=status,
                            check_in_method='MANUAL',
                        )
                        att_rec_count += 1

        self.stdout.write(f'  -> {att_sess_count} seances de presence, {att_rec_count} pointages crees')

    # ─────────────────────────────────────────────────────────────────────────
    def _section(self, title):
        self.stdout.write(f'\n  {self.style.MIGRATE_HEADING(f"-- {title} --")}')

    def _log(self, kind, name, created):
        icon = '+' if created else '.'
        color = self.style.SUCCESS if created else self.style.WARNING
        self.stdout.write(color(f'  {icon} [{kind}] {name}'))
