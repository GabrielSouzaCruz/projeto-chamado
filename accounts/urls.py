# accounts/urls.py
"""
URLs do app accounts (autenticação e gerenciamento de usuários).

Namespace: 'accounts'

Rotas disponíveis:
- login/       : Autenticação de usuários
- logout/      : Encerramento de sessão
- register/    : Registro de novos usuários
- profile/     : Visualização e edição de perfil
- alterar-senha/ : Troca de senha

Exemplo de uso em templates:
{% url 'accounts:login' %}
{% url 'accounts:profile' %}
"""

from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # =============================================================================
    # AUTENTICAÇÃO
    # =============================================================================
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # =============================================================================
    # REGISTRO
    # =============================================================================
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # =============================================================================
    # PERFIL E SENHA
    # =============================================================================
    path('profile/', views.ProfileUpdateView.as_view(), name='profile'),
    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),
]