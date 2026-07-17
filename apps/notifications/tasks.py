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
