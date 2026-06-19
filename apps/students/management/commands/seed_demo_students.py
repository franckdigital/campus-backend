"""
Management command to seed demo student and parent data.

Usage:
    python manage.py seed_demo_students
"""
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Seed demo data for angealain@gmail.com (student) and jeandupont@campus.com (parent)'

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.students.models import Student, Parent, StudentParent
        from apps.core.models import Site, AcademicYear
        from apps.academic.models import Class, Enrollment, Program, Level

        self.stdout.write(self.style.MIGRATE_HEADING('Seeding demo student/parent data...'))

        with transaction.atomic():
            # ── 1. Get or create a site ──────────────────────────────────────
            site = Site.objects.filter(is_active=True).first()
            if not site:
                site = Site.objects.create(
                    name='ITA Marcory',
                    code='ITAMARCORY',
                    city='Abidjan',
                    is_main=True,
                )
                self.stdout.write(f'  Created site: {site.name}')
            else:
                self.stdout.write(f'  Using site: {site.name}')

            # ── 2. Get or create academic year ───────────────────────────────
            academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not academic_year:
                academic_year = AcademicYear.objects.create(
                    name='2025-2026',
                    code='2025-2026',
                    start_date=datetime.date(2025, 9, 1),
                    end_date=datetime.date(2026, 7, 31),
                    is_current=True,
                )
                self.stdout.write(f'  Created academic year: {academic_year.name}')
            else:
                self.stdout.write(f'  Using academic year: {academic_year.name}')

            # ── 3. Get or create a class ─────────────────────────────────────
            class_obj = Class.objects.filter(site=site, is_active=True).first()
            if not class_obj:
                # Need a Program and Level first
                program, _ = Program.objects.get_or_create(
                    code='INFO',
                    defaults={
                        'name': 'Informatique',
                        'site': site,
                        'duration_years': 3,
                    }
                )
                level, _ = Level.objects.get_or_create(
                    program=program,
                    code='L1',
                    defaults={
                        'name': 'Licence 1',
                        'order': 1,
                    }
                )
                class_obj = Class.objects.create(
                    name='L1 Informatique 2025-2026',
                    code='L1-INFO-2526',
                    level=level,
                    site=site,
                    academic_year=academic_year,
                    max_students=40,
                )
                self.stdout.write(f'  Created class: {class_obj.name}')
            else:
                self.stdout.write(f'  Using class: {class_obj.name}')

            # ── 4. Update student user ───────────────────────────────────────
            try:
                student_user = User.objects.get(email='angealain@gmail.com')
            except User.DoesNotExist:
                student_user = User.objects.create(email='angealain@gmail.com', user_type='STUDENT')
                student_user.set_password('campus123')
                self.stdout.write('  Created user angealain@gmail.com')

            student_user.first_name = 'Ange'
            student_user.last_name = 'Alain'
            student_user.phone = '+225 07 00 00 01'
            student_user.user_type = 'STUDENT'
            student_user.site = site
            student_user.is_active = True
            student_user.set_password('campus123')
            student_user.save()
            self.stdout.write(f'  Updated user: {student_user.full_name} ({student_user.email})')

            # ── 5. Get or create student profile ────────────────────────────
            student, created = Student.objects.get_or_create(
                user=student_user,
                defaults={
                    'site': site,
                    'gender': 'M',
                    'birth_date': datetime.date(2003, 5, 15),
                    'birth_place': 'Abidjan',
                    'nationality': 'Ivoirienne',
                    'address': 'Marcory Zone 4, Abidjan',
                    'city': 'Abidjan',
                    'status': 'ACTIVE',
                    'admission_date': datetime.date(2025, 9, 1),
                    'registration_fee': 150000,
                    'registration_fee_paid': True,
                    'tuition_fee': 2000000,
                    'total_paid': 1550000,
                    'remaining_balance': 450000,
                }
            )

            if not created:
                # Update existing profile
                student.site = site
                student.gender = student.gender or 'M'
                student.birth_date = student.birth_date or datetime.date(2003, 5, 15)
                student.birth_place = student.birth_place or 'Abidjan'
                student.nationality = student.nationality or 'Ivoirienne'
                student.address = student.address or 'Marcory Zone 4, Abidjan'
                student.city = student.city or 'Abidjan'
                student.status = 'ACTIVE'
                student.admission_date = student.admission_date or datetime.date(2025, 9, 1)
                student.registration_fee = student.registration_fee or 150000
                student.registration_fee_paid = True
                student.tuition_fee = student.tuition_fee or 2000000
                student.total_paid = student.total_paid or 1550000
                student.remaining_balance = student.remaining_balance or 450000
                student.save()
                self.stdout.write(f'  Updated student profile: #{student.matricule}')
            else:
                self.stdout.write(f'  Created student profile: #{student.matricule}')

            # ── 6. Create enrollment ─────────────────────────────────────────
            enrollment, created_enrollment = Enrollment.objects.get_or_create(
                student=student,
                academic_year=academic_year,
                defaults={
                    'class_obj': class_obj,
                    'status': 'ACTIVE',
                    'is_active': True,
                }
            )
            if created_enrollment:
                self.stdout.write(f'  Created enrollment: {class_obj.name}')
            else:
                if enrollment.status != 'ACTIVE':
                    enrollment.status = 'ACTIVE'
                    enrollment.class_obj = class_obj
                    enrollment.save()
                self.stdout.write(f'  Enrollment already exists: {enrollment.class_obj.name}')

            # ── 7. Create/update parent user ────────────────────────────────
            try:
                parent_user = User.objects.get(email='jeandupont@campus.com')
            except User.DoesNotExist:
                parent_user = User.objects.create(email='jeandupont@campus.com', user_type='PARENT')
                parent_user.set_password('campus123')
                self.stdout.write('  Created user jeandupont@campus.com')

            parent_user.first_name = 'Jean'
            parent_user.last_name = 'Dupont'
            parent_user.phone = '+225 07 00 00 02'
            parent_user.user_type = 'PARENT'
            parent_user.site = site
            parent_user.is_active = True
            parent_user.set_password('campus123')
            parent_user.save()
            self.stdout.write(f'  Updated user: {parent_user.full_name} ({parent_user.email})')

            # ── 8. Get or create parent profile ─────────────────────────────
            parent, _ = Parent.objects.get_or_create(
                user=parent_user,
                defaults={
                    'relationship': 'FATHER',
                    'profession': 'Ingénieur',
                    'employer': 'ITA Group',
                    'address': 'Cocody, Abidjan',
                    'city': 'Abidjan',
                    'emergency_contact': '+225 07 00 00 02',
                }
            )
            self.stdout.write(f'  Parent profile: {parent_user.full_name}')

            # ── 9. Link parent to student ────────────────────────────────────
            link, created_link = StudentParent.objects.get_or_create(
                student=student,
                parent=parent,
                defaults={
                    'is_primary': True,
                    'can_pickup': True,
                    'receives_notifications': True,
                }
            )
            if created_link:
                self.stdout.write(f'  Linked {parent_user.full_name} -> {student_user.full_name}')
            else:
                self.stdout.write(f'  Link already exists: {parent_user.full_name} -> {student_user.full_name}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('OK Demo data seeded successfully!'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Credentials:'))
        self.stdout.write(f'  Student:  angealain@gmail.com   / campus123')
        self.stdout.write(f'  Parent:   jeandupont@campus.com / campus123')
        self.stdout.write('')
