"""
Notification dispatch service.
Handles in-app, email, SMS, WhatsApp, and WebSocket channels.
"""
import logging
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail

from .models import Notification, NotificationLog, NotificationPreference

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Low-level channel senders
# ──────────────────────────────────────────────────────────────

def _send_websocket(notification):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.recipient.id}',
            {
                'type': 'notification_message',
                'notification': {
                    'id': str(notification.id),
                    'type': notification.notification_type,
                    'priority': notification.priority,
                    'title': notification.title,
                    'message': notification.message,
                    'data': notification.data,
                    'action_url': notification.action_url,
                    'created_at': notification.created_at.isoformat(),
                }
            }
        )
        log = NotificationLog.objects.create(
            notification=notification, channel='WEBSOCKET', status='SENT',
            sent_at=timezone.now()
        )
    except Exception as exc:
        logger.warning("WebSocket send failed: %s", exc)


def _send_email(notification, log):
    recipient = notification.recipient
    email = getattr(recipient, 'email', '') or ''
    if not email:
        log.mark_failed('Pas d\'adresse email')
        return

    try:
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@campus.edu',
            recipient_list=[email],
            fail_silently=False,
        )
        log.mark_sent(address=email)
    except Exception as exc:
        logger.error("Email send failed to %s: %s", email, exc)
        log.mark_failed(str(exc))


def _send_sms(notification, log, phone_number):
    """
    Send SMS via configured provider.
    Set SMS_PROVIDER = 'twilio' | 'infobip' | 'mock' in settings.
    """
    provider = getattr(settings, 'SMS_PROVIDER', 'mock')

    try:
        if provider == 'twilio':
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=notification.message,
                from_=settings.TWILIO_FROM_NUMBER,
                to=phone_number,
            )
        elif provider == 'infobip':
            import requests as req
            resp = req.post(
                f"https://{settings.INFOBIP_BASE_URL}/sms/2/text/advanced",
                headers={
                    'Authorization': f"App {settings.INFOBIP_API_KEY}",
                    'Content-Type': 'application/json',
                },
                json={'messages': [{'destinations': [{'to': phone_number}], 'text': notification.message}]},
                timeout=10,
            )
            resp.raise_for_status()
        else:
            # Mock — log only, no real send
            logger.info("[SMS MOCK] To %s: %s", phone_number, notification.message)

        log.mark_sent(address=phone_number)
    except Exception as exc:
        logger.error("SMS send failed to %s: %s", phone_number, exc)
        log.mark_failed(str(exc))


def _send_whatsapp(notification, log, number):
    """
    Send WhatsApp message via configured provider.
    Set WHATSAPP_PROVIDER = 'twilio' | 'meta' | 'mock' in settings.
    """
    provider = getattr(settings, 'WHATSAPP_PROVIDER', 'mock')

    try:
        if provider == 'twilio':
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=notification.message,
                from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                to=f"whatsapp:{number}",
            )
        elif provider == 'meta':
            import requests as req
            resp = req.post(
                f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_ID}/messages",
                headers={
                    'Authorization': f"Bearer {settings.WHATSAPP_TOKEN}",
                    'Content-Type': 'application/json',
                },
                json={
                    'messaging_product': 'whatsapp',
                    'to': number,
                    'type': 'text',
                    'text': {'body': notification.message},
                },
                timeout=10,
            )
            resp.raise_for_status()
        else:
            logger.info("[WHATSAPP MOCK] To %s: %s", number, notification.message)

        log.mark_sent(address=number)
    except Exception as exc:
        logger.error("WhatsApp send failed to %s: %s", number, exc)
        log.mark_failed(str(exc))


# ──────────────────────────────────────────────────────────────
# Main dispatcher
# ──────────────────────────────────────────────────────────────

# Must match the Android channel ids registered client-side in
# campus-mobile/src/hooks/usePushNotifications.js (ANDROID_CHANNELS) — all
# three are HIGH/MAX importance there. Omitting channelId on the Expo push
# makes Expo fall back to its own implicit "default" channel (DEFAULT
# importance), which never shows as a heads-up banner on a locked screen —
# the notification still arrives, just silently, only visible once the
# phone is unlocked and the shade is opened.
_ANDROID_CHANNEL_BY_TYPE = {
    'PAYMENT': 'payments',
    'REMINDER': 'payments',
    'ATTENDANCE': 'attendance',
    'ABSENCE': 'attendance',
}


def _android_channel_for(notification):
    return _ANDROID_CHANNEL_BY_TYPE.get(notification.notification_type, 'default')


def dispatch_notification(notification, channels=None, force_channels=None):
    """
    Send a notification on all requested channels.
    - channels: explicit list or None → read from user preferences
    - force_channels: bypass preference check
    """
    _send_websocket(notification)

    if force_channels:
        active = force_channels
    elif channels:
        active = channels
    else:
        try:
            prefs = notification.recipient.notification_preferences
            active = prefs.active_channels()
        except NotificationPreference.DoesNotExist:
            active = ['IN_APP', 'PUSH']

    prefs = None
    try:
        prefs = notification.recipient.notification_preferences
    except NotificationPreference.DoesNotExist:
        pass

    for channel in active:
        if channel in ('IN_APP', 'WEBSOCKET'):
            continue  # already handled above

        log = NotificationLog.objects.create(
            notification=notification,
            channel=channel,
            status='PENDING',
        )

        if channel == 'EMAIL':
            _send_email(notification, log)

        elif channel == 'SMS':
            phone = (prefs.phone_number if prefs else '') or getattr(notification.recipient, 'phone', '')
            if phone:
                _send_sms(notification, log, phone)
            else:
                log.mark_failed('Numéro SMS introuvable')

        elif channel == 'WHATSAPP':
            wa_number = (prefs.whatsapp_number if prefs else '') or ''
            if wa_number:
                _send_whatsapp(notification, log, wa_number)
            else:
                log.mark_failed('Numéro WhatsApp introuvable')

        elif channel == 'PUSH':
            from .push import push_to_user
            success, _ = push_to_user(
                notification.recipient,
                notification.title,
                notification.message,
                data=notification.data,
                channel_id=_android_channel_for(notification),
            )
            if success > 0:
                log.mark_sent()
            else:
                log.mark_failed('Aucun token actif ou envoi échoué')


# ──────────────────────────────────────────────────────────────
# Event-triggered helpers
# ──────────────────────────────────────────────────────────────

def _get_student_parents(student):
    return [
        sp.parent.user
        for sp in student.student_parents.filter(receives_notifications=True).select_related('parent__user')
        if sp.parent and sp.parent.user
    ]


def notify_payment_validated(payment):
    """H2: Paiement validé → parents (et étudiant)."""
    student = payment.invoice.student
    amount  = payment.amount
    inv_no  = payment.invoice.invoice_number

    # Notify student
    n = Notification.send(
        recipient=student.user,
        notification_type='PAYMENT',
        title='✅ Paiement confirmé',
        message=f'Votre paiement de {int(amount):,} FCFA a été validé (facture {inv_no}).'.replace(',', ' '),
        data={'payment_id': str(payment.id), 'invoice_id': str(payment.invoice.id), 'type': 'PAYMENT'},
        action_url=f'/payments/{payment.id}',
        site=payment.invoice.site,
    )
    dispatch_notification(n, channels=['IN_APP', 'PUSH'])

    # Notify parents
    for parent_user in _get_student_parents(student):
        n = Notification.send(
            recipient=parent_user,
            notification_type='PAYMENT',
            title='✅ Paiement reçu',
            message=f'Paiement de {int(amount):,} FCFA validé pour {student.user.full_name} (facture {inv_no}).'.replace(',', ' '),
            data={'payment_id': str(payment.id), 'student_id': str(student.id), 'type': 'PAYMENT'},
            priority='HIGH',
            site=payment.invoice.site,
        )
        dispatch_notification(n, channels=['IN_APP', 'PUSH'])


# kept for backward-compat
notify_payment_received = notify_payment_validated


def notify_manual_payment_submitted(payment):
    """Semi-auto Mobile Money submission (mobile app) → admin/finance staff,
    so someone reviews the proof and validates it (see
    apps.payments.views.ManualMobileMoneySubmitView and
    apps.finance.views.PaymentViewSet.validate). Mirrors notify_cash_deposit's
    role targeting — this is the same "money came in, needs review" event,
    just declared by the payer instead of recorded at a cash register."""
    from apps.accounts.models import User

    student = payment.invoice.student
    amount  = payment.amount
    inv_no  = payment.invoice.invoice_number
    payer_name = payment.submitted_by.full_name if payment.submitted_by else student.user.full_name

    reviewers = User.objects.filter(
        is_active=True,
        roles__name__in=['ADMIN', 'DIRECTOR', 'FINANCE'],
    ).distinct()

    for user in reviewers:
        n = Notification.send(
            recipient=user,
            notification_type='PAYMENT',
            priority='HIGH',
            title='💰 Paiement Mobile Money à valider',
            message=(
                f'{payer_name} a soumis une preuve de paiement de {int(amount):,} FCFA '
                f'pour {student.user.full_name} (facture {inv_no}). En attente de validation.'
            ).replace(',', ' '),
            data={
                'payment_id': str(payment.id),
                'invoice_id': str(payment.invoice.id),
                'student_id': str(student.id),
                'type': 'PAYMENT_PENDING',
            },
            action_url=f'/payments/{payment.id}',
            site=payment.invoice.site,
        )
        dispatch_notification(n, channels=['IN_APP', 'PUSH'])


def notify_absence_recorded(attendance_record):
    """H2: Absence constatée → parents."""
    student = attendance_record.student
    session = attendance_record.attendance_session.session
    date_str = str(attendance_record.attendance_session.date)
    subject_name = session.subject.name if session and session.subject else 'cours'

    for parent_user in _get_student_parents(student):
        n = Notification.send(
            recipient=parent_user,
            notification_type='ABSENCE',
            priority='HIGH',
            title='⚠️ Absence signalée',
            message=(
                f'{student.user.full_name} a été marqué(e) absent(e) '
                f'en {subject_name} le {date_str}.'
            ),
            data={
                'student_id': str(student.id),
                'session_id': str(session.id),
                'date': date_str,
                'status': 'ABSENT',
                'type': 'ABSENCE',
            },
        )
        dispatch_notification(n, channels=['IN_APP', 'PUSH'])


# kept for backward-compat
notify_absence = notify_absence_recorded


def notify_late_recorded(attendance_record):
    """Retard constaté → parents (notification moins urgente qu'une absence)."""
    student = attendance_record.student
    session = attendance_record.attendance_session.session
    date_str = str(attendance_record.attendance_session.date)
    subject_name = session.subject.name if session and session.subject else 'cours'

    for parent_user in _get_student_parents(student):
        n = Notification.send(
            recipient=parent_user,
            notification_type='ATTENDANCE',
            priority='NORMAL',
            title='Retard signalé',
            message=(
                f'{student.user.full_name} est arrivé(e) en retard '
                f'en {subject_name} le {date_str}.'
            ),
            data={
                'student_id': str(student.id),
                'session_id': str(session.id),
                'date': date_str,
                'status': 'LATE',
            },
        )
        dispatch_notification(n)


def notify_absence_planned(absence_request):
    """H2: Absence prévue (motif) → administration."""
    from apps.accounts.models import User

    student  = absence_request.student
    start    = str(absence_request.start_date)
    end      = str(absence_request.end_date)
    reason   = absence_request.reason or ''

    admins = User.objects.filter(
        is_active=True,
        roles__name__in=['ADMIN', 'DIRECTOR'],
    ).distinct()

    for admin in admins:
        n = Notification.send(
            recipient=admin,
            notification_type='ABSENCE',
            priority='NORMAL',
            title='Absence prévue soumise',
            message=(
                f'{student.user.full_name} a déclaré une absence du {start} au {end}. '
                f'Motif : {reason or "non précisé"}'
            ),
            data={
                'student_id': str(student.id),
                'absence_request_id': str(absence_request.id),
                'start_date': start,
                'end_date': end,
            },
        )
        dispatch_notification(n, channels=['IN_APP'])


def notify_cash_deposit(transaction):
    """H2: Versement caisse/mobile money → finance + compta."""
    from apps.accounts.models import User

    amount   = transaction.amount
    tx_type  = getattr(transaction, 'transaction_type', 'DEPOSIT')
    label    = 'Mobile Money' if 'mobile' in tx_type.lower() else 'Versement caisse'

    finance_and_accounting = User.objects.filter(
        is_active=True,
        roles__name__in=['FINANCE', 'ACCOUNTING', 'ADMIN'],
    ).distinct()

    for user in finance_and_accounting:
        n = Notification.send(
            recipient=user,
            notification_type='FINANCE',
            priority='HIGH',
            title=f'{label} enregistré',
            message=f'{label} de {amount} FCFA enregistré.',
            data={
                'transaction_id': str(transaction.id),
                'amount': str(amount),
                'type': tx_type,
            },
        )
        dispatch_notification(n, channels=['IN_APP', 'EMAIL'])


def notify_assignment_published(assignment):
    """Notify students about new assignment."""
    from apps.academic.models import Enrollment

    enrollments = Enrollment.objects.filter(
        class_obj=assignment.class_obj, is_active=True, status='ENROLLED'
    ).select_related('student__user')

    for enrollment in enrollments:
        n = Notification.send(
            recipient=enrollment.student.user,
            notification_type='ASSIGNMENT',
            title='Nouveau devoir',
            message=f'Nouveau devoir "{assignment.title}" en {assignment.subject.name}.',
            data={'assignment_id': str(assignment.id)},
            action_url=f'/assignments/{assignment.id}',
        )
        dispatch_notification(n)


def notify_assignment_graded(correction):
    """Notify student and parents about graded assignment."""
    submission = correction.submission
    student    = submission.student
    assignment = submission.assignment

    n = Notification.send(
        recipient=student.user,
        notification_type='GRADE',
        title='Devoir corrigé',
        message=f'"{assignment.title}" corrigé – Note : {correction.score}/{assignment.max_score}.',
        data={
            'assignment_id': str(assignment.id),
            'submission_id': str(submission.id),
            'score': str(correction.score),
        },
        action_url=f'/submissions/{submission.id}',
    )
    dispatch_notification(n)

    for parent_user in _get_student_parents(student):
        n = Notification.send(
            recipient=parent_user,
            notification_type='GRADE',
            title='Devoir corrigé',
            message=(
                f'{student.user.full_name} a reçu {correction.score}/{assignment.max_score} '
                f'pour "{assignment.title}".'
            ),
            data={'student_id': str(student.id), 'assignment_id': str(assignment.id)},
        )
        dispatch_notification(n)


# ──────────────────────────────────────────────────────────────
# Auto-retry helper (called by Celery periodic task)
# ──────────────────────────────────────────────────────────────

def retry_failed_logs():
    """
    Pick up RETRYING logs whose next_retry_at is due and re-dispatch.
    Returns count of logs attempted.
    """
    now = timezone.now()
    due = NotificationLog.objects.filter(
        status='RETRYING',
        next_retry_at__lte=now,
    ).select_related('notification__recipient')

    count = 0
    for log in due:
        notification = log.notification
        log.status = 'PENDING'
        log.save(update_fields=['status'])

        if log.channel == 'EMAIL':
            _send_email(notification, log)
        elif log.channel == 'SMS':
            try:
                phone = notification.recipient.notification_preferences.phone_number
            except Exception:
                phone = ''
            if phone:
                _send_sms(notification, log, phone)
            else:
                log.mark_failed('Numéro introuvable (retry)')
        elif log.channel == 'WHATSAPP':
            try:
                wa = notification.recipient.notification_preferences.whatsapp_number
            except Exception:
                wa = ''
            if wa:
                _send_whatsapp(notification, log, wa)
            else:
                log.mark_failed('Numéro WA introuvable (retry)')

        count += 1

    return count


# kept for backward-compat
send_realtime_notification = _send_websocket
