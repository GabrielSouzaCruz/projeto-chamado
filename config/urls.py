# config/urls.py

from pathlib import Path

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.generic.base import RedirectView, TemplateView

from tickets.health import health_check_view
from tickets.api import salvar_push_subscription


def service_worker(request):
    """Serve o Service Worker a partir do scope raiz (/ — sem prefixo).

    Porquê: registado em /static/sw.js, o scope ficaria em /static/ e as páginas
    da app (/tickets/...) nunca seriam controladas pelo SW — o que impedia o
    pushManager.subscribe (navigator.serviceWorker.ready nunca resolvia) e o
    fallback offline. O header Service-Worker-Allowed liberta o scope '/' a um
    script que não vive na raiz, e sem cache permite que novas versões do sw.js
    sejam detetadas imediatamente.
    """
    caminho = Path(settings.BASE_DIR) / 'static' / 'sw.js'
    try:
        conteudo = caminho.read_bytes()
    except (OSError, FileNotFoundError):
        return HttpResponse('Not Found', status=404)
    resp = HttpResponse(conteudo, content_type='application/javascript; charset=utf-8')
    resp['Service-Worker-Allowed'] = '/'
    resp['Cache-Control'] = 'no-cache'
    return resp

urlpatterns = [
    # Admin do Django
    path('admin/', admin.site.urls),

    # Health check (público, para serviços externos como UptimeRobot)
    path('health/', health_check_view, name='health_check'),

    # Web Push nativo (VAPID): salva a inscrição pushManager do navegador
    path('api/save-push-subscription/', salvar_push_subscription, name='save_push_subscription'),

    # Service Worker (scope raiz): necessário para push nativo + offline
    path('sw.js', service_worker, name='service_worker'),

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