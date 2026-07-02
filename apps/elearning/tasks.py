"""
Celery tasks — Classes virtuelles & notifications de session.
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def _log(virtual_class, segment, log_type, detail):
    from .models import SessionLog
    try:
        SessionLog.objects.create(
            virtual_class=virtual_class,
            segment=segment,
            log_type=log_type,
            detail=detail,
        )
    except Exception as e:
        logger.warning(f"SessionLog failed: {e}")


def _notify_users(classroom, message, segment=None):
    """
    Envoie une notification in-app à tous les étudiants de la classe
    et au créateur (enseignant). Utilise le système de notifications
    existant si disponible, sinon logue seulement.
    """
    try:
        from apps.notifications.models import Notification  # type: ignore
        recipients = list(classroom.class_obj.students.values_list('user_id', flat=True))
        if classroom.created_by_id:
            recipients.append(classroom.created_by_id)

        for user_id in set(recipients):
            Notification.objects.create(
                user_id=user_id,
                title=f"Classe virtuelle : {classroom.title}",
                body=message,
                notification_type='VIRTUAL_CLASS',
                related_object_id=str(classroom.id),
            )
    except Exception:
        logger.info(f"[Notification] {classroom.title}: {message}")


# ── Rappels pré-session ──────────────────────────────────────────────────────

@shared_task(name='elearning.notify_segment_10min')
def notify_segment_10min(segment_id):
    from .models import MeetingSegment
    try:
        seg = MeetingSegment.objects.select_related('virtual_class').get(id=segment_id)
    except MeetingSegment.DoesNotExist:
        return
    if seg.status in ('TERMINEE', 'ANNULEE'):
        return

    classroom = seg.virtual_class
    label = f"Session {seg.sequence}/{classroom.segments.count()}"
    msg = f"Votre cours continue dans 10 minutes. {label} de « {classroom.title} »."
    _notify_users(classroom, msg, seg)
    _log(classroom, seg, 'NOTIF_10MIN', msg)
    logger.info(f"[10min] {classroom.title} seg#{seg.sequence}")


@shared_task(name='elearning.notify_segment_5min')
def notify_segment_5min(segment_id):
    from .models import MeetingSegment
    try:
        seg = MeetingSegment.objects.select_related('virtual_class').get(id=segment_id)
    except MeetingSegment.DoesNotExist:
        return
    if seg.status in ('TERMINEE', 'ANNULEE'):
        return

    classroom = seg.virtual_class
    msg = f"Préparez-vous à rejoindre la prochaine session de « {classroom.title} » dans 5 minutes."
    _notify_users(classroom, msg, seg)
    _log(classroom, seg, 'NOTIF_5MIN', msg)


@shared_task(name='elearning.notify_segment_1min')
def notify_segment_1min(segment_id):
    from .models import MeetingSegment
    try:
        seg = MeetingSegment.objects.select_related('virtual_class').get(id=segment_id)
    except MeetingSegment.DoesNotExist:
        return
    if seg.status in ('TERMINEE', 'ANNULEE'):
        return

    classroom = seg.virtual_class
    msg = f"Cliquez sur « Continuer » pour rejoindre la session {seg.sequence} de « {classroom.title} »."
    _notify_users(classroom, msg, seg)
    _log(classroom, seg, 'NOTIF_1MIN', msg)


@shared_task(name='elearning.notify_next_session')
def notify_next_session(current_segment_id):
    """Notifie les participants que la session suivante est disponible."""
    from .models import MeetingSegment
    try:
        seg = MeetingSegment.objects.select_related('virtual_class').get(id=current_segment_id)
        next_seg = MeetingSegment.objects.get(
            virtual_class=seg.virtual_class, sequence=seg.sequence + 1
        )
    except MeetingSegment.DoesNotExist:
        return

    classroom = seg.virtual_class
    msg = (
        f"La session {next_seg.sequence} de « {classroom.title} » commence maintenant. "
        f"Cliquez pour rejoindre."
    )
    _notify_users(classroom, msg, next_seg)
    _log(classroom, next_seg, 'NOTIF_NEXT', msg)


# ── Changement automatique de statut ─────────────────────────────────────────

@shared_task(name='elearning.auto_start_segment')
def auto_start_segment(segment_id):
    """Passe le segment en EN_COURS automatiquement à l'heure prévue."""
    from .models import MeetingSegment
    try:
        seg = MeetingSegment.objects.select_related('virtual_class').get(id=segment_id)
    except MeetingSegment.DoesNotExist:
        return

    if seg.status not in ('PLANIFIEE', 'EN_ATTENTE'):
        return

    seg.status = 'EN_COURS'
    seg.started_at = timezone.now()
    seg.save()
    _log(seg.virtual_class, seg, 'STARTED', f'Segment {seg.sequence} démarré automatiquement')
    logger.info(f"[AUTO_START] Segment {seg.sequence} of {seg.virtual_class.title}")


@shared_task(name='elearning.auto_end_segment')
def auto_end_segment(segment_id):
    """Termine le segment automatiquement et notifie la transition."""
    from .models import MeetingSegment
    try:
        seg = MeetingSegment.objects.select_related('virtual_class').get(id=segment_id)
    except MeetingSegment.DoesNotExist:
        return

    if seg.status != 'EN_COURS':
        return

    seg.status = 'TERMINEE'
    seg.ended_at = timezone.now()
    seg.save()
    _log(seg.virtual_class, seg, 'ENDED', f'Segment {seg.sequence} terminé automatiquement')

    next_seg = MeetingSegment.objects.filter(
        virtual_class=seg.virtual_class,
        sequence=seg.sequence + 1,
    ).first()

    if next_seg:
        next_seg.status = 'EN_ATTENTE'
        next_seg.save()
        _log(seg.virtual_class, next_seg, 'TRANSITION',
             f'Transition automatique vers segment {next_seg.sequence}')
        # Notifier immédiatement
        notify_next_session.delay(str(seg.id))
    else:
        # Fin de la classe
        classroom = seg.virtual_class
        classroom.is_ended = True
        classroom.ended_at = timezone.now()
        classroom.save()


@shared_task(name='elearning.schedule_classroom_tasks')
def schedule_classroom_tasks(classroom_id):
    """
    Planifie l'ensemble des tâches de notification et de transition
    pour tous les segments d'une classe virtuelle.
    Appeler après génération des segments.
    """
    from .models import VirtualClassroom, MeetingSegment
    import datetime

    try:
        classroom = VirtualClassroom.objects.get(id=classroom_id)
    except VirtualClassroom.DoesNotExist:
        return

    segments = list(MeetingSegment.objects.filter(
        virtual_class=classroom, is_active=True
    ).order_by('sequence'))

    for seg in segments:
        sid = str(seg.id)
        st  = seg.start_time
        et  = seg.end_time

        def eta(dt):
            return dt if timezone.is_aware(dt) else timezone.make_aware(dt)

        # Auto-start à l'heure
        auto_start_segment.apply_async(args=[sid], eta=eta(st))
        # Auto-end à la fin
        auto_end_segment.apply_async(args=[sid], eta=eta(et))

        # Notifications avant le début (sauf premier segment)
        if seg.sequence > 1:
            notify_segment_10min.apply_async(
                args=[sid], eta=eta(st - datetime.timedelta(minutes=10))
            )
            notify_segment_5min.apply_async(
                args=[sid], eta=eta(st - datetime.timedelta(minutes=5))
            )
            notify_segment_1min.apply_async(
                args=[sid], eta=eta(st - datetime.timedelta(minutes=1))
            )

    logger.info(
        f"[SCHEDULE] {len(segments)} segments planifiés pour {classroom.title}"
    )
    return {'scheduled': len(segments)}
