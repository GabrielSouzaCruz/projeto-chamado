# config/urls.py - VERSÃO ALTERNATIVA

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView  # ✅ Import alternativo

urlpatterns = [
    # Admin do Django
    path('admin/', admin.site.urls),
    
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

# Media files (apenas DEBUG)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)