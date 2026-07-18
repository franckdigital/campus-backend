from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(name='notifications.retry_failed')
def retry_failed_notifications():
    """Periodic task: retry RETRYING logs that are due."""
    from .services import retry_failed_logs
    count = retry_failed_logs()
    logger.info("Retried %d notification log(s)", count)
    return count


@shared_task(name='notifications.check_push_receipts')
def check_push_receipts():
    """Periodic task: confirm real delivery outcome for PUSH logs whose
    Expo ticket said 'ok' but whose actual receipt hasn't been checked yet.
    A ticket 'ok' only means Expo accepted the request — without this task
    a real delivery failure (dead token, misconfigured Android FCM
    credential, etc.) never shows up anywhere and looks identical to a
    successful send. See apps.notifications.push.check_expo_receipts."""
    from .push import check_expo_receipts
    result = check_expo_receipts()
    logger.info(
        "check_push_receipts: %d log(s) checked, %d delivered, %d failed",
        result['checked'], result['delivered'], result['failed'],
    )
    return result


@shared_task(name='notifications.send_exam_reminders')
def send_exam_reminders():
    """Daily periodic task: for every active, automatic ReminderConfig of
    type EXAMEN whose exam date hasn't passed yet, send a reminder to all
    active students (+ parents) if they're due for one today according to
    that config's own frequency (see services.send_exam_reminder_config)."""
    from django.utils import timezone
    from .models import ReminderConfig
    from .services import send_exam_reminder_config

    today = timezone.now().date()
    configs = ReminderConfig.objects.filter(
        reminder_type='EXAMEN', is_active=True, is_automatic=True, exam_date__gte=today,
    )
    sent_count = sum(send_exam_reminder_config(c, today) for c in configs)
    logger.info('send_exam_reminders: %d notification(s) sent', sent_count)
    return sent_count
