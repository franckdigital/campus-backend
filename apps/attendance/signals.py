import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AttendanceRecord

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AttendanceRecord)
def on_attendance_record_save(sender, instance, created, **kwargs):
    """Push-notify parents when their child is marked ABSENT."""
    if instance.status != 'ABSENT':
        return
    # Skip auto-marked records that trigger bulk — fire only once per real event
    try:
        from apps.notifications.services import notify_absence_recorded
        from apps.notifications.push import push_to_user
        from apps.students.models import StudentParent

        student = instance.student
        session = instance.attendance_session.session
        date_str = str(instance.attendance_session.date)

        parents = StudentParent.objects.filter(
            student=student, receives_notifications=True
        ).select_related('parent__user')

        for sp in parents:
            parent_user = sp.parent.user
            push_to_user(
                parent_user,
                title='⚠️ Absence signalée',
                body=(
                    f'{student.user.full_name} est absent(e) en '
                    f'{session.subject.name} le {date_str}.'
                ),
                data={
                    'type':       'ABSENCE',
                    'student_id': str(student.id),
                    'date':       date_str,
                },
            )
    except Exception as exc:
        logger.error("Attendance push-notify failed: %s", exc)
