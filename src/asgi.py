"""
ASGI config for secure ATCS project.
Supports both HTTP and WebSocket protocols.
"""
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from boom_gate.routing import websocket_urlpatterns

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

# Django ASGI application
django_asgi_app = get_asgi_application()

# ASGI application with routing
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
