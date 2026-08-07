# accounts/views.py
"""
Views de autenticação e gerenciamento de usuários.

Inclui:
- Login/Logout customizados
- Registro de novos usuários
- Atualização de perfil
- Alteração de senha

Nota: Registro é aberto (sem aprovação). Para produção com controle,
implemente aprovação via admin.
"""

import logging

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from tickets.models import Ticket

from .forms import LoginForm, UserRegistrationForm, ProfileUpdateForm
from .models import User

# Logger do app accounts: ações sensíveis de segurança (configurado no LOGGING
# de config/settings.py com nível INFO e saída para o console/stdout).
logger = logging.getLogger('accounts')


# =============================================================================
# LOGIN / LOGOUT
# =============================================================================

# Rate limiting anti força-bruta no login
MAX_TENTATIVAS_LOGIN = 10
TEMPO_BLOQUEIO_LOGIN = 600  # 10 minutos em segundos
CACHE_KEY_PREFIX = 'login_falhas_'

def get_client_ip(request):
    """
    Captura o IP real do cliente considerando proxies (Render/nginx/gunicorn).
    HTTP_X_FORWARDED_FOR pode vir com vários IPs: 'ip_cliente, proxy1, proxy2'
    — retorna sempre o primeiro (o IP original do cliente).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def _cache_key(ip):
    """Gera a chave do cache para um IP."""
    return f'{CACHE_KEY_PREFIX}{ip}'

class CustomLoginView(SuccessMessageMixin, LoginView):
    """
    View de login personalizada com Bootstrap e mensagens de sucesso.
    
    Segurança:
    - Redirect de usuários já autenticados (evita loop)
    - CSRF protegido pelo Django
    - Rate limiting anti força-bruta via cache (por IP, 10 tentativas / 10 min)
    """
    
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True
    success_message = 'Bem-vindo(a), %(username)s!'
    
    def get_success_url(self):
        """Redireciona para dashboard após login bem-sucedido."""
        return reverse_lazy('tickets:dashboard')

    def form_valid(self, form):
        """Login OK → zera o contador de falhas do IP."""
        cache.delete(_cache_key(get_client_ip(self.request)))
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Credenciais inválidas → incrementa o contador e mostra quantas
        tentativas restam antes do bloqueio.
        """
        ip = get_client_ip(self.request)
        chave = _cache_key(ip)
        tentativas = cache.get(chave, 0) + 1
        cache.set(chave, tentativas, TEMPO_BLOQUEIO_LOGIN)

        restantes = MAX_TENTATIVAS_LOGIN - tentativas
        if restantes > 0:
            logger.warning(
                'Falha de login - IP %s: tentativa %s/%s (restantes: %s)',
                ip, tentativas, MAX_TENTATIVAS_LOGIN, restantes,
            )
            form.add_error(
                None,
                f'Credenciais inválidas. Você tem mais {restantes} tentativa(s) antes do bloqueio.'
            )
        else:
            logger.warning(
                'IP %s BLOQUEADO por força bruta após %s tentativas de login falhas '
                '(bloqueio de %ss)',
                ip, tentativas, TEMPO_BLOQUEIO_LOGIN,
            )
            form.add_error(
                None,
                'Muitas tentativas falhas. Por segurança, seu IP foi bloqueado por 10 minutos.'
            )
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        """
        Antes de processar o formulário, verifica se o IP já está bloqueado.
        Se atingiu o limite, NÃO processa o login e retorna erro bloqueante
        (sem incrementar o contador novamente).
        """
        ip = get_client_ip(request)
        tentativas = cache.get(_cache_key(ip), 0)
        if tentativas >= MAX_TENTATIVAS_LOGIN:
            logger.warning(
                'IP %s bloqueado - nova tentativa de login recusada '
                '(contador atual: %s, bloqueio de %ss)',
                ip, tentativas, TEMPO_BLOQUEIO_LOGIN,
            )
            form = self.get_form()
            form.add_error(
                None,
                'Muitas tentativas falhas. Por segurança, seu IP foi bloqueado por 10 minutos.'
            )
            return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)


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
    - Login automático após registro
    - Para produção com controle, considere:
      1. Aprovação via admin (is_active=False até aprovar)
      2. Whitelist de domínios corporativos
    
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