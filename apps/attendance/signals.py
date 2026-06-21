import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AttendanceRecord

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AttendanceRecord)
def on_attendance_record_save(sender, instance, created, **kwargs):
    """Push-notify parents when their child is marked ABSENT or LATE."""
    if instance.status not in ('ABSENT', 'LATE'):
        return
    try:
        from apps.notifications.push import push_to_user
        from apps.students.models import StudentParent

        student = instance.student
        session = instance.attendance_session.session
        date_str = str(instance.attendance_session.date)
        subject_name = session.subject.name if session and session.subject else 'cours'

        parents = StudentParent.objects.filter(
            student=student, receives_notifications=True
        ).select_related('parent__user')

        if instance.status == 'ABSENT':
            title = '⚠️ Absence signalée'
            body = f'{student.user.full_name} est absent(e) en {subject_name} le {date_str}.'
            notif_type = 'ABSENCE'
        else:
            title = '🕐 Retard signalé'
            body = f'{student.user.full_name} est arrivé(e) en retard en {subject_name} le {date_str}.'
            notif_type = 'ATTENDANCE'

        for sp in parents:
            parent_user = sp.parent.user
            push_to_user(
                parent_user,
                title=title,
                body=body,
                data={
                    'type':       notif_type,
                    'student_id': str(student.id),
                    'date':       date_str,
                    'status':     instance.status,
                },
            )
    except Exception as exc:
        logger.error("Attendance push-notify failed: %s", exc)
