# tickets/urls.py

from django.urls import path

from . import views


app_name = 'tickets'


urlpatterns = [

    path('', views.dashboard, name='dashboard'),

    path('novo/', views.TicketCreateView.as_view(), name='create'),

    path('<int:pk>/', views.TicketDetailView.as_view(), name='detail'),

    path('<int:pk>/comentar/', views.adicionar_comentario, name='add_comment'),

    path('<int:pk>/assumir/', views.assumir_ticket, name='take'),

    path('<int:pk>/status/', views.alterar_status, name='change_status'),

    path('<int:pk>/editar/', views.TicketUpdateView.as_view(), name='update'),
    path('categorias/', views.lista_categorias, name='categorias'),

    path('categorias/nova/', views.CategoriaCreateView.as_view(), name='categoria_create'),

    path('categorias/<int:pk>/editar/', views.CategoriaUpdateView.as_view(), name='categoria_update'),

]