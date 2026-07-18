"""
Expo Push Notification sender.
Calls the Expo push API to deliver native notifications to mobile devices.
Tokens must start with 'ExponentPushToken[' or 'ExpoPushToken['.
"""
import logging
import requests

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'


def _is_expo_token(token):
    return token and (
        token.startswith('ExponentPushToken[') or
        token.startswith('ExpoPushToken[')
    )


def send_expo_push(tokens, title, body, data=None, sound='default', badge=1, channel_id=None):
    """
    Send push to a list of Expo tokens.
    Returns (success_count, list_of_failed_items, tickets).

    `tickets` is one entry per token attempted: {'token', 'ticket_id', 'ok', 'error'}.
    IMPORTANT: an 'ok' ticket only means Expo *accepted the request* — it does
    NOT mean Apple/Google actually delivered it to the device. Real delivery
    outcome (including things like an expired/misconfigured Android FCM
    credential, or a token Apple/Google now consider dead) only shows up a
    few minutes later via the receipt endpoint — see check_expo_receipts().
    Callers that need to know real delivery status must persist `ticket_id`
    and check receipts later; treating a ticket 'ok' as "delivered" is the
    exact bug that made push failures silent for closed/background apps.

    channel_id: Android notification channel ('payments', 'attendance', 'default').
    """
    valid = [t for t in tokens if _is_expo_token(t)]
    if not valid:
        return 0, [], []

    def _build_message(token):
        msg = {
            'to':    token,
            'title': title,
            'body':  body,
            'data':  data or {},
            'sound': sound,
            'badge': badge,
        }
        if channel_id:
            msg['channelId'] = channel_id
        return msg

    messages = [_build_message(t) for t in valid]

    try:
        resp = requests.post(
            EXPO_PUSH_URL,
            json=messages,
            headers={
                'Accept':           'application/json',
                'Accept-Encoding':  'gzip, deflate',
                'Content-Type':     'application/json',
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()

        failed = []
        tickets = []
        success = 0
        for token, item in zip(valid, result.get('data', [])):
            if item.get('status') == 'ok':
                success += 1
                tickets.append({'token': token, 'ticket_id': item.get('id'), 'ok': True})
            else:
                logger.warning("Expo push ticket failed: %s", item)
                failed.append(item)
                tickets.append({'token': token, 'ticket_id': None, 'ok': False, 'error': item})

        return success, failed, tickets

    except Exception as exc:
        logger.error("Expo push request failed: %s", exc)
        return 0, [], []


GENERIC_LOGGED_OUT_TITLE = 'Nouvelle notification'
GENERIC_LOGGED_OUT_BODY = (
    "Vous avez une nouvelle notification importante. "
    "Ouvrez l'application et connectez-vous pour la consulter."
)

# Per-category generic content for logged-out devices — names the topic so
# the notification isn't meaningless, but never the sensitive specifics
# (amount, child's name, etc.) that the real notification.data/title/body
# would carry. Falls back to the fully generic message above for any
# category not listed here.
GENERIC_LOGGED_OUT_BY_CATEGORY = {
    'echeancier_reminder': (
        'Échéancier de scolarité',
        "Notification scolarité ESCAM — une échéance de scolarité vous attend. "
        "Connectez-vous pour la consulter.",
    ),
}


def _logged_out_content(data):
    category = (data or {}).get('category')
    return GENERIC_LOGGED_OUT_BY_CATEGORY.get(category, (GENERIC_LOGGED_OUT_TITLE, GENERIC_LOGGED_OUT_BODY))


def get_user_expo_tokens(user):
    """Return (logged_in_tokens, logged_out_tokens) — both are still active
    (eligible for push), split by whether the user is currently logged out
    on that device. A logged-out device still gets pinged, just with a
    content-free message instead of the real one (see push_to_user)."""
    from .models import DeviceToken
    qs = DeviceToken.objects.filter(user=user, is_active=True, platform='EXPO')
    logged_in = list(qs.filter(is_logged_in=True).values_list('token', flat=True))
    logged_out = list(qs.filter(is_logged_in=False).values_list('token', flat=True))
    return logged_in, logged_out


def push_to_user(user, title, body, data=None, channel_id=None):
    """High-level helper: push to all active devices of a user — devices
    where the user is logged out get a generic, detail-free message instead
    of the real title/body/data, so nothing sensitive shows on a lock screen
    for an account nobody is currently signed into on that device.

    Returns (success_count, failed_items, tickets) — see send_expo_push for
    what `tickets` means and why it matters (ticket 'ok' != delivered)."""
    logged_in_tokens, logged_out_tokens = get_user_expo_tokens(user)

    total_success = 0
    all_failed = []
    all_tickets = []

    if logged_in_tokens:
        success, failed, tickets = send_expo_push(logged_in_tokens, title, body, data=data, channel_id=channel_id)
        total_success += success
        all_failed += failed
        all_tickets += tickets

    if logged_out_tokens:
        generic_title, generic_body = _logged_out_content(data)
        success, failed, tickets = send_expo_push(
            logged_out_tokens, generic_title, generic_body,
            data={}, channel_id=channel_id,
        )
        total_success += success
        all_failed += failed
        all_tickets += tickets

    return total_success, all_failed, all_tickets


# ──────────────────────────────────────────────────────────────
# Receipts — the actual delivery outcome, checked a few minutes after
# sending (Expo needs time to hear back from Apple/Google). Without this,
# a push whose ticket said 'ok' but that Apple/Google silently dropped
# (dead token, or — very commonly — a misconfigured/expired Android FCM
# credential) is indistinguishable from a real delivery: the log says
# SENT forever and nothing ever surfaces the real error.
# ──────────────────────────────────────────────────────────────

EXPO_RECEIPTS_URL = 'https://exp.host/--/api/v2/push/getReceipts'


def fetch_expo_receipts(ticket_ids):
    """Look up delivery receipts for a batch of Expo ticket ids.
    Returns {ticket_id: {'status': 'ok'|'error', 'message': str, 'details': dict}}.
    Expo caps getReceipts at ~1000 ids per request; callers should chunk.
    """
    if not ticket_ids:
        return {}
    try:
        resp = requests.post(
            EXPO_RECEIPTS_URL,
            json={'ids': ticket_ids},
            headers={
                'Accept':          'application/json',
                'Accept-Encoding': 'gzip, deflate',
                'Content-Type':    'application/json',
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get('data', {})
    except Exception as exc:
        logger.error("Expo getReceipts request failed: %s", exc)
        return {}


def check_expo_receipts():
    """Poll receipts for every PUSH NotificationLog still sitting on a
    ticket we haven't confirmed yet, update its real status, and deactivate
    any DeviceToken Expo reports as dead (DeviceNotRegistered) so future
    sends stop wasting a ticket on it. Meant to be called periodically by
    Celery (see apps.notifications.tasks.check_push_receipts), a few
    minutes after the corresponding sends — Expo receipts aren't available
    immediately.

    Returns dict with counts: {'checked', 'delivered', 'failed'}.
    """
    from django.utils import timezone
    from .models import NotificationLog, DeviceToken

    logs = list(NotificationLog.objects.filter(
        channel='PUSH', status='SENT', metadata__has_key='tickets',
    ).exclude(metadata__receipts_checked=True))

    all_ids = []
    for log in logs:
        for t in log.metadata.get('tickets', []):
            if t.get('ok') and t.get('ticket_id'):
                all_ids.append(t['ticket_id'])

    receipts = {}
    for i in range(0, len(all_ids), 300):
        receipts.update(fetch_expo_receipts(all_ids[i:i + 300]))

    delivered_count = 0
    failed_count = 0

    for log in logs:
        tickets = log.metadata.get('tickets', [])
        pending_ids = [t['ticket_id'] for t in tickets if t.get('ok') and t.get('ticket_id')]
        if not pending_ids:
            # Every token in this log already failed at ticket time — nothing to poll.
            log.metadata['receipts_checked'] = True
            log.save(update_fields=['metadata'])
            continue

        resolved = {tid: receipts[tid] for tid in pending_ids if tid in receipts}
        if len(resolved) < len(pending_ids):
            continue  # some receipts not ready yet — try again next run

        any_delivered = False
        errors = []
        for tid, receipt in resolved.items():
            if receipt.get('status') == 'ok':
                any_delivered = True
            else:
                error_code = (receipt.get('details') or {}).get('error')
                errors.append(f"{error_code or receipt.get('message')}")
                if error_code == 'DeviceNotRegistered':
                    dead_token = next((t['token'] for t in tickets if t.get('ticket_id') == tid), None)
                    if dead_token:
                        DeviceToken.objects.filter(token=dead_token).update(is_active=False)

        log.metadata['receipts_checked'] = True
        log.metadata['receipts'] = resolved
        if any_delivered:
            log.status = 'DELIVERED'
            log.delivered_at = timezone.now()
            log.save(update_fields=['metadata', 'status', 'delivered_at'])
            delivered_count += 1
        else:
            log.error_message = '; '.join(errors)[:500]
            log.status = 'FAILED'
            log.save(update_fields=['metadata', 'status', 'error_message'])
            failed_count += 1

    return {'checked': len(logs), 'delivered': delivered_count, 'failed': failed_count}
