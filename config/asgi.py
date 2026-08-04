import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# Inicia o Django HTTP normal
django_asgi_app = get_asgi_application()

# Importações do Channels devem vir DEPOIS do setup do Django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from tickets.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # Requisições HTTP normais vão para as views do Django
    "http": django_asgi_app,
    
    # Requisições WebSocket (ws://) vão para o Channels
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})