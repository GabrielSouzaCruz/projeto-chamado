# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView, TemplateView

from tickets.health import health_check_view

urlpatterns = [
    # Admin do Django
    path('admin/', admin.site.urls),

    # Health check (público, para serviços externos como UptimeRobot)
    path('health/', health_check_view, name='health_check'),

    # Página Offline (servida pelo Service Worker quando não há rede)
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),

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

# =============================================================================
# Media files (anexos) — servidos pelo próprio Django, em DEV e PROD.
# O Render (Free Tier) roda WSGI puro, sem Nginx/cache para o /media/: o Django
# serve direto de MEDIA_ROOT. Os anexos são apenas PDFs/imagens pequenos com
# upload limitado (DATA_UPLOAD_MAX_MEMORY_SIZE).
#
# Obs.: com STORAGES["default"] = Cloudinary, anexos novos apontam para a CDN
# (res.cloudinary.com). Esta rota garante acesso aos arquivos locais/legados
# que ainda existam em MEDIA_ROOT e é o fallback quando Cloudinary não estiver
# ativo (sem CLOUDINARY_URL), onde a mídia volta para o disco local.
# =============================================================================
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)