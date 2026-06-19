"""
python manage.py send_monthly_reminders [--days-before N]

Sends push + in-app reminders to parents of students with unpaid/partial invoices,
triggered when N or fewer days remain before month end.
Cron: daily, e.g. 0 9 * * * python manage.py send_monthly_reminders
"""
import calendar
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Send end-of-month payment reminders to parents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-before', type=int, default=5,
            help='Send reminders when N or fewer days remain before month end (default: 5)'
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Send regardless of days remaining'
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        _, last_day = calendar.monthrange(today.year, today.month)
        days_left = last_day - today.day

        if not options['force'] and days_left > options['days_before']:
            self.stdout.write(
                f'{days_left} jours avant la fin du mois — seuil {options["days_before"]}. '
                f'Utilisez --force pour forcer.'
            )
            return

        from apps.finance.models import Invoice
        from apps.students.models import StudentParent
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_notification

        unpaid = Invoice.objects.filter(
            status__in=['SENT', 'PARTIAL', 'OVERDUE']
        ).select_related('student__user', 'site')

        count = 0
        for invoice in unpaid:
            student  = invoice.student
            balance  = invoice.balance

            parents = StudentParent.objects.filter(
                student=student, receives_notifications=True
            ).select_related('parent__user')

            for sp in parents:
                parent_user = sp.parent.user
                n = Notification.send(
                    recipient=parent_user,
                    notification_type='REMINDER',
                    priority='HIGH',
                    title='Rappel de paiement',
                    message=(
                        f'La facture {invoice.invoice_number} de '
                        f'{student.user.full_name} est toujours en attente. '
                        f'Montant restant : {balance} FCFA. '
                        f'Fin du mois dans {days_left} jour(s).'
                    ),
                    data={
                        'invoice_id': str(invoice.id),
                        'student_id': str(student.id),
                        'balance':    str(balance),
                    },
                    site=invoice.site,
                )
                dispatch_notification(n, channels=['IN_APP', 'PUSH'])
                count += 1

        self.stdout.write(self.style.SUCCESS(f'{count} rappel(s) envoyé(s).'))
