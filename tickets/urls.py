# tickets/urls.py
from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # 1. ROTAS FIXAS (DEVE VIR PRIMEIRO)
    path('', views.dashboard, name='dashboard'),
    path('novo/', views.TicketCreateView.as_view(), name='create'),
    path('historico/', views.historico, name='historico'),
    path('categorias/', views.lista_categorias, name='categorias'),
    path('categorias/nova/', views.CategoriaCreateView.as_view(), name='categoria_create'),
    path('categorias/<int:pk>/editar/', views.CategoriaUpdateView.as_view(), name='categoria_update'),
    path('categorias/<int:pk>/deletar/', views.CategoriaDeleteView.as_view(), name='categoria_delete'),
    path('fila-admin/', views.fila_admin, name='fila_admin'), # <--- Fixa e bem definida

    # 2. APIs (PREFIXADAS PARA NÃO CONFUNDIR)
    path('api/check-novos/', views.check_novos_tickets, name='check_novos'),
    path('api/dashboard/', views.api_dashboard_update, name='api_dashboard_update'),
    path('api/fila-admin/', views.api_fila_admin_update, name='api_fila_admin_update'),
    path('api/comentarios/<int:ticket_id>/', views.api_comentarios_update, name='api_comentarios_update'),
    
    # 3. ROTAS COM ID (SEMELHANTES DEVEM FICAR JUNTAS NO FINAL)
    path('<int:pk>/', views.TicketDetailView.as_view(), name='detail'),
    path('<int:pk>/comentar/', views.adicionar_comentario, name='add_comment'),
    path('<int:pk>/assumir/', views.assumir_ticket, name='take'),
    path('<int:pk>/status/', views.alterar_status, name='change_status'),
    path('<int:pk>/editar/', views.TicketUpdateView.as_view(), name='update'),
    path('<int:pk>/cancelar/', views.cancelar_ticket, name='cancelar'),
]