# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.static import serve
from django.views.generic.base import RedirectView

from tickets.health import health_check_view

urlpatterns = [
    # Admin do Django
    path('admin/', admin.site.urls),

    # Health check (público, para serviços externos como UptimeRobot)
    path('health/', health_check_view, name='health_check'),

    # App de autenticação
    path('accounts/', include('accounts.urls')),

    # App de tickets (COM PREFIXO /tickets/)
    path('tickets/', include('tickets.urls')),

    # Redirect raiz para dashboard (usando RedirectView)
    path('', RedirectView.as_view(pattern_name='tickets:dashboard', permanent=False)),
]

# Error Handlers
handler404 = 'tickets.views.error_404'
handler500 = 'tickets.views.error_500'
handler403 = 'tickets.views.error_403'

# Media files: servidos em produção pelo Django.
# Como o Render (modo WSGI puro) não tem Nginx/cache para o /media/, o Django
# serve diretamente a partir de MEDIA_ROOT. Os anexos são apenas PDFs/imagens
# pequenos com upload limitado a 5MB (proteção via DATA_UPLOAD_MAX_MEMORY_SIZE).
urlpatterns += [
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
]