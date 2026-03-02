# config/urls.py

from django.contrib import admin

from django.urls import path, include

from django.conf import settings

from django.conf.urls.static import static

 

urlpatterns = [

    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),

    path('', include('tickets.urls')),

]

# config/urls.py (adicionar ao final, antes do if settings.DEBUG)

 

# Páginas de erro customizadas

handler404 = 'tickets.views.page_not_found'

handler500 = 'tickets.views.server_error'

handler403 = 'tickets.views.permission_denied' 

# Servir arquivos de mídia em desenvolvimento

if settings.DEBUG:

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)