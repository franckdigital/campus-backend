"""
Simulate a given date and run the échéancier reminder logic against the
ESCAM test students (see seed_echeancier_students), then print what was
actually sent to the student and their parent — safe to run against any
database since it never loops over real students, only the @escam-test.ci
ones created by the seed command.

Usage:
    python manage.py seed_echeancier_students   # once, to create the test data
    python manage.py test_echeancier_reminders                    # defaults to 2026-06-25
    python manage.py test_echeancier_reminders --date 2026-05-25
    python manage.py test_echeancier_reminders --email fatou.bamba@escam-test.ci
"""
import datetime
from unittest.mock import patch

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Simule une date et declenche le rappel d'echeancier pour les etudiants de test ESCAM"

    def add_arguments(self, parser):
        parser.add_argument('--date', default='2026-06-25', help='Date simulee (YYYY-MM-DD)')
        parser.add_argument('--email', default=None, help="Ne tester qu'un seul etudiant (email)")

    def handle(self, *args, **options):
        from apps.students.models import Student, StudentParent
        from apps.finance.models import compute_tuition_schedule_status, get_student_installment_schedule
        from apps.finance.tasks import _maybe_remind_student
        from apps.notifications.models import Notification

        sim_date = datetime.datetime.strptime(options['date'], '%Y-%m-%d').date()
        fake_now = timezone.make_aware(datetime.datetime.combine(sim_date, datetime.time(9, 0)))

        students = Student.objects.filter(user__email__endswith='@escam-test.ci').select_related('user', 'site')
        if options['email']:
            students = students.filter(user__email=options['email'])

        if not students.exists():
            self.stdout.write(self.style.ERROR(
                "Aucun etudiant de test trouve. Lancez d'abord : "
                "python manage.py seed_echeancier_students"
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f'Simulation au {sim_date.isoformat()}'))

        parent_emails = list(
            StudentParent.objects.filter(student__in=students).values_list('parent__user__email', flat=True)
        )

        total_sent = 0
        with patch('django.utils.timezone.now', return_value=fake_now):
            for student in students:
                status = compute_tuition_schedule_status(student)
                schedule = get_student_installment_schedule(student)

                self.stdout.write(f"\n  -- {student.user.full_name} ({student.user.email}) --")
                self.stdout.write(
                    f"     A jour: {status['is_up_to_date']} | "
                    f"Du: {status['cumulative_due']} FCFA | Paye: {status['cumulative_paid']} FCFA"
                )
                for row in schedule['installments']:
                    self.stdout.write(
                        f"       {row['label']} ({row['due_date']}): "
                        f"{row['amount']} FCFA — {row['status']}"
                    )

                sent = _maybe_remind_student(student, sim_date)
                total_sent += sent
                self.stdout.write(
                    self.style.SUCCESS(f'     -> {sent} notification(s) envoyee(s)')
                    if sent else self.style.WARNING('     -> Aucune notification (a jour, override, ou hors fenetre de rappel)')
                )

        self.stdout.write(self.style.MIGRATE_HEADING(f'\nTotal: {total_sent} notification(s)'))

        student_emails = list(students.values_list('user__email', flat=True))
        recent = Notification.objects.filter(
            recipient__email__in=student_emails + parent_emails,
            data__category='echeancier_reminder',
        ).order_by('-created_at')[:10]

        self.stdout.write(self.style.MIGRATE_HEADING('\nDernieres notifications de rappel en base:'))
        for n in recent:
            self.stdout.write(f"  [{n.created_at:%Y-%m-%d %H:%M}] {n.recipient.email}: {n.title}")
            self.stdout.write(f"      {n.message}")
