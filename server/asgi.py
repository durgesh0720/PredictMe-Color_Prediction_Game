import os
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.sessions import SessionMiddlewareStack
from django.core.asgi import get_asgi_application

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from polling.routing import websocket_urlpatterns
from polling.websocket_auth import WebSocketAuthMiddleware, WebSocketRateLimitMiddleware, WebSocketSecurityMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": SessionMiddlewareStack(
            AllowedHostsOriginValidator(
                WebSocketSecurityMiddleware(
                    WebSocketRateLimitMiddleware(
                        WebSocketAuthMiddleware(
                            URLRouter(websocket_urlpatterns)
                        )
                    )
                )
            )
        ),
    }
)