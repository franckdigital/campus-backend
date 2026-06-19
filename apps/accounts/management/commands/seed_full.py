"""
seed_full.py  —  Wipe DB + 2 realistic accounts per actor, full data for all modules.
Usage: python manage.py seed_full
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, datetime

ADMIN_PWD = 'Admin2024!'
DEMO_PWD  = 'Campus2024!'

def _dt(d, h=10, m=0):
    return timezone.make_aware(datetime(d.year, d.month, d.day, h, m))


class Command(BaseCommand):
    help = 'Wipe the database and seed 2 accounts per actor with complete demo data'

    def handle(self, *args, **options):
        print('\n=== NETTOYAGE ===')
        self._clean()

        print('\n=== DONNEES DE REFERENCE ===')
        site        = self._site()
        ay          = self._academic_year(site)
        s1, s2      = self._semesters(ay)
        _prg, lvls  = self._programs_levels(site)
        subjs       = self._subjects()
        self._level_subjects(lvls, subjs)
        rooms       = self._rooms(site)

        print('\n=== COMPTES ===')
        admins   = self._admins(site)
        staffs   = self._staffs(site)
        teachers = self._teachers(site)
        students, parents = self._students_parents(site)

        print('\n=== STRUCTURE ACADEMIQUE ===')
        classes  = self._classes(lvls, ay, site, teachers)
        self._class_subject_teacher(classes, subjs, teachers)
        sessions = self._sessions(classes, subjs, teachers, rooms)
        self._enrollments(students, classes, ay)

        print('\n=== FINANCE ===')
        fee_types, pay_methods = self._finance_config(site)
        self._invoices_payments(students, site, ay, fee_types, pay_methods, staffs)

        print('\n=== NOTES ===')
        self._grades(students, classes[0], subjs, teachers, s1)

        print('\n=== PRESENCES ===')
        self._attendance(sessions, students)

        print('\n=== COMPTABILITE ===')
        self._bank_and_expenses(site, pay_methods, admins)

        self._summary()

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
    # 2. DONNEES DE REFERENCE
    # =========================================================================

    def _site(self):
        from apps.core.models import Site
        site, _ = Site.objects.get_or_create(
            code='ITA',
            defaults=dict(
                name="Institut de Technologie d'Abidjan",
                address='Boulevard de la Paix, Cocody',
                city='Abidjan',
                country='CI',
                phone='+225 27 22 48 00 00',
                email='contact@ita.ci',
                is_main=True,
            ),
        )
        print(f'  Site: {site.name}')
        return site

    def _academic_year(self, site):
        from apps.core.models import AcademicYear
        ay = AcademicYear.objects.create(
            name='2024-2025',
            code='AY-2024-2025',
            start_date=date(2024, 9, 2),
            end_date=date(2025, 6, 28),
            is_current=True,
            registration_open=True,
        )
        print(f'  Annee academique: {ay.name}')
        return ay

    def _semesters(self, ay):
        from apps.academic.models import Semester
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
        print('  Semestres: S1, S2')
        return s1, s2

    def _programs_levels(self, site):
        from apps.academic.models import Program, Level
        li = Program.objects.create(
            name='Licence Informatique', code='LI',
            description='Licence professionnelle en Informatique et Genie Logiciel',
            duration_years=3, site=site,
        )
        bts = Program.objects.create(
            name='BTS Comptabilite', code='BTS-COMPTA',
            description='Brevet de Technicien Superieur en Comptabilite et Gestion',
            duration_years=2, site=site,
        )
        l1 = Level.objects.create(name='Licence 1', code='L1', order=1, program=li)
        l2 = Level.objects.create(name='Licence 2', code='L2', order=2, program=li)
        l3 = Level.objects.create(name='Licence 3', code='L3', order=3, program=li)
        print(f'  Programmes: LI, BTS-COMPTA | Niveaux: L1, L2, L3')
        return [li, bts], [l1, l2, l3]

    def _subjects(self):
        from apps.academic.models import Subject
        data = [
            ('ALG101', 'Algorithmique et structures de donnees', 4, 4),
            ('PRG101', 'Programmation Python',                   3, 3),
            ('MAT101', 'Mathematiques discretes',                3, 3),
            ('RES101', 'Reseaux informatiques',                  3, 3),
            ('BDD101', 'Bases de donnees relationnelles',        3, 4),
            ('ANG101', 'Anglais technique',                      2, 2),
            ('COM101', 'Communication professionnelle',          2, 2),
            ('SYS201', "Systemes d'exploitation",                3, 3),
            ('WEB201', 'Developpement web full-stack',           4, 4),
            ('MAT201', 'Analyse et algebre lineaire',            3, 3),
        ]
        subjs = {}
        for code, name, coef, hpw in data:
            subjs[code] = Subject.objects.create(
                name=name, code=code, coefficient=coef, hours_per_week=hpw,
            )
        print(f'  Matieres: {len(subjs)}')
        return subjs

    def _level_subjects(self, lvls, subjs):
        from apps.academic.models import LevelSubject
        l1_codes = ['ALG101', 'PRG101', 'MAT101', 'RES101', 'BDD101', 'ANG101', 'COM101']
        l2_codes = ['SYS201', 'WEB201', 'MAT201', 'BDD101', 'RES101', 'ANG101']
        for code in l1_codes:
            LevelSubject.objects.create(level=lvls[0], subject=subjs[code], is_mandatory=True)
        for code in l2_codes:
            LevelSubject.objects.create(level=lvls[1], subject=subjs[code], is_mandatory=True)

    def _rooms(self, site):
        from apps.academic.models import Room
        data = [
            ('AMPHI-A',  'Amphitheatre A',      200, 'AMPHITHEATER'),
            ('SALLE-101','Salle 101',             40, 'CLASSROOM'),
            ('SALLE-102','Salle 102',             35, 'CLASSROOM'),
            ('LABO-INFO','Laboratoire Informatique', 30, 'LAB'),
            ('SALLE-201','Salle 201',             40, 'CLASSROOM'),
        ]
        rooms = {}
        for code, name, cap, rtype in data:
            rooms[code] = Room.objects.create(
                name=name, code=code, site=site,
                building='Batiment A', floor='1',
                capacity=cap, room_type=rtype,
            )
        print(f'  Salles: {len(rooms)}')
        return rooms

    # =========================================================================
    # 3. COMPTES
    # =========================================================================

    def _make_user(self, site, email, fname, lname, utype, pwd,
                   is_staff=False, is_super=False):
        from apps.accounts.models import User
        u = User.objects.create(
            email=email, first_name=fname, last_name=lname,
            user_type=utype, is_active=True,
            is_staff=is_staff, is_superuser=is_super, site=site,
        )
        u.set_password(pwd)
        u.save()
        return u

    def _admins(self, site):
        users = [
            self._make_user(site, 'yao.koffi@ita.ci',      'Koffi Emmanuel', 'Yao',       'ADMIN', ADMIN_PWD, True, True),
            self._make_user(site, 'nguessan.adjoua@ita.ci', 'Adjoua Patricia','N\'Guessan','ADMIN', ADMIN_PWD, True, False),
        ]
        for u in users:
            print(f'  [ADMIN]   {u.email}')
        return users

    def _staffs(self, site):
        users = [
            self._make_user(site, 'sery.fatou@ita.ci',    'Fatou Benedicte', 'Sery',   'STAFF', DEMO_PWD),
            self._make_user(site, 'konate.ismael@ita.ci', 'Ismael',          'Konate', 'STAFF', DEMO_PWD),
        ]
        for u in users:
            print(f'  [STAFF]   {u.email}')
        return users

    def _teachers(self, site):
        from apps.academic.models import TeacherProfile, TeacherSite
        data = [
            ('brou.marc@ita.ci',     'Marc-Antoine', 'Brou',    'Informatique',  'Doctorat en Informatique',      date(2021, 9, 1),  'PERMANENT', 'PROF-001'),
            ('diabate.amara@ita.ci', 'Amara',         'Diabate', 'Mathematiques', 'Master en Mathematiques Pures', date(2022, 1, 15), 'PERMANENT', 'PROF-002'),
        ]
        teachers = []
        for email, fn, ln, spec, qual, hire, ctype, emp_id in data:
            u = self._make_user(site, email, fn, ln, 'TEACHER', DEMO_PWD)
            prof = TeacherProfile.objects.create(
                user=u, employee_id=emp_id,
                specialization=spec, qualification=qual,
                hire_date=hire, contract_type=ctype, hourly_rate=15000,
            )
            TeacherSite.objects.create(teacher=prof, site=site, is_primary=True)
            teachers.append(prof)
            print(f'  [TEACHER] {email}')
        return teachers

    def _students_parents(self, site):
        from apps.students.models import Student, Parent, StudentParent

        # --- Etudiant 1 : Ibrahim ---
        u1 = self._make_user(site, 'kone.ibrahim@ita.ci', 'Ibrahim Desire', 'Kone', 'STUDENT', DEMO_PWD)
        s1 = Student.objects.create(
            user=u1, matricule='ITA-2024-001', gender='M',
            birth_date=date(2003, 1, 22), birth_place='Bouake',
            nationality='Ivoirienne', address='Quartier Residentiel, Rue 14',
            city='Abidjan', site=site, status='ACTIVE',
            admission_date=date(2024, 9, 2),
            emergency_contact_name='Kone Mamadou',
            emergency_contact_phone='+225 07 07 07 07 07',
            emergency_contact_relation='Pere',
            registration_fee=75000, registration_fee_paid=True,
            tuition_fee=675000, total_paid=600000, remaining_balance=75000,
        )

        # --- Etudiante 2 : Aicha ---
        u2 = self._make_user(site, 'traore.aicha@ita.ci', 'Aicha Mariame', 'Traore', 'STUDENT', DEMO_PWD)
        s2 = Student.objects.create(
            user=u2, matricule='ITA-2024-002', gender='F',
            birth_date=date(2002, 8, 15), birth_place='Abidjan',
            nationality='Ivoirienne', address='Cocody Angre, Rue 42B',
            city='Abidjan', site=site, status='ACTIVE',
            admission_date=date(2024, 9, 2),
            emergency_contact_name='Coulibaly Rokia',
            emergency_contact_phone='+225 05 05 05 05 05',
            emergency_contact_relation='Mere',
            registration_fee=75000, registration_fee_paid=True,
            tuition_fee=675000, total_paid=675000, remaining_balance=0,
        )

        # --- Parent 1 : Pere d'Ibrahim ---
        pu1 = self._make_user(site, 'kone.mamadou@ita.ci', 'Mamadou', 'Kone', 'PARENT', DEMO_PWD)
        p1 = Parent.objects.create(
            user=pu1, profession='Ingenieur Civil', employer='BNETD',
            address='Yopougon, Cite SOGEFIA', city='Abidjan',
            relationship='FATHER', emergency_contact='+225 07 07 07 07 07',
        )
        StudentParent.objects.create(
            student=s1, parent=p1,
            is_primary=True, can_pickup=True, receives_notifications=True,
        )

        # --- Parent 2 : Mere d'Aicha ---
        pu2 = self._make_user(site, 'coulibaly.rokia@ita.ci', 'Rokia', 'Coulibaly', 'PARENT', DEMO_PWD)
        p2 = Parent.objects.create(
            user=pu2, profession='Commercante', employer='Auto-entrepreneur',
            address='Adjame, Quartier Commerce', city='Abidjan',
            relationship='MOTHER', emergency_contact='+225 05 05 05 05 05',
        )
        StudentParent.objects.create(
            student=s2, parent=p2,
            is_primary=True, can_pickup=True, receives_notifications=True,
        )

        print(f'  [STUDENT] {u1.email}')
        print(f'  [STUDENT] {u2.email}')
        print(f'  [PARENT]  {pu1.email}  (pere de Ibrahim)')
        print(f'  [PARENT]  {pu2.email}  (mere de Aicha)')
        return [s1, s2], [p1, p2]

    # =========================================================================
    # 4. STRUCTURE ACADEMIQUE
    # =========================================================================

    def _classes(self, lvls, ay, site, teachers):
        from apps.academic.models import Class as ClassModel
        c1 = ClassModel.objects.create(
            name='L1 Informatique A', code='L1-INFO-A',
            level=lvls[0], academic_year=ay, site=site,
            max_students=35, main_teacher=teachers[0],
        )
        c2 = ClassModel.objects.create(
            name='L2 Informatique A', code='L2-INFO-A',
            level=lvls[1], academic_year=ay, site=site,
            max_students=30, main_teacher=teachers[0],
        )
        print(f'  Classes: {c1.code}, {c2.code}')
        return [c1, c2]

    def _class_subject_teacher(self, classes, subjs, teachers):
        from apps.academic.models import ClassSubjectTeacher
        # unique_together = ['class_obj', 'subject'] — 1 teacher per subject per class
        l1 = [
            ('ALG101', 0), ('PRG101', 0), ('BDD101', 0),
            ('MAT101', 1), ('RES101', 1), ('ANG101', 1), ('COM101', 1),
        ]
        l2 = [
            ('SYS201', 0), ('WEB201', 0), ('BDD101', 0),
            ('MAT201', 1), ('RES101', 1), ('ANG101', 1),
        ]
        for cls, assignments in [(classes[0], l1), (classes[1], l2)]:
            for code, tidx in assignments:
                ClassSubjectTeacher.objects.create(
                    class_obj=cls, subject=subjs[code], teacher=teachers[tidx],
                )
        print(f'  Affectations matieres-enseignants: {len(l1)+len(l2)}')

    def _sessions(self, classes, subjs, teachers, rooms):
        from apps.academic.models import Session as AcaSession
        # L1 emploi du temps (day_of_week: 0=Lundi ... 5=Samedi)
        l1_data = [
            (0, time(8,  0), time(10, 0), 'ALG101', 0, 'SALLE-101'),
            (0, time(10,30), time(12,30), 'PRG101', 0, 'LABO-INFO'),
            (1, time(8,  0), time(10, 0), 'MAT101', 1, 'SALLE-101'),
            (1, time(10,30), time(12,30), 'RES101', 1, 'SALLE-102'),
            (2, time(8,  0), time(10, 0), 'BDD101', 0, 'LABO-INFO'),
            (2, time(10,30), time(12,30), 'ANG101', 1, 'SALLE-101'),
            (3, time(8,  0), time(10, 0), 'ALG101', 0, 'SALLE-101'),
            (3, time(10,30), time(12,30), 'COM101', 1, 'SALLE-102'),
            (4, time(8,  0), time(10, 0), 'PRG101', 0, 'LABO-INFO'),
            (4, time(10,30), time(12,30), 'MAT101', 1, 'SALLE-101'),
        ]
        l2_data = [
            (1, time(14, 0), time(16, 0), 'SYS201', 0, 'LABO-INFO'),
            (3, time(14, 0), time(16, 0), 'WEB201', 0, 'LABO-INFO'),
            (4, time(14, 0), time(16, 0), 'MAT201', 1, 'SALLE-201'),
        ]
        l1_sessions = []
        for day, start, end, code, tidx, room_code in l1_data:
            sess = AcaSession.objects.create(
                class_obj=classes[0], subject=subjs[code],
                teacher=teachers[tidx], room=rooms[room_code],
                day_of_week=day, start_time=start, end_time=end,
                is_recurring=True,
            )
            l1_sessions.append(sess)
        for day, start, end, code, tidx, room_code in l2_data:
            AcaSession.objects.create(
                class_obj=classes[1], subject=subjs[code],
                teacher=teachers[tidx], room=rooms[room_code],
                day_of_week=day, start_time=start, end_time=end,
                is_recurring=True,
            )
        print(f'  Seances: {len(l1_data)} (L1) + {len(l2_data)} (L2)')
        return l1_sessions

    def _enrollments(self, students, classes, ay):
        from apps.academic.models import Enrollment
        # unique_together = ['student', 'academic_year']
        for s in students:
            Enrollment.objects.create(
                student=s, class_obj=classes[0], academic_year=ay,
                status='ENROLLED',
            )
        print(f'  Inscriptions: {len(students)} etudiants -> L1-INFO-A')

    # =========================================================================
    # 5. FINANCE
    # =========================================================================

    def _finance_config(self, site):
        from apps.finance.models import FeeType, PaymentMethod
        fee_types = {}
        for code, name, amt, recur in [
            ('INSCRIPTION',  "Frais d'inscription",    75000,  False),
            ('SCOLARITE-S1', 'Frais de scolarite S1', 300000, True),
            ('SCOLARITE-S2', 'Frais de scolarite S2', 300000, True),
            ('EXAMENS',      "Frais d'examens",         25000, True),
        ]:
            fee_types[code] = FeeType.objects.create(
                name=name, code=code, default_amount=amt, is_recurring=recur,
            )

        pay_methods = {}
        for code, name, online in [
            ('CASH',     'Especes',                    False),
            ('VIREMENT', 'Virement bancaire',          False),
            ('MOBILE',   'Mobile Money (MTN/Orange)',  True),
        ]:
            pay_methods[code] = PaymentMethod.objects.create(
                name=name, code=code, is_online=online,
            )

        print(f'  Types de frais: {len(fee_types)} | Modes de paiement: {len(pay_methods)}')
        return fee_types, pay_methods

    def _invoices_payments(self, students, site, ay, fee_types, pay_methods, staffs):
        from apps.finance.models import Invoice, InvoiceItem, Payment
        receiver = staffs[1]  # konate.ismael — agent financier

        for i, student in enumerate(students):
            fully_paid = (i == 1)  # Aicha est completement a jour

            # ----------------------------------------------------------------
            # Facture 1 : Inscription + S1  (entierement payee)
            # Invoice.save() appelle calculate_totals() qui lit self.items —
            # on cree donc les lignes AVANT de rappeler .save() pour avoir les
            # bons montants (total, subtotal, balance, status).
            # ----------------------------------------------------------------
            inv1 = Invoice.objects.create(
                student=student, site=site, academic_year=ay,
                invoice_number=f'FAC-2024-{i+1:03d}',
                due_date=date(2024, 9, 30),
                amount_paid=375000,
                created_by=receiver,
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
            inv1.save()  # recalcule: subtotal=375000, total=375000, balance=0, status=PAID
            Invoice.objects.filter(pk=inv1.pk).update(issue_date=date(2024, 9, 2))

            p1 = Payment.objects.create(
                payment_number=f'PAY-2024-{i*10+1:03d}',
                invoice=inv1,
                payment_method=pay_methods['CASH'],
                amount=375000, status='SUCCESS',
                reference=f'REF-CASH-{2024}{i+1:02d}01',
                received_by=receiver, validated_by=receiver,
                validated_at=_dt(date(2024, 9, 5)),
            )
            Payment.objects.filter(pk=p1.pk).update(payment_date=_dt(date(2024, 9, 5)))

            # ----------------------------------------------------------------
            # Facture 2 : S2
            # Ibrahim : 0 paye → balance=300000, status=OVERDUE (echeance depassee)
            # Aicha   : 300000 paye → balance=0, status=PAID
            # ----------------------------------------------------------------
            s2_paid = 300000 if fully_paid else 225000
            inv2 = Invoice.objects.create(
                student=student, site=site, academic_year=ay,
                invoice_number=f'FAC-2025-{i+1:03d}',
                due_date=date(2025, 2, 15),
                amount_paid=s2_paid,
                created_by=receiver,
            )
            InvoiceItem.objects.create(
                invoice=inv2, fee_type=fee_types['SCOLARITE-S2'],
                description='Frais de scolarite Semestre 2',
                quantity=1, unit_price=300000, total=300000,
            )
            # Reset status avant recalc : calculate_totals() ne peut passer a OVERDUE
            # que si status != 'PAID', or le 1er create() l'a mis a PAID (balance=0 sans items)
            inv2.status = 'DRAFT'
            inv2.save()  # recalcule : PAID si fully_paid, OVERDUE sinon (echeance depassee)
            Invoice.objects.filter(pk=inv2.pk).update(issue_date=date(2025, 1, 20))

            p2_amount = 300000 if fully_paid else 225000
            p2 = Payment.objects.create(
                payment_number=f'PAY-2025-{i*10+1:03d}',
                invoice=inv2,
                payment_method=pay_methods['MOBILE'],
                amount=p2_amount, status='SUCCESS',
                reference=f'REF-MOB-{2025}{i+1:02d}01',
                received_by=receiver, validated_by=receiver,
                validated_at=_dt(date(2025, 2, 1)),
            )
            Payment.objects.filter(pk=p2.pk).update(payment_date=_dt(date(2025, 2, 1)))

        print(f'  Factures et paiements: {len(students)} etudiants')

    # =========================================================================
    # 6. NOTES
    # =========================================================================

    def _grades(self, students, cls, subjs, teachers, s1):
        from apps.grades.models import GradeCategory, Evaluation, Grade, ReportCard

        cc   = GradeCategory.objects.create(name='Controle Continu', code='CC',   weight=0.4)
        exam = GradeCategory.objects.create(name='Examen Final',     code='EXAM', weight=0.6)

        # Scores  [ibrahim_cc, ibrahim_exam, aicha_cc, aicha_exam]
        scores = {
            'ALG101': [14, 13, 17, 16],
            'PRG101': [15, 14, 18, 17],
            'MAT101': [12, 11, 15, 14],
            'RES101': [13, 14, 16, 15],
            'BDD101': [16, 15, 18, 17],
            'ANG101': [14, 13, 15, 14],
            'COM101': [15, 16, 17, 18],
        }

        for code, sc in scores.items():
            subj = subjs[code]

            ev_cc = Evaluation.objects.create(
                title=f'CC1 - {subj.name}',
                eval_type='DEVOIR', subject=subj, class_group=cls,
                semester=s1, date=date(2024, 11, 15),
                max_score=20, coefficient=1, is_locked=True,
                created_by=teachers[0].user,
            )
            ev_ex = Evaluation.objects.create(
                title=f'Examen S1 - {subj.name}',
                eval_type='EXAMEN', subject=subj, class_group=cls,
                semester=s1, date=date(2025, 1, 20),
                max_score=20, coefficient=2, is_locked=True,
                created_by=teachers[0].user,
            )

            for si, student in enumerate(students):
                Grade.objects.create(
                    student=student, subject=subj, class_group=cls,
                    semester=s1, evaluation=ev_cc, category=cc,
                    score=sc[si * 2], max_score=20,
                    date=date(2024, 11, 15),
                    comment='Bon travail' if sc[si * 2] >= 14 else 'Peut mieux faire',
                    entered_by=teachers[0].user,
                )
                Grade.objects.create(
                    student=student, subject=subj, class_group=cls,
                    semester=s1, evaluation=ev_ex, category=exam,
                    score=sc[si * 2 + 1], max_score=20,
                    date=date(2025, 1, 20),
                    comment='Resultats satisfaisants',
                    entered_by=teachers[0].user,
                )

        # --- Bulletins ---
        # Ibrahim : avg ~13.43/20  (cc*0.4 + exam*0.6 par matiere, puis moy ponderee)
        ReportCard.objects.create(
            student=students[0], class_group=cls, semester=s1,
            average='13.43', rank=2, total_students=2, status='PASS',
            subject_averages={
                'ALG101': {'cc': 14, 'exam': 13, 'coef': 4, 'avg': 13.4},
                'PRG101': {'cc': 15, 'exam': 14, 'coef': 3, 'avg': 14.4},
                'MAT101': {'cc': 12, 'exam': 11, 'coef': 3, 'avg': 11.4},
                'RES101': {'cc': 13, 'exam': 14, 'coef': 3, 'avg': 13.6},
                'BDD101': {'cc': 16, 'exam': 15, 'coef': 3, 'avg': 15.4},
                'ANG101': {'cc': 14, 'exam': 13, 'coef': 2, 'avg': 13.4},
                'COM101': {'cc': 15, 'exam': 16, 'coef': 2, 'avg': 15.6},
            },
            teacher_comment='Etudiant serieux et regulier. Bon travail en BDD et COM.',
            principal_comment='Resultats encourageants. Continue sur cette lancee.',
            is_published=True,
        )

        # Aicha : avg ~15.91/20
        ReportCard.objects.create(
            student=students[1], class_group=cls, semester=s1,
            average='15.91', rank=1, total_students=2, status='HONORS',
            subject_averages={
                'ALG101': {'cc': 17, 'exam': 16, 'coef': 4, 'avg': 16.4},
                'PRG101': {'cc': 18, 'exam': 17, 'coef': 3, 'avg': 17.4},
                'MAT101': {'cc': 15, 'exam': 14, 'coef': 3, 'avg': 14.4},
                'RES101': {'cc': 16, 'exam': 15, 'coef': 3, 'avg': 15.4},
                'BDD101': {'cc': 18, 'exam': 17, 'coef': 3, 'avg': 17.4},
                'ANG101': {'cc': 15, 'exam': 14, 'coef': 2, 'avg': 14.4},
                'COM101': {'cc': 17, 'exam': 18, 'coef': 2, 'avg': 17.6},
            },
            teacher_comment='Excellente etudiante, tres investie. Major de la promotion.',
            principal_comment='Felicitations. Mention Tres Bien meritee.',
            is_published=True,
        )

        total = Grade.objects.count()
        print(f'  Notes: {total} | Evaluations: {Evaluation.objects.count()} | Bulletins: 2')

    # =========================================================================
    # 7. PRESENCES
    # =========================================================================

    def _attendance(self, sessions, students):
        from apps.attendance.models import AttendanceSession, AttendanceRecord, AbsenceRequest

        # 10 seances sur les 2 dernieres semaines (mai 2025)
        seance_dates = [
            (sessions[0], date(2025, 5, 5)),   # ALG101 Lun
            (sessions[2], date(2025, 5, 6)),   # MAT101 Mar
            (sessions[4], date(2025, 5, 7)),   # BDD101 Mer  <- Ibrahim absent
            (sessions[6], date(2025, 5, 8)),   # ALG101 Jeu
            (sessions[8], date(2025, 5, 9)),   # PRG101 Ven
            (sessions[0], date(2025, 5, 12)),  # ALG101 Lun
            (sessions[2], date(2025, 5, 13)),  # MAT101 Mar  <- Ibrahim absent
            (sessions[4], date(2025, 5, 14)),  # BDD101 Mer
            (sessions[6], date(2025, 5, 15)),  # ALG101 Jeu
            (sessions[8], date(2025, 5, 16)),  # PRG101 Ven
        ]
        ibrahim_absent_idx = {2, 6}  # indices ou Ibrahim est absent

        for idx, (sess, d) in enumerate(seance_dates):
            att_sess = AttendanceSession.objects.create(
                session=sess, date=d, status='CLOSED',
                opened_by=sess.teacher.user,
            )
            for si, student in enumerate(students):
                is_absent = (si == 0 and idx in ibrahim_absent_idx)
                AttendanceRecord.objects.create(
                    attendance_session=att_sess,
                    student=student,
                    status='ABSENT' if is_absent else 'PRESENT',
                    check_in_method='MANUAL',
                    marked_by=sess.teacher.user,
                )

        # Demande d'absence justifiee pour Ibrahim (7 mai — certif medical)
        AbsenceRequest.objects.create(
            student=students[0],
            start_date=date(2025, 5, 7),
            end_date=date(2025, 5, 7),
            reason='Maladie — certificat medical joint',
            status='APPROVED',
            reviewed_by=students[0].user,  # auto-reference pour demo
            reviewed_at=_dt(date(2025, 5, 8)),
            review_notes='Absence justifiee — certificat medical recu le 08/05/2025',
        )

        total = AttendanceRecord.objects.count()
        print(f'  Presences: {total} enregistrements | 1 demande d\'absence approuvee')

    # =========================================================================
    # 8. COMPTABILITE
    # =========================================================================

    def _bank_and_expenses(self, site, pay_methods, admins):
        from apps.finance.models import BankAccount, Expense, CashRegister

        BankAccount.objects.create(
            name='Compte Courant Principal', bank_name='BICICI',
            account_number='CI93BI0080111301134500014944',
            iban='CI93BI0080111301134500014944', swift='BICICIAB',
            account_type='CHECKING', balance=12500000,
            currency='XOF', site=site,
        )
        BankAccount.objects.create(
            name='Compte Epargne Investissement', bank_name='Ecobank',
            account_number='CI45ECO9876543210',
            account_type='SAVINGS', balance=5000000,
            currency='XOF', site=site,
        )

        expenses = [
            ('Salaires enseignants - Avril 2025',    'SALARY',      2800000, date(2025, 4, 30)),
            ('Salaires personnel administratif',     'SALARY',      1200000, date(2025, 4, 30)),
            ('Facture electricite - Avril 2025',     'UTILITIES',    180000, date(2025, 4, 15)),
            ('Fournitures de bureau - Papeterie',    'SUPPLIES',      45000, date(2025, 4, 10)),
            ('Maintenance serveurs informatiques',   'MAINTENANCE',  320000, date(2025, 3, 20)),
            ('Abonnement Internet et telephonie',    'UTILITIES',     95000, date(2025, 4, 1)),
            ('Nettoyage et entretien des locaux',    'MAINTENANCE',   80000, date(2025, 4, 8)),
            ('Communication et publicite digitale',  'MARKETING',    150000, date(2025, 3, 15)),
            ('Transport et logistique - Mars',       'TRANSPORT',     60000, date(2025, 3, 25)),
        ]
        for label, cat, amt, d in expenses:
            Expense.objects.create(
                site=site, label=label, category=cat, amount=amt, date=d,
                payment_method=pay_methods['VIREMENT'],
                status='PAID', approved_by=admins[0],
            )

        CashRegister.objects.create(
            name='Caisse Principale Scolarite', code='CAISSE-01',
            site=site, current_balance=450000, is_open=True,
        )

        print(f'  Comptes bancaires: 2 | Depenses: {len(expenses)} | Caisse: 1')

    # =========================================================================
    # 9. RESUME
    # =========================================================================

    def _summary(self):
        from apps.accounts.models import User
        from apps.grades.models import Grade, Evaluation
        from apps.attendance.models import AttendanceRecord
        from apps.finance.models import Payment, Invoice

        sep = '=' * 72
        print('\n' + sep)
        print('SEED COMPLETE — RESUME DES COMPTES')
        print(sep)
        rows = [
            ('Role',          'Email',                     'Mot de passe', 'URL'),
            ('-' * 14,        '-' * 28,                    '-' * 14,       '-' * 10),
            ('Admin 1',       'yao.koffi@ita.ci',           ADMIN_PWD,     '/admin'),
            ('Admin 2',       'nguessan.adjoua@ita.ci',     ADMIN_PWD,     '/admin'),
            ('Staff 1',       'sery.fatou@ita.ci',          DEMO_PWD,      '/admin'),
            ('Staff 2',       'konate.ismael@ita.ci',       DEMO_PWD,      '/admin'),
            ('Enseignant 1',  'brou.marc@ita.ci',           DEMO_PWD,      '/teacher'),
            ('Enseignant 2',  'diabate.amara@ita.ci',       DEMO_PWD,      '/teacher'),
            ('Etudiant 1',    'kone.ibrahim@ita.ci',        DEMO_PWD,      '/student'),
            ('Etudiant 2',    'traore.aicha@ita.ci',        DEMO_PWD,      '/student'),
            ('Parent 1',      'kone.mamadou@ita.ci',        DEMO_PWD,      '/parent'),
            ('Parent 2',      'coulibaly.rokia@ita.ci',     DEMO_PWD,      '/parent'),
        ]
        for r in rows:
            print(f'  {r[0]:<15} {r[1]:<29} {r[2]:<15} {r[3]}')
        print(sep)

        print('\nSTATISTIQUES BD')
        print(f'  Utilisateurs  : {User.objects.count()}')
        print(f'  Notes         : {Grade.objects.count()}')
        print(f'  Evaluations   : {Evaluation.objects.count()}')
        print(f'  Presences     : {AttendanceRecord.objects.count()}')
        print(f'  Paiements     : {Payment.objects.count()}')
        print(f'  Factures      : {Invoice.objects.count()}')
        print(sep + '\n')
