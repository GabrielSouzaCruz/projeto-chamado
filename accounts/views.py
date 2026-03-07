# accounts/views.py
"""
Views de autenticação e gerenciamento de usuários.

Inclui:
- Login/Logout customizados
- Registro de novos usuários
- Atualização de perfil
- Alteração de senha

Nota: Registro é aberto (sem aprovação). Para produção com controle,
implemente aprovação via admin ou verificação por e-mail.
"""

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from tickets.models import Ticket

from .forms import LoginForm, UserRegistrationForm, ProfileUpdateForm
from .models import User


# =============================================================================
# LOGIN / LOGOUT
# =============================================================================

class CustomLoginView(SuccessMessageMixin, LoginView):
    """
    View de login personalizada com Bootstrap e mensagens de sucesso.
    
    Segurança:
    - Redirect de usuários já autenticados (evita loop)
    - CSRF protegido pelo Django
    - Rate limiting deve ser configurado no nginx/gunicorn em produção
    """
    
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True
    success_message = 'Bem-vindo(a), %(username)s!'
    
    def get_success_url(self):
        """Redireciona para dashboard após login bem-sucedido."""
        return reverse_lazy('tickets:dashboard')


class CustomLogoutView(LogoutView):
    """
    View de logout.
    
    Limpa a sessão e redireciona para página de login.
    Em produção, configure SESSION_COOKIE_SECURE para invalidar cookie HTTPS.
    """
    
    next_page = reverse_lazy('accounts:login')


# =============================================================================
# REGISTRO
# =============================================================================

class RegisterView(SuccessMessageMixin, CreateView):
    """
    View para registro de novos usuários.
    
    ⚠️ ATENÇÃO (Segurança):
    - Registro é ABERTO (qualquer um pode criar conta)
    - Login automático após registro (sem verificação de e-mail)
    - Para produção com controle, considere:
      1. Aprovação via admin (is_active=False até aprovar)
      2. Verificação por e-mail (enviar token único)
      3. Whitelist de domínios corporativos
    
    Após registro:
    - Usuário é logado automaticamente
    - Redirecionado para dashboard
    - Pode abrir tickets imediatamente
    """
    
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('tickets:dashboard')
    success_message = 'Conta criada com sucesso! Você está logado.'
    
    def form_valid(self, form):
        """
        Salva o usuário e faz login automático.
        
        Por que login automático?
        - Melhor UX para sistemas internos
        - Evita etapa extra de login após registro
        - ⚠️ Em produção com verificação de e-mail, remova esta linha
        """
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


# =============================================================================
# PERFIL
# =============================================================================

class ProfileUpdateView(SuccessMessageMixin, UpdateView):
    """
    View para atualização de perfil do usuário logado.
    
    Recursos:
    - Usuário só pode editar seu próprio perfil (get_object = request.user)
    - Exibe estatísticas de tickets do usuário
    - Validação de e-mail único (via model)
    
    Segurança:
    - Login obrigatório (herdado de UpdateView + get_object)
    - CSRF protegido
    """
    
    model = User
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')
    success_message = 'Perfil atualizado com sucesso!'
    
    def get_object(self):
        """
        Retorna o usuário logado como objeto a ser editado.
        
        Isso garante que usuários só possam editar seu próprio perfil,
        não de outros usuários (segurança por design).
        """
        return self.request.user
    
    def get_context_data(self, **kwargs):
        """
        Adiciona estatísticas de tickets ao contexto do template.
        
        Stats incluídos:
        - total: Todos os tickets abertos pelo usuário
        - resolvidos: Tickets já finalizados
        - abertos: Tickets em andamento ou abertos
        """
        context = super().get_context_data(**kwargs)
        
        tickets_solicitados = Ticket.objects.filter(solicitante=self.request.user)
        
        context['stats'] = {
            'total': tickets_solicitados.count(),
            'resolvidos': tickets_solicitados.filter(status='resolvido').count(),
            'abertos': tickets_solicitados.filter(
                status__in=['aberto', 'em_andamento']
            ).count(),
        }
        
        return context


# =============================================================================
# SENHA
# =============================================================================

@login_required
def alterar_senha(request):
    """
    View para alteração de senha do usuário logado.
    
    Segurança:
    - Login obrigatório (@login_required)
    - Valida senha atual antes de permitir mudança
    - Atualiza hash da sessão para não deslogar (update_session_auth_hash)
    - Usa validadores de senha do Django (min_length, complexidade, etc.)
    
    Fluxo:
    1. GET: Exibe formulário
    2. POST: Valida senha atual + nova senha → salva → atualiza sessão
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Atualiza hash da sessão para manter usuário logado após mudar senha
            update_session_auth_hash(request, user)
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/alterar_senha.html', {'form': form})