from django.core.management.base import BaseCommand
from apps.students.models import Student
from apps.academic.models import Enrollment, Class
from apps.finance.models import Invoice
from apps.core.models import AcademicYear


class Command(BaseCommand):
    help = 'Sync enrollments for all students who have invoices but no enrollments'

    def handle(self, *args, **options):
        # Get current academic year
        current_year = AcademicYear.get_current()
        if not current_year:
            self.stdout.write(self.style.ERROR('No current academic year found'))
            return

        self.stdout.write(f'Using academic year: {current_year.name}')

        # Get all students
        students = Student.objects.filter(is_active=True)
        created_count = 0
        skipped_count = 0

        for student in students:
            # Check if student already has enrollment for current year
            has_enrollment = Enrollment.objects.filter(
                student=student,
                academic_year=current_year
            ).exists()

            if has_enrollment:
                skipped_count += 1
                continue

            # Find a class for this student
            # Option 1: Use latest enrollment's class
            latest_enrollment = student.enrollments.select_related('class_obj').order_by('-created_at').first()
            
            if latest_enrollment:
                class_obj = latest_enrollment.class_obj
            else:
                # Option 2: Get any active class from student's site
                class_obj = Class.objects.filter(
                    site=student.site,
                    academic_year=current_year,
                    is_active=True
                ).first()

            if class_obj:
                Enrollment.objects.create(
                    student=student,
                    class_obj=class_obj,
                    academic_year=current_year,
                    status='ENROLLED',
                    is_active=True
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created enrollment for {student.matricule} in {class_obj.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'No class found for {student.matricule} (site: {student.site})')
                )

        self.stdout.write(self.style.SUCCESS(f'\nDone! Created: {created_count}, Skipped: {skipped_count}'))
