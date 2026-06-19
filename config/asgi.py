"""
ASGI config for Campus Management System.
Supports HTTP and WebSocket protocols.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from apps.chat.routing import websocket_urlpatterns as chat_patterns
from apps.notifications.routing import websocket_urlpatterns as notification_patterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                chat_patterns + notification_patterns
            )
        )
    ),
})
