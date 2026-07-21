"""
seed_elearning_students.py — Cree 5 etudiants de test (+ parents lies, notifications
push activees) inscrits dans une classe existante, avec une facture impayee chacun,
pour tester de bout en bout le systeme ELearning + paiement CinetPay + notifications
push, sans avoir a relancer tout `seed_full`.

Usage: python manage.py seed_elearning_students
Pre-requis : avoir deja execute `python manage.py seed_full`.
Idempotent : peut etre relance sans dupliquer les comptes (get_or_create par email).

Ordre recommande pour un environnement de test complet :
  1. python manage.py seed_full                 -> sites, classes, matieres...
  2. python manage.py seed_elearning_students    -> ce script (5 eleves + parents)
  3. python manage.py seed_elearning             -> lecons/quiz/devoirs, y compris
     la progression de ces 5 nouveaux eleves car ils sont deja inscrits dans une
     classe existante au moment ou seed_elearning s'execute.
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError

STUDENT_PWD = 'Eleve2024!'

# (email, prenom, nom, genre, naissance, lieu_naissance, matricule,
#  email_parent, prenom_parent, nom_parent, telephone_parent)
TEST_STUDENTS = [
    ('test1.eleve@campus.ci', 'Awa', 'Diabate', 'F', date(2003, 2, 10), 'Abidjan',
     'TEST-2024-001', 'test1.parent@campus.ci', 'Mamadou', 'Diabate', '+225 07 01 01 01 01'),
    ('test2.eleve@campus.ci', 'Yacouba', 'Sangare', 'M', date(2003, 5, 18), 'Bouake',
     'TEST-2024-002', 'test2.parent@campus.ci', 'Fatou', 'Sangare', '+225 07 02 02 02 02'),
    ('test3.eleve@campus.ci', 'Nadege', 'Kacou', 'F', date(2002, 11, 4), 'Abidjan',
     'TEST-2024-003', 'test3.parent@campus.ci', 'Bernard', 'Kacou', '+225 07 03 03 03 03'),
    ('test4.eleve@campus.ci', 'Idriss', 'Fofana', 'M', date(2003, 8, 27), 'Daloa',
     'TEST-2024-004', 'test4.parent@campus.ci', 'Salimata', 'Fofana', '+225 07 04 04 04 04'),
    ('test5.eleve@campus.ci', 'Carole', 'Brou', 'F', date(2002, 6, 14), 'Abidjan',
     'TEST-2024-005', 'test5.parent@campus.ci', 'Jean', 'Brou', '+225 07 05 05 05 05'),
]


class Command(BaseCommand):
    help = (
        'Cree 5 etudiants de test (+ parents lies, notifications activees) inscrits '
        'dans une classe existante, avec une facture impayee chacun, pour tester '
        'le systeme ELearning + paiement CinetPay + notifications push de bout en bout.'
    )

    def handle(self, *args, **options):
        from apps.academic.models import Class as ClassModel
        from apps.core.models import AcademicYear

        cls = ClassModel.objects.select_related('site').order_by('id').first()
        if not cls:
            raise CommandError(
                "Aucune classe trouvee. Executez d'abord `python manage.py seed_full`."
            )
        ay = AcademicYear.objects.filter(is_current=True).first() \
            or AcademicYear.objects.order_by('-id').first()
        if not ay:
            raise CommandError("Aucune annee academique trouvee.")

        self.stdout.write(f'\n=== ETUDIANTS DE TEST ELEARNING ({cls.code} — {cls.site.name}) ===')

        students = self._create_students_parents(cls.site)
        self._enroll(students, cls, ay)
        self._create_invoices(students, cls.site, ay)

        self.stdout.write(self.style.SUCCESS(
            f'\n5 etudiants de test prets dans la classe {cls.code} ({cls.site.name}).'
        ))
        self.stdout.write('\nIdentifiants (mot de passe identique pour tous) :')
        for row in TEST_STUDENTS:
            self.stdout.write(f'  [ELEVE]   {row[0]} / {STUDENT_PWD}')
        for row in TEST_STUDENTS:
            self.stdout.write(f'  [PARENT]  {row[7]} / {STUDENT_PWD}')
        self.stdout.write(
            '\nProchaine etape : `python manage.py seed_elearning` pour generer '
            'les lecons/quiz/devoirs (y compris la progression de ces 5 eleves).'
        )

    def _create_students_parents(self, site):
        from apps.accounts.models import User
        from apps.students.models import Student, Parent, StudentParent

        students = []
        for (s_email, fn, ln, gender, birth_date, birth_place, matricule,
             p_email, p_fn, p_ln, p_tel) in TEST_STUDENTS:

            su, su_created = User.objects.get_or_create(
                email=s_email,
                defaults=dict(
                    first_name=fn, last_name=ln, user_type='STUDENT',
                    is_active=True, site=site,
                ),
            )
            if su_created:
                su.set_password(STUDENT_PWD)
                su.save()

            student, _ = Student.objects.get_or_create(
                user=su,
                defaults=dict(
                    matricule=matricule, gender=gender,
                    birth_date=birth_date, birth_place=birth_place,
                    nationality='Ivoirienne',
                    address='Abidjan', city='Abidjan',
                    site=site, status='ACTIVE',
                    admission_date=date(2024, 9, 2),
                    emergency_contact_name=f'{p_fn} {p_ln}',
                    emergency_contact_phone=p_tel,
                    emergency_contact_relation='PARENT',
                    registration_fee=75000, is_enrolled=False,
                    tuition_fee=600000, total_paid=0,
                    remaining_balance=600000,
                ),
            )
            students.append(student)
            self.stdout.write(f'  [ELEVE]   {s_email}')

            pu, pu_created = User.objects.get_or_create(
                email=p_email,
                defaults=dict(
                    first_name=p_fn, last_name=p_ln, user_type='PARENT',
                    is_active=True, site=site,
                ),
            )
            if pu_created:
                pu.set_password(STUDENT_PWD)
                pu.save()

            parent, _ = Parent.objects.get_or_create(
                user=pu,
                defaults=dict(
                    profession='Test', employer='Test',
                    address='Abidjan', city='Abidjan',
                    relationship='PARENT', emergency_contact=p_tel,
                ),
            )
            StudentParent.objects.get_or_create(
                student=student, parent=parent,
                defaults=dict(is_primary=True, can_pickup=True, receives_notifications=True),
            )
            self.stdout.write(f'  [PARENT]  {p_email}')

        return students

    def _enroll(self, students, cls, ay):
        from apps.academic.models import Enrollment

        for student in students:
            Enrollment.objects.get_or_create(
                student=student, class_obj=cls, academic_year=ay,
                defaults=dict(status='ENROLLED'),
            )
        self.stdout.write(f'  Inscriptions: {len(students)} -> {cls.code}')

    def _create_invoices(self, students, site, ay):
        from apps.finance.models import Invoice, InvoiceItem, FeeType

        fee_inscription = FeeType.objects.filter(code='INSCRIPTION').first()
        fee_scolarite = FeeType.objects.filter(code='SCOLARITE-S1').first()
        if not fee_inscription or not fee_scolarite:
            self.stdout.write(self.style.WARNING(
                '  [WARN] Types de frais introuvables — factures de test non creees '
                '(executez `seed_full` au prealable).'
            ))
            return

        created_count = 0
        for student in students:
            if Invoice.objects.filter(student=student, amount_paid=0).exists():
                continue
            inv = Invoice.objects.create(
                student=student, site=site, academic_year=ay,
                due_date=date(2025, 9, 30), amount_paid=0,
            )
            InvoiceItem.objects.create(
                invoice=inv, fee_type=fee_inscription,
                description="Frais d'inscription — test paiement CinetPay",
                quantity=1, unit_price=75000, total=75000,
            )
            InvoiceItem.objects.create(
                invoice=inv, fee_type=fee_scolarite,
                description='Frais de scolarite — test paiement CinetPay',
                quantity=1, unit_price=300000, total=300000,
            )
            inv.save()
            created_count += 1
        self.stdout.write(f'  Factures impayees creees: {created_count} (test CinetPay)')
