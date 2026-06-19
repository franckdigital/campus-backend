from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import time as dt_time, date as date_type


DAY_END     = dt_time(18, 30)
EVENING_END = dt_time(22, 0)


class Command(BaseCommand):
    help = 'Marque absents les etudiants non pointes du jour (cron: 18h30 slot=DAY, 22h00 slot=EVENING)'

    def add_arguments(self, parser):
        parser.add_argument('--slot', choices=['DAY', 'EVENING', 'ALL'], default='ALL')
        parser.add_argument('--date', type=str, default=None, help='YYYY-MM-DD (defaut: aujourd\'hui)')

    def handle(self, *args, **options):
        from apps.attendance.models import AttendanceSession, AttendanceRecord
        from apps.academic.models import Session as AcademicSession, Enrollment

        slot        = options['slot']
        target_date = date_type.fromisoformat(options['date']) if options['date'] else timezone.localdate()
        target_dow  = target_date.weekday()

        sessions_qs = AcademicSession.objects.filter(day_of_week=target_dow, is_active=True)
        if slot == 'DAY':
            sessions_qs = sessions_qs.filter(start_time__lt=DAY_END)
        elif slot == 'EVENING':
            sessions_qs = sessions_qs.filter(start_time__gte=DAY_END)

        marked = 0
        processed = 0

        for session in sessions_qs:
            att_session, _ = AttendanceSession.objects.get_or_create(
                session=session,
                date=target_date,
                defaults={'status': 'CLOSED'}
            )

            # Skip postponed sessions — no absence should be recorded
            if att_session.is_postponed:
                self.stdout.write(f'  [AJOURNÉ] {session} — ignoré')
                continue

            if att_session.status == 'OPEN':
                att_session.status = 'CLOSED'
                att_session.closed_at = timezone.now()
                att_session.save()

            enrollments = Enrollment.objects.filter(
                class_obj=session.class_obj, is_active=True, status='ENROLLED'
            ).select_related('student')

            for e in enrollments:
                _, created = AttendanceRecord.objects.get_or_create(
                    attendance_session=att_session,
                    student=e.student,
                    defaults={'status': 'ABSENT', 'check_in_method': 'AUTO'}
                )
                if created:
                    marked += 1

            processed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'[{target_date}] slot={slot}: {marked} absents marques sur {processed} seances'
            )
        )
