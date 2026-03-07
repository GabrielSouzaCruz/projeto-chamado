# tickets/urls.py

from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # =============================================================================
    # DASHBOARD E PRINCIPAL
    # =============================================================================
    path('', views.dashboard, name='dashboard'),
    path('novo/', views.TicketCreateView.as_view(), name='create'),
    path('historico/', views.historico_tickets, name='historico'),
    
    # =============================================================================
    # APIs PARA POLLING EM TEMPO REAL
    # =============================================================================
    path('api/check-novos/', views.check_novos_tickets, name='check_novos'),
    path('api/dashboard/', views.api_dashboard_update, name='api_dashboard_update'),
    path('api/fila-admin/', views.api_fila_admin_update, name='api_fila_admin_update'),
    
    # =============================================================================
    # APIs DE TICKET (DEVEM VIR ANTES DE <int:pk>/!)
    # =============================================================================
    path('api/tickets/<int:ticket_id>/comentarios/', views.api_comentarios_update, name='api_comentarios_update'),
    path('api/tickets/<int:pk>/detail-ajax/', views.ticket_detail_ajax, name='ticket_detail_ajax'),
    
    # =============================================================================
    # TICKET: DETALHES E AÇÕES (DEPOIS DAS APIs)
    # =============================================================================
    path('<int:pk>/', views.TicketDetailView.as_view(), name='detail'),
    path('<int:pk>/comentar/', views.adicionar_comentario, name='add_comment'),
    path('<int:pk>/assumir/', views.assumir_ticket, name='take'),
    path('<int:pk>/status/', views.alterar_status, name='change_status'),
    path('<int:pk>/editar/', views.TicketUpdateView.as_view(), name='update'),
    path('<int:pk>/cancelar/', views.cancelar_ticket, name='cancelar'),
    
    # =============================================================================
    # CATEGORIAS
    # =============================================================================
    path('categorias/nova/', views.CategoriaCreateView.as_view(), name='categoria_create'),
    path('categorias/<int:pk>/editar/', views.CategoriaUpdateView.as_view(), name='categoria_update'),
    path('categorias/', views.lista_categorias, name='categorias'),
    
    # =============================================================================
    # FILA ADMIN
    # =============================================================================
    path('fila-admin/', views.fila_admin, name='fila_admin'),
]