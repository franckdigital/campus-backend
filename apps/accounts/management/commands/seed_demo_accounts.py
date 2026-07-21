"""
Management command to create/reset demo accounts for each portal interface.
Usage: python manage.py seed_demo_accounts
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date


DEMO_PASSWORD = 'Campus2024!'
ADMIN_PASSWORD = 'Admin2024!'


class Command(BaseCommand):
    help = 'Create or reset demo accounts for each portal interface'

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.core.models import Site

        site = Site.objects.first()
        if not site:
            self.stderr.write('No site found. Create a site first.')
            return

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Seeding demo accounts ===\n'))

        self._make_admin(site)
        self._make_staff(site)
        self._make_teacher(site)
        self._make_student(site)
        self._make_parent(site)
        self._print_summary()

    # ── Admin ──────────────────────────────────────────────────────────────────

    def _make_admin(self, site):
        from apps.accounts.models import User
        email = 'admin@ita.ci'
        user, created = User.objects.update_or_create(
            email=email,
            defaults=dict(
                first_name='Administrateur',
                last_name='Principal',
                user_type='ADMIN',
                is_staff=True,
                is_superuser=True,
                is_active=True,
                site=site,
            )
        )
        user.set_password(ADMIN_PASSWORD)
        user.save()
        lbl = 'Créé' if created else 'Mis à jour'
        self.stdout.write(self.style.SUCCESS(f'[ADMIN]   {lbl}: {email}'))

        # Also reset existing admin@campus.com
        try:
            existing = User.objects.get(email='admin@campus.com')
            existing.set_password(ADMIN_PASSWORD)
            existing.save()
            self.stdout.write(self.style.SUCCESS(f'[ADMIN]   Réinitialisé: admin@campus.com'))
        except User.DoesNotExist:
            pass

    # ── Staff ──────────────────────────────────────────────────────────────────

    def _make_staff(self, site):
        from apps.accounts.models import User
        email = 'staff@ita.ci'
        user, created = User.objects.update_or_create(
            email=email,
            defaults=dict(
                first_name='Agent',
                last_name='Administratif',
                user_type='STAFF',
                is_staff=False,
                is_active=True,
                site=site,
            )
        )
        user.set_password(DEMO_PASSWORD)
        user.save()
        lbl = 'Créé' if created else 'Mis à jour'
        self.stdout.write(self.style.SUCCESS(f'[STAFF]   {lbl}: {email}'))

    # ── Teacher ────────────────────────────────────────────────────────────────

    def _make_teacher(self, site):
        from apps.accounts.models import User
        from apps.academic.models import TeacherProfile

        email = 'prof@ita.ci'
        user, created = User.objects.update_or_create(
            email=email,
            defaults=dict(
                first_name='Professeur',
                last_name='Démo',
                user_type='TEACHER',
                is_active=True,
                site=site,
            )
        )
        user.set_password(DEMO_PASSWORD)
        user.save()
        lbl = 'Créé' if created else 'Mis à jour'
        self.stdout.write(self.style.SUCCESS(f'[TEACHER] {lbl}: {email}'))

        TeacherProfile.objects.update_or_create(
            user=user,
            defaults=dict(
                employee_id='DEMO-PROF-01',
                specialization='Informatique',
                qualification='Master en Informatique',
                hire_date=date(2023, 9, 1),
                contract_type='PERMANENT',
            )
        )

        # Reset existing teacher accounts too
        for teacher_email in ['m.brou@campus.ci', 'a.diabate@campus.ci',
                               't.kouame@campus.ci', 'k.mensah@campus.ci']:
            try:
                t = User.objects.get(email=teacher_email)
                t.set_password(DEMO_PASSWORD)
                t.save()
                self.stdout.write(self.style.SUCCESS(f'[TEACHER] Réinitialisé: {teacher_email}'))
            except User.DoesNotExist:
                pass

    # ── Student ────────────────────────────────────────────────────────────────

    def _make_student(self, site):
        from apps.accounts.models import User
        from apps.students.models import Student

        email = 'etudiant@ita.ci'
        user, created = User.objects.update_or_create(
            email=email,
            defaults=dict(
                first_name='Étudiant',
                last_name='Démo',
                user_type='STUDENT',
                is_active=True,
                site=site,
            )
        )
        user.set_password(DEMO_PASSWORD)
        user.save()
        lbl = 'Créé' if created else 'Mis à jour'
        self.stdout.write(self.style.SUCCESS(f'[STUDENT] {lbl}: {email}'))

        Student.objects.update_or_create(
            user=user,
            defaults=dict(
                matricule='DEMO-STU-2024',
                gender='M',
                birth_date=date(2000, 1, 15),
                birth_place='Abidjan',
                nationality='Ivoirienne',
                site=site,
                status='ACTIVE',
                admission_date=date(2024, 9, 1),
                registration_fee=50000,
                is_enrolled=True,
                tuition_fee=500000,
                total_paid=250000,
                remaining_balance=250000,
            )
        )

        # Reset existing student accounts
        for student_email in ['angealain@gmail.com', 'ange@gmail.com',
                               'franck@gmail.com', 'alain@gmail.com']:
            try:
                s = User.objects.get(email=student_email)
                s.set_password(DEMO_PASSWORD)
                s.save()
                self.stdout.write(self.style.SUCCESS(f'[STUDENT] Réinitialisé: {student_email}'))
            except User.DoesNotExist:
                pass

    # ── Parent ─────────────────────────────────────────────────────────────────

    def _make_parent(self, site):
        from apps.accounts.models import User
        from apps.students.models import Parent, Student, StudentParent

        email = 'parent@ita.ci'
        user, created = User.objects.update_or_create(
            email=email,
            defaults=dict(
                first_name='Parent',
                last_name='Démo',
                user_type='PARENT',
                is_active=True,
                site=site,
            )
        )
        user.set_password(DEMO_PASSWORD)
        user.save()
        lbl = 'Créé' if created else 'Mis à jour'
        self.stdout.write(self.style.SUCCESS(f'[PARENT]  {lbl}: {email}'))

        parent_profile, _ = Parent.objects.update_or_create(
            user=user,
            defaults=dict(
                profession='Ingénieur',
                address='Abidjan, Cocody',
                city='Abidjan',
                relationship='FATHER',
            )
        )

        # Link parent to demo student
        try:
            demo_student = Student.objects.get(matricule='DEMO-STU-2024')
            StudentParent.objects.get_or_create(
                student=demo_student,
                parent=parent_profile,
                defaults=dict(is_primary=True)
            )
            self.stdout.write(self.style.SUCCESS(f'[PARENT]  Lié à l\'étudiant: DEMO-STU-2024'))
        except Student.DoesNotExist:
            pass

        # Reset existing parent account
        try:
            p = User.objects.get(email='jeandupont@campus.com')
            p.set_password(DEMO_PASSWORD)
            p.save()
            self.stdout.write(self.style.SUCCESS(f'[PARENT]  Réinitialisé: jeandupont@campus.com'))
        except User.DoesNotExist:
            pass

    # ── Summary ────────────────────────────────────────────────────────────────

    def _print_summary(self):
        sep = '=' * 72
        print('\n' + sep)
        print('COMPTES DEMO -- RESUME')
        print(sep)
        rows = [
            ('Interface',     'Email',                 'Mot de passe',  'URL'),
            ('-'*15,          '-'*25,                  '-'*14,          '-'*18),
            ('Admin',         'admin@ita.ci',           ADMIN_PASSWORD,  '/admin'),
            ('Admin (exist)', 'admin@campus.com',       ADMIN_PASSWORD,  '/admin'),
            ('Staff',         'staff@ita.ci',           DEMO_PASSWORD,   '/admin'),
            ('Enseignant',    'prof@ita.ci',            DEMO_PASSWORD,   '/teacher'),
            ('Enseignant',    'm.brou@campus.ci',       DEMO_PASSWORD,   '/teacher'),
            ('Etudiant',      'etudiant@ita.ci',        DEMO_PASSWORD,   '/student'),
            ('Etudiant',      'ange@gmail.com',         DEMO_PASSWORD,   '/student'),
            ('Parent',        'parent@ita.ci',          DEMO_PASSWORD,   '/parent'),
            ('Parent',        'jeandupont@campus.com',  DEMO_PASSWORD,   '/parent'),
        ]
        for row in rows:
            print(f'  {row[0]:<16} {row[1]:<26} {row[2]:<15} {row[3]}')
        print(sep + '\n')
