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
    Returns (success_count, list_of_failed_items).
    channel_id: Android notification channel ('payments', 'attendance', 'default').
    """
    valid = [t for t in tokens if _is_expo_token(t)]
    if not valid:
        return 0, []

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
        success = 0
        for item in result.get('data', []):
            if item.get('status') == 'ok':
                success += 1
            else:
                logger.warning("Expo push ticket failed: %s", item)
                failed.append(item)

        return success, failed

    except Exception as exc:
        logger.error("Expo push request failed: %s", exc)
        return 0, []


GENERIC_LOGGED_OUT_TITLE = 'Nouvelle notification'
GENERIC_LOGGED_OUT_BODY = (
    "Vous avez une nouvelle notification importante. "
    "Ouvrez l'application et connectez-vous pour la consulter."
)


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
    for an account nobody is currently signed into on that device."""
    logged_in_tokens, logged_out_tokens = get_user_expo_tokens(user)

    total_success = 0
    all_failed = []

    if logged_in_tokens:
        success, failed = send_expo_push(logged_in_tokens, title, body, data=data, channel_id=channel_id)
        total_success += success
        all_failed += failed

    if logged_out_tokens:
        success, failed = send_expo_push(
            logged_out_tokens, GENERIC_LOGGED_OUT_TITLE, GENERIC_LOGGED_OUT_BODY,
            data={}, channel_id=channel_id,
        )
        total_success += success
        all_failed += failed

    return total_success, all_failed
