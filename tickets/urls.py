# tickets/urls.py
from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # 1. ROTAS PRINCIPAIS
    path('', views.dashboard, name='dashboard'),
    path('historico/', views.historico, name='historico'),
    path('fila-admin/', views.fila_admin, name='fila_admin'),
    
    # 2. CRUD DE CHAMADOS (TICKETS) - Nomes padronizados!
    path('novo/', views.TicketCreateView.as_view(), name='create'), 
    path('<int:pk>/', views.TicketDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.TicketUpdateView.as_view(), name='update'),
    path('<int:pk>/comentar/', views.adicionar_comentario, name='add_comment'),
    path('<int:pk>/assumir/', views.assumir_ticket, name='take'),
    path('<int:pk>/status/', views.alterar_status, name='change_status'),
    path('<int:pk>/cancelar/', views.cancelar_ticket, name='cancelar'),
    path('<int:pk>/apagar/', views.apagar_ticket, name='apagar'),

    # 3. ROTAS DE API (ESSENCIAIS PARA O WEBSOCKET E JAVASCRIPT)
    path('api/dashboard/', views.api_dashboard_update, name='api_dashboard_update'),
    path('api/fila-admin/', views.api_fila_admin_update, name='api_fila_admin_update'),
    path('api/comentarios/<int:ticket_id>/', views.api_comentarios_update, name='api_comentarios_update'),

    # 4. CRUD DE CATEGORIAS
    path('categorias/', views.lista_categorias, name='categorias'),
    path('categorias/nova/', views.CategoriaCreateView.as_view(), name='categoria_create'),
    path('categorias/<int:pk>/editar/', views.CategoriaUpdateView.as_view(), name='categoria_update'),
    path('categorias/<int:pk>/deletar/', views.CategoriaDeleteView.as_view(), name='categoria_delete'),
]