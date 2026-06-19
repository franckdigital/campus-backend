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
