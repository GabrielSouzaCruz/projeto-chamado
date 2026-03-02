# accounts/urls.py (versão completa atualizada)

from django.urls import path

from . import views

 

app_name = 'accounts'

 

urlpatterns = [

    path('login/', views.CustomLoginView.as_view(), name='login'),

    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    path('register/', views.RegisterView.as_view(), name='register'),

    path('profile/', views.ProfileUpdateView.as_view(), name='profile'),

    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),

]