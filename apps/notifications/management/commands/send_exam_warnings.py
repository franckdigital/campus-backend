"""
python manage.py send_exam_warnings [--days-ahead N] [--absence-threshold N]

For every EXAMEN/RATTRAPAGE evaluation in the next N days, checks each enrolled
student. If their absence count ≥ threshold OR they have unpaid invoices,
sends a push + in-app warning to BOTH parent and student.
Cron: daily, e.g. 0 7 * * * python manage.py send_exam_warnings
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Warn parents and students about exam admission issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead', type=int, default=7,
            help='Look for exams within N days (default: 7)'
        )
        parser.add_argument(
            '--absence-threshold', type=int, default=3,
            help='Absence count that blocks admission (default: 3)'
        )

    def handle(self, *args, **options):
        from apps.grades.models import Evaluation
        from apps.academic.models import Enrollment
        from apps.finance.models import Invoice
        from apps.students.models import StudentParent
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_notification

        today    = timezone.localdate()
        horizon  = today + timezone.timedelta(days=options['days_ahead'])
        threshold = options['absence_threshold']

        exams = Evaluation.objects.filter(
            eval_type__in=['EXAMEN', 'RATTRAPAGE'],
            date__gte=today,
            date__lte=horizon,
        ).select_related('subject', 'class_group')

        sent = 0
        for exam in exams:
            enrollments = Enrollment.objects.filter(
                class_obj=exam.class_group, is_active=True, status='ENROLLED'
            ).select_related('student__user')

            for enr in enrollments:
                student = enr.student

                # Count absences
                absence_count = student.attendance_records.filter(
                    status='ABSENT'
                ).count()

                # Check unpaid invoices
                has_unpaid = Invoice.objects.filter(
                    student=student,
                    status__in=['SENT', 'PARTIAL', 'OVERDUE']
                ).exists()

                reasons = []
                if absence_count >= threshold:
                    reasons.append(f'{absence_count} absence(s) enregistrée(s)')
                if has_unpaid:
                    reasons.append('frais scolaires impayés')

                if not reasons:
                    continue

                reason_str = ' et '.join(reasons)
                exam_label = f'{exam.title} ({exam.subject.name}) le {exam.date}'

                # Warn student
                n = Notification.send(
                    recipient=student.user,
                    notification_type='ALERT',
                    priority='URGENT',
                    title='⚠️ Admission à l\'examen',
                    message=(
                        f'Vous risquez de ne pas être admis(e) à : {exam_label}. '
                        f'Raison(s) : {reason_str}. '
                        f'Contactez l\'administration au plus vite.'
                    ),
                    data={
                        'exam_id':   str(exam.id),
                        'exam_date': str(exam.date),
                        'reasons':   reasons,
                    },
                )
                dispatch_notification(n, channels=['IN_APP', 'PUSH'])
                sent += 1

                # Warn parents
                parents = StudentParent.objects.filter(
                    student=student, receives_notifications=True
                ).select_related('parent__user')

                for sp in parents:
                    n = Notification.send(
                        recipient=sp.parent.user,
                        notification_type='ALERT',
                        priority='URGENT',
                        title='⚠️ Admission à l\'examen refusée',
                        message=(
                            f'{student.user.full_name} risque de ne pas être admis(e) à : '
                            f'{exam_label}. Raison(s) : {reason_str}. '
                            f'Contactez l\'établissement immédiatement.'
                        ),
                        data={
                            'student_id': str(student.id),
                            'exam_id':    str(exam.id),
                            'exam_date':  str(exam.date),
                            'reasons':    reasons,
                        },
                    )
                    dispatch_notification(n, channels=['IN_APP', 'PUSH'])
                    sent += 1

        self.stdout.write(self.style.SUCCESS(f'{sent} avertissement(s) envoyé(s).'))
