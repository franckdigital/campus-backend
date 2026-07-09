"""
Simulate a given date and run the échéancier reminder logic, then print what
was actually sent to the student and their parent.

With no --email: only loops over the @escam-test.ci test students (see
seed_echeancier_students) — safe to run against any database, never touches
real students. Pass --email to target ONE specific student directly instead,
by any email — including a real, newly-enrolled student. This sends a REAL
notification (push + in-app) to that student and their parents if they're
genuinely behind on their échéancier, exactly as the daily prod task would.

Usage:
    python manage.py seed_echeancier_students   # once, to create the ESCAM test data
    python manage.py test_echeancier_reminders                    # defaults to 2026-06-25, test students only
    python manage.py test_echeancier_reminders --date 2026-05-25
    python manage.py test_echeancier_reminders --email fatou.bamba@escam-test.ci

    # Target a real student directly (any email, not just @escam-test.ci)
    python manage.py test_echeancier_reminders --email real.student@example.com --date 2026-07-25

    # Re-send right away instead of waiting out the real 3-day throttle
    # (_maybe_remind_student skips a student who already got a reminder less
    # than REMINDER_INTERVAL_DAYS ago) — deletes that student's + their
    # parents' previous echeancier_reminder Notification rows first, so the
    # cycle looks brand new to the task. Test-only, never do this in prod.
    python manage.py test_echeancier_reminders --email fatou.bamba@escam-test.ci --force
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
        parser.add_argument(
            '--force', action='store_true',
            help="Supprime les rappels echeancier precedents du/des etudiant(s) cible(s) "
                 "avant de tester, pour contourner le throttle de 3 jours."
        )

    def handle(self, *args, **options):
        from apps.students.models import Student, StudentParent
        from apps.finance.models import compute_tuition_schedule_status, get_student_installment_schedule
        from apps.finance.tasks import _maybe_remind_student, REMINDER_CATEGORY
        from apps.notifications.models import Notification

        sim_date = datetime.datetime.strptime(options['date'], '%Y-%m-%d').date()
        fake_now = timezone.make_aware(datetime.datetime.combine(sim_date, datetime.time(9, 0)))

        if options['email']:
            # Explicit target — any student, real or test. Deliberate opt-in,
            # unlike the no-args case which must stay test-only.
            students = Student.objects.filter(user__email=options['email']).select_related('user', 'site')
            if not students.filter(user__email__endswith='@escam-test.ci').exists():
                self.stdout.write(self.style.WARNING(
                    "ATTENTION: cible hors @escam-test.ci — ceci enverra une VRAIE notification "
                    "(push + in-app) a un vrai etudiant/parent si son echeancier est en retard."
                ))
        else:
            students = Student.objects.filter(user__email__endswith='@escam-test.ci').select_related('user', 'site')

        if not students.exists():
            self.stdout.write(self.style.ERROR(
                "Aucun etudiant trouve pour ce filtre. Sans --email, lancez d'abord : "
                "python manage.py seed_echeancier_students"
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f'Simulation au {sim_date.isoformat()}'))

        parent_emails = list(
            StudentParent.objects.filter(student__in=students).values_list('parent__user__email', flat=True)
        )

        if options['force']:
            student_emails_for_wipe = list(students.values_list('user__email', flat=True))
            deleted, _ = Notification.objects.filter(
                recipient__email__in=student_emails_for_wipe + parent_emails,
                notification_type='REMINDER',
                data__category=REMINDER_CATEGORY,
            ).delete()
            self.stdout.write(self.style.WARNING(
                f'--force: {deleted} ancien(s) rappel(s) supprime(s) pour contourner le throttle de 3 jours.'
            ))

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
