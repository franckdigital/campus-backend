"""
seed_demo_complet.py — Peuple la base avec des étudiants d'école classique
(PRESENTIEL) ET d'e-learning (ELEARNING), avec parents, inscriptions et
factures impayées pour 5 comptes de test paiement Mobile Money.

100 % idempotent : get_or_create partout, ne supprime rien.
Fonctionne avec la structure réelle en production (n'exige pas seed_full).

Usage : python manage.py seed_demo_complet
"""
from datetime import date
from django.core.management.base import BaseCommand, CommandError

DEMO_PWD = 'Campus2024!'

# ── Étudiants école classique (PRESENTIEL) ────────────────────────────────
CLASSIQUE_STUDENTS = [
    ('cl1.etudiant@campus.ci', 'Kouassi',  'Amedée',   'M', date(2002,  3, 14), 'Abidjan',      'CL-2024-001', 'cl1.parent@campus.ci', 'René',      'Kouassi',  '+225 07 11 11 11 11'),
    ('cl2.etudiant@campus.ci', 'Adjoua',   'Bénédicte','F', date(2003,  7, 22), 'Yamoussoukro', 'CL-2024-002', 'cl2.parent@campus.ci', 'Cécile',    'Adjoua',   '+225 07 22 22 22 22'),
    ('cl3.etudiant@campus.ci', 'Traoré',   'Ismael',   'M', date(2002, 11,  5), 'Bouaké',       'CL-2024-003', 'cl3.parent@campus.ci', 'Fatoumata', 'Traoré',   '+225 07 33 33 33 33'),
    ('cl4.etudiant@campus.ci', 'Bamba',    'Karidia',  'F', date(2003,  1, 30), 'Abidjan',      'CL-2024-004', 'cl4.parent@campus.ci', 'Ibrahim',   'Bamba',    '+225 07 44 44 44 44'),
    ('cl5.etudiant@campus.ci', 'Coulibaly','Drissa',   'M', date(2002,  9, 18), 'Daloa',        'CL-2024-005', 'cl5.parent@campus.ci', 'Mariam',    'Coulibaly','+225 07 55 55 55 55'),
    ('cl6.etudiant@campus.ci', 'N\'Guessan','Ornella', 'F', date(2003,  4, 11), 'Abidjan',      'CL-2024-006', 'cl6.parent@campus.ci', 'Albert',    'N\'Guessan','+225 07 66 66 66 66'),
]

# ── Étudiants e-learning (ELEARNING) ─────────────────────────────────────
ELEARNING_STUDENTS = [
    ('el1.etudiant@campus.ci', 'Ouattara', 'Seydou',   'M', date(2001,  6, 25), 'Korhogo',   'EL-2024-001', 'el1.parent@campus.ci', 'Lacina',   'Ouattara','+225 05 11 11 11 11'),
    ('el2.etudiant@campus.ci', 'Sanogo',   'Aminata',  'F', date(2002,  2, 14), 'Abidjan',   'EL-2024-002', 'el2.parent@campus.ci', 'Noël',     'Sanogo',  '+225 05 22 22 22 22'),
    ('el3.etudiant@campus.ci', 'Koné',     'Lamine',   'M', date(2001, 10,  8), 'Bouaké',    'EL-2024-003', 'el3.parent@campus.ci', 'Salimata', 'Koné',    '+225 05 33 33 33 33'),
    ('el4.etudiant@campus.ci', 'Diallo',   'Kadiatou', 'F', date(2002,  8, 19), 'Abidjan',   'EL-2024-004', 'el4.parent@campus.ci', 'Mamadou',  'Diallo',  '+225 05 44 44 44 44'),
    ('el5.etudiant@campus.ci', 'Fofana',   'Adama',    'M', date(2001, 12,  3), 'San Pedro', 'EL-2024-005', 'el5.parent@campus.ci', 'Safiatou', 'Fofana',  '+225 05 55 55 55 55'),
]

# ── 5 comptes de test paiement Mobile Money (couvrent les deux modalités) ─
PAYMENT_TEST_STUDENTS = [
    ('pay1.test@campus.ci', 'Test',  'Paiement1', 'M', date(2003, 1, 1), 'Abidjan', 'PAY-TEST-001', 'pay1.parent@campus.ci', 'Parent', 'Test1', '+225 07 01 01 01 01', 'PRESENTIEL'),
    ('pay2.test@campus.ci', 'Test',  'Paiement2', 'F', date(2003, 1, 2), 'Abidjan', 'PAY-TEST-002', 'pay2.parent@campus.ci', 'Parent', 'Test2', '+225 07 02 02 02 02', 'ELEARNING'),
    ('pay3.test@campus.ci', 'Test',  'Paiement3', 'M', date(2003, 1, 3), 'Abidjan', 'PAY-TEST-003', 'pay3.parent@campus.ci', 'Parent', 'Test3', '+225 07 03 03 03 03', 'PRESENTIEL'),
    ('pay4.test@campus.ci', 'Test',  'Paiement4', 'F', date(2003, 1, 4), 'Abidjan', 'PAY-TEST-004', 'pay4.parent@campus.ci', 'Parent', 'Test4', '+225 07 04 04 04 04', 'ELEARNING'),
    ('pay5.test@campus.ci', 'Test',  'Paiement5', 'M', date(2003, 1, 5), 'Abidjan', 'PAY-TEST-005', 'pay5.parent@campus.ci', 'Parent', 'Test5', '+225 07 05 05 05 05', 'PRESENTIEL'),
]


class Command(BaseCommand):
    help = (
        'Crée des étudiants école classique (PRESENTIEL) + e-learning (ELEARNING) '
        'avec parents et factures impayées pour 5 comptes de test paiement Mobile Money. '
        '100 %% idempotent — ne supprime aucune donnée existante.'
    )

    def handle(self, *args, **options):
        from apps.core.models import Site, AcademicYear
        from apps.academic.models import Program, Level, Class

        # ── Site ──────────────────────────────────────────────────────────
        site = Site.objects.order_by('id').first()
        if not site:
            raise CommandError(
                "Aucun site trouvé. Créez au moins un site dans l'admin avant "
                "d'exécuter cette commande."
            )
        self.stdout.write(f'\n=== SITE : {site.name} ({site.code}) ===')

        # ── Année académique ──────────────────────────────────────────────
        ay = (
            AcademicYear.objects.filter(is_current=True).first()
            or AcademicYear.objects.order_by('-id').first()
        )
        if not ay:
            raise CommandError(
                "Aucune année académique trouvée. Créez-en une dans Paramètres → "
                "Années académiques."
            )
        self.stdout.write(f'Année académique : {ay.name}')

        # ── Programmes ───────────────────────────────────────────────────
        prog_cl, _ = Program.objects.get_or_create(
            code='PROG-CLASSIQUE',
            defaults=dict(name='École Classique', site=site, duration_years=3,
                          description='Formation en présentiel — École classique'),
        )
        prog_el, _ = Program.objects.get_or_create(
            code='PROG-ELEARNING',
            defaults=dict(name='E-Learning', site=site, duration_years=3,
                          description='Formation à distance — E-Learning'),
        )
        self.stdout.write(f'Programmes : {prog_cl.name}, {prog_el.name}')

        # ── Niveaux (L1 seul suffit pour les démos) ──────────────────────
        level_cl, _ = Level.objects.get_or_create(
            program=prog_cl, code='L1',
            defaults=dict(name='Licence 1', order=1),
        )
        level_el, _ = Level.objects.get_or_create(
            program=prog_el, code='L1',
            defaults=dict(name='Licence 1', order=1),
        )

        # ── Classes ───────────────────────────────────────────────────────
        cls_cl, _ = Class.objects.get_or_create(
            code='L1-CL-A', academic_year=ay, site=site,
            defaults=dict(name='Licence 1 — Classique A', level=level_cl, max_students=40),
        )
        cls_el, _ = Class.objects.get_or_create(
            code='L1-EL-A', academic_year=ay, site=site,
            defaults=dict(name='Licence 1 — E-Learning A', level=level_el, max_students=40),
        )
        self.stdout.write(f'Classes : {cls_cl.code}, {cls_el.code}')

        # ── Étudiants classique ───────────────────────────────────────────
        self.stdout.write('\n--- Étudiants école classique (PRESENTIEL) ---')
        cl_students = self._create_students(CLASSIQUE_STUDENTS, site, 'PRESENTIEL', cls_cl, ay)

        # ── Étudiants e-learning ──────────────────────────────────────────
        self.stdout.write('\n--- Étudiants e-learning (ELEARNING) ---')
        el_students = self._create_students(ELEARNING_STUDENTS, site, 'ELEARNING', cls_el, ay)

        # ── Comptes de test paiement Mobile Money ─────────────────────────
        self.stdout.write('\n--- Comptes de test paiement Mobile Money ---')
        pay_students = self._create_payment_test_students(
            PAYMENT_TEST_STUDENTS, site, cls_cl, cls_el, ay
        )
        self._create_invoices(pay_students, site, ay)

        # ── Résumé final ─────────────────────────────────────────────────
        self._print_summary(cl_students, el_students, pay_students)

    # =====================================================================
    # CRÉATION ÉTUDIANTS
    # =====================================================================

    def _create_students(self, data, site, modality, cls_obj, ay):
        from apps.accounts.models import User
        from apps.students.models import Student, Parent, StudentParent
        from apps.academic.models import Enrollment

        students = []
        for (email, last, first, gender, birth_date, birth_place,
             matricule, p_email, p_first, p_last, p_tel) in data:

            su, created = User.objects.get_or_create(
                email=email,
                defaults=dict(
                    first_name=first, last_name=last,
                    user_type='STUDENT', is_active=True, site=site,
                ),
            )
            if created:
                su.set_password(DEMO_PWD)
                su.save()

            student, _ = Student.objects.get_or_create(
                user=su,
                defaults=dict(
                    matricule=matricule, gender=gender,
                    birth_date=birth_date, birth_place=birth_place,
                    nationality='Ivoirienne', address='Abidjan', city='Abidjan',
                    site=site, status='ACTIVE', modality=modality,
                    admission_date=date(2024, 9, 2),
                    emergency_contact_name=f'{p_first} {p_last}',
                    emergency_contact_phone=p_tel,
                    emergency_contact_relation='PARENT',
                    registration_fee=75000, registration_fee_paid=False,
                    tuition_fee=500000, total_paid=0, remaining_balance=500000,
                ),
            )
            students.append(student)
            self.stdout.write(f'  {"+" if created else "·"} {email}')

            pu, pu_created = User.objects.get_or_create(
                email=p_email,
                defaults=dict(
                    first_name=p_first, last_name=p_last,
                    user_type='PARENT', is_active=True, site=site,
                ),
            )
            if pu_created:
                pu.set_password(DEMO_PWD)
                pu.save()

            parent, _ = Parent.objects.get_or_create(
                user=pu,
                defaults=dict(
                    profession='Salarié', employer='Secteur privé',
                    address='Abidjan', city='Abidjan',
                    emergency_contact=p_tel, relationship='PARENT',
                ),
            )
            StudentParent.objects.get_or_create(
                student=student, parent=parent,
                defaults=dict(is_primary=True, can_pickup=True, receives_notifications=True),
            )
            Enrollment.objects.get_or_create(
                student=student, class_obj=cls_obj, academic_year=ay,
                defaults=dict(status='ENROLLED'),
            )

        return students

    # =====================================================================
    # COMPTES TEST PAIEMENT
    # =====================================================================

    def _create_payment_test_students(self, data, site, cls_cl, cls_el, ay):
        from apps.accounts.models import User
        from apps.students.models import Student, Parent, StudentParent
        from apps.academic.models import Enrollment

        students = []
        for (email, last, first, gender, birth_date, birth_place,
             matricule, p_email, p_first, p_last, p_tel, modality) in data:

            su, created = User.objects.get_or_create(
                email=email,
                defaults=dict(
                    first_name=first, last_name=last,
                    user_type='STUDENT', is_active=True, site=site,
                ),
            )
            if created:
                su.set_password(DEMO_PWD)
                su.save()

            cls = cls_el if modality == 'ELEARNING' else cls_cl

            student, _ = Student.objects.get_or_create(
                user=su,
                defaults=dict(
                    matricule=matricule, gender=gender,
                    birth_date=birth_date, birth_place=birth_place,
                    nationality='Ivoirienne', address='Abidjan', city='Abidjan',
                    site=site, status='ACTIVE', modality=modality,
                    admission_date=date(2024, 9, 2),
                    emergency_contact_name=f'{p_first} {p_last}',
                    emergency_contact_phone=p_tel,
                    emergency_contact_relation='PARENT',
                    registration_fee=75000, registration_fee_paid=False,
                    tuition_fee=350000, total_paid=0, remaining_balance=350000,
                ),
            )
            students.append((student, modality))
            self.stdout.write(f'  {"+" if created else "·"} {email} [{modality}]')

            pu, pu_created = User.objects.get_or_create(
                email=p_email,
                defaults=dict(
                    first_name=p_first, last_name=p_last,
                    user_type='PARENT', is_active=True, site=site,
                ),
            )
            if pu_created:
                pu.set_password(DEMO_PWD)
                pu.save()

            parent, _ = Parent.objects.get_or_create(
                user=pu,
                defaults=dict(
                    profession='Test', employer='Test',
                    address='Abidjan', city='Abidjan',
                    emergency_contact=p_tel, relationship='PARENT',
                ),
            )
            StudentParent.objects.get_or_create(
                student=student, parent=parent,
                defaults=dict(is_primary=True, can_pickup=True, receives_notifications=True),
            )
            Enrollment.objects.get_or_create(
                student=student, class_obj=cls, academic_year=ay,
                defaults=dict(status='ENROLLED'),
            )

        return students

    # =====================================================================
    # FACTURES IMPAYÉES POUR TEST
    # =====================================================================

    def _create_invoices(self, pay_students, site, ay):
        from apps.finance.models import Invoice, InvoiceItem, FeeType

        fee_scol, _ = FeeType.objects.get_or_create(
            code='SCOLARITE',
            defaults=dict(name='Frais de scolarité', default_amount=350000, is_recurring=True),
        )
        fee_inscr, _ = FeeType.objects.get_or_create(
            code='INSCRIPTION',
            defaults=dict(name="Frais d'inscription", default_amount=75000, is_recurring=False),
        )

        created = 0
        for student, modality in pay_students:
            if Invoice.objects.filter(student=student, amount_paid=0).exists():
                continue
            inv = Invoice.objects.create(
                student=student, site=site, academic_year=ay,
                due_date=date(2025, 9, 30), amount_paid=0,
                notes=f'Facture test paiement Mobile Money — {modality}',
            )
            InvoiceItem.objects.create(
                invoice=inv, fee_type=fee_inscr,
                description="Frais d'inscription 2024-2025",
                quantity=1, unit_price=75000, total=75000,
            )
            InvoiceItem.objects.create(
                invoice=inv, fee_type=fee_scol,
                description='Frais de scolarité 2024-2025',
                quantity=1, unit_price=350000, total=350000,
            )
            inv.save()
            created += 1

        self.stdout.write(f'  Factures impayées créées : {created}')

    # =====================================================================
    # RÉSUMÉ
    # =====================================================================

    def _print_summary(self, cl_students, el_students, pay_students):
        sep = '=' * 70
        self.stdout.write('\n' + sep)
        self.stdout.write('SEED DÉMO COMPLET TERMINÉ')
        self.stdout.write(sep)
        self.stdout.write(f'  Étudiants école classique (PRESENTIEL) : {len(cl_students)}')
        self.stdout.write(f'  Étudiants e-learning (ELEARNING)       : {len(el_students)}')
        self.stdout.write(f'  Comptes de test paiement               : {len(pay_students)}')
        self.stdout.write(sep)
        self.stdout.write('')
        self.stdout.write('IDENTIFIANTS COMPTES DE TEST (mot de passe identique pour tous)')
        self.stdout.write(f'  Mot de passe : {DEMO_PWD}')
        self.stdout.write('')
        self.stdout.write('  ┌─────────────────────────────┬─────────────┬────────────┬───────────────┐')
        self.stdout.write('  │ Email étudiant              │ Matricule   │ Modalité   │ Email parent  │')
        self.stdout.write('  ├─────────────────────────────┼─────────────┼────────────┼───────────────┤')
        for (email, last, first, gender, birth_date, birth_place,
             matricule, p_email, p_first, p_last, p_tel, modality) in PAYMENT_TEST_STUDENTS:
            self.stdout.write(
                f'  │ {email:<27} │ {matricule:<11} │ {modality:<10} │ {p_email:<13} │'
            )
        self.stdout.write('  └─────────────────────────────┴─────────────┴────────────┴───────────────┘')
        self.stdout.write('')
        self.stdout.write('  → Application mobile : pay1.test@campus.ci  /  Campus2024!')
        self.stdout.write('  → Tous les comptes parents : pay{N}.parent@campus.ci  /  Campus2024!')
        self.stdout.write(sep + '\n')
