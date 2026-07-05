from celery import shared_task
import logging

logger = logging.getLogger(__name__)

# Reminders only start once the month is nearly over (mirrors the "à jour"
# rule elsewhere: a student must have settled the previous month's fraction
# by the 5th of the following month) — and then repeat every N days,
# including a running cycle that crosses into the next month, until the
# student is fully caught up (compute_tuition_schedule_status.is_up_to_date).
REMINDER_START_DAY = 25
REMINDER_INTERVAL_DAYS = 3
REMINDER_CATEGORY = 'echeancier_reminder'


def _maybe_remind_student(student, today):
    """Send an échéancier reminder to one student + their parents if (and
    only if) they're actually due for one today. Returns the number of
    notifications sent (0 if skipped). Factored out of send_echeancier_reminders
    so a test/shell script can exercise this exact logic against a specific
    student without looping over — and potentially notifying — every real
    student in the database.
    """
    from apps.finance.models import compute_tuition_schedule_status
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_notification, _get_student_parents

    schedule_status = compute_tuition_schedule_status(student)
    if not schedule_status['has_schedule']:
        return 0
    if schedule_status['is_up_to_date'] or schedule_status['echeance_override']:
        return 0

    last_reminder = Notification.objects.filter(
        recipient=student.user,
        notification_type='REMINDER',
        data__category=REMINDER_CATEGORY,
    ).order_by('-created_at').first()

    if last_reminder is None:
        # First reminder of a new shortfall cycle — only starts on/after
        # the 25th, never earlier in the month.
        if today.day < REMINDER_START_DAY:
            return 0
    else:
        days_since = (today - last_reminder.created_at.date()).days
        if days_since < REMINDER_INTERVAL_DAYS:
            return 0

    remaining = float(schedule_status['cumulative_due']) - float(schedule_status['cumulative_paid'])
    if remaining <= 0:
        return 0

    remaining_str = f'{remaining:,.0f}'.replace(',', ' ')
    title = 'Rappel — échéancier de scolarité'
    sent_count = 0

    student_notif = Notification.send(
        recipient=student.user,
        notification_type='REMINDER',
        priority='HIGH',
        title=title,
        message=(
            f'Vous avez un solde de {remaining_str} FCFA en retard sur votre échéancier '
            f'de scolarité. Merci de régulariser votre situation auprès de l\'administration.'
        ),
        data={'category': REMINDER_CATEGORY, 'student_id': str(student.id)},
        action_url='/student/finances',
        site=student.site,
    )
    dispatch_notification(student_notif, channels=['IN_APP', 'PUSH'])
    sent_count += 1

    for parent_user in _get_student_parents(student):
        parent_notif = Notification.send(
            recipient=parent_user,
            notification_type='REMINDER',
            priority='HIGH',
            title=title,
            message=(
                f'Votre enfant {student.user.full_name} a un solde de {remaining_str} FCFA '
                f'en retard sur son échéancier de scolarité. Merci de régulariser la situation '
                f'auprès de l\'administration.'
            ),
            data={'category': REMINDER_CATEGORY, 'student_id': str(student.id)},
            action_url='/parent/children',
            site=student.site,
        )
        dispatch_notification(parent_notif, channels=['IN_APP', 'PUSH'])
        sent_count += 1

    return sent_count


@shared_task(name='finance.send_echeancier_reminders')
def send_echeancier_reminders():
    """Daily periodic task: nag students (and their parents) who are behind
    on their échéancier de scolarité — whether they've paid nothing at all or
    only partially — starting on the 25th of the month, then every 3 days,
    until they're fully up to date or the admin grants an override.

    Idempotent per run: a student/parent pair only ever gets one reminder
    per REMINDER_INTERVAL_DAYS window, tracked via the most recent
    Notification of type REMINDER tagged with data.category=echeancier_reminder.
    """
    from django.utils import timezone
    from apps.students.models import Student

    today = timezone.now().date()
    sent_count = 0

    students = Student.objects.filter(is_active=True, status='ACTIVE').select_related('user', 'site')
    for student in students:
        sent_count += _maybe_remind_student(student, today)

    logger.info('send_echeancier_reminders: %d notification(s) sent', sent_count)
    return sent_count
