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


def get_user_expo_tokens(user):
    """Return all active Expo push tokens for a user."""
    from .models import DeviceToken
    return list(
        DeviceToken.objects.filter(user=user, is_active=True, platform='EXPO')
        .values_list('token', flat=True)
    )


def push_to_user(user, title, body, data=None, channel_id=None):
    """High-level helper: push to all active devices of a user."""
    tokens = get_user_expo_tokens(user)
    if tokens:
        return send_expo_push(tokens, title, body, data=data, channel_id=channel_id)
    return 0, []
