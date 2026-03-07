# accounts/decorators.py
"""
Decorators de autorização para function-based views.

Decorators disponíveis:
- tecnico_required: Restringe acesso a usuários is_technician=True
- admin_required: Restringe acesso a superusers (admins do Django)
- usuario_proprio_or_tecnico: Permite proprietário OU técnico

Uso em views:
    @tecnico_required
    def minha_view(request):
        ...

    @admin_required
    def fila_admin(request):
        ...

⚠️ IMPORTANTE - Ordem dos decorators:
    ✅ CORRETO: @login_required → @wraps → def wrapper
    (login primeiro, depois permissão específica)
    
    Para class-based views, use mixins (accounts/mixins.py) em vez de decorators.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect


# =============================================================================
# TÉCNICO
# =============================================================================

def tecnico_required(view_func):
    """
    Decorator que restringe acesso a usuários com is_technician=True.
    
    Verificações (em ordem):
    1. Usuário está autenticado? (login_required)
    2. Usuário é técnico? (is_technician == True)
    
    Se falhar:
    - Redireciona para dashboard
    - Exibe mensagem de erro informativa
    
    Uso:
        @tecnico_required
        def assumir_ticket(request, pk):
            # Apenas técnicos chegam aqui
            ...
    
    ⚠️ Para class-based views, use TecnicoRequiredMixin (mixins.py):
        class MinhaView(TecnicoRequiredMixin, View):
            ...
    
    Segurança:
    - Não expõe informações sobre o recurso protegido
    - Mensagem genérica para não vazar existência de recursos
    """
    
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_technician:
            messages.error(request, 'Acesso restrito a técnicos de TI.')
            return redirect('tickets:dashboard')
        return view_func(request, *args, **kwargs)
    
    return wrapper


# =============================================================================
# ADMIN (SUPERUSER)
# =============================================================================

def admin_required(view_func):
    """
    Decorator que restringe acesso a superusers (admins do Django).
    
    Verificações:
    1. Usuário está autenticado?
    2. Usuário é ativo? (is_active == True)
    3. Usuário é superuser? (is_superuser == True)
    
    Se falhar:
    - Redireciona para login (não para dashboard)
    - Sem mensagem (user_passes_test não suporta messages)
    
    Uso:
        @admin_required
        def fila_admin(request):
            # Apenas superusers chegam aqui
            ...
    
    Diferença para tecnico_required:
    - tecnico_required: is_technician (técnicos de TI)
    - admin_required: is_superuser (admins do Django)
    
    Um usuário pode ser:
    - Técnico mas não admin: is_technician=True, is_superuser=False
    - Admin mas não técnico: is_technician=False, is_superuser=True
    - Ambos: is_technician=True, is_superuser=True
    - Nenhum: is_technician=False, is_superuser=False
    
    ⚠️ Para class-based views, use @method_decorator:
        from django.utils.decorators import method_decorator
        
        @method_decorator(admin_required, name='dispatch')
        class MinhaView(View):
            ...
    """
    
    test_decorator = user_passes_test(
        lambda u: u.is_active and u.is_superuser,
        login_url='accounts:login',
        redirect_field_name=None
    )
    
    return test_decorator(view_func)


# =============================================================================
# PROPRIETÁRIO OU TÉCNICO
# =============================================================================

def usuario_proprio_or_tecnico(view_func):
    """
    Decorator que permite acesso se:
    - Usuário é técnico (is_technician=True), OU
    - Usuário é proprietário do recurso (solicitante do ticket)
    
    Verificações (em ordem):
    1. Usuário está autenticado? (login_required)
    2. Usuário é técnico? → Permite acesso
    3. Usuário é proprietário do ticket? → Permite acesso
    4. Caso contrário → Negado
    
    Requer:
    - View deve receber parâmetro 'pk' ou 'ticket_id' na URL
    - Modelo Ticket deve estar disponível
    
    Uso:
        @usuario_proprio_or_tecnico
        def detalhe_ticket(request, pk):
            # Técnico OU solicitante chegam aqui
            ...
    
    ⚠️ LIMITAÇÕES:
    - Só funciona com tickets (import hardcoded de Ticket)
    - Para outros modelos, crie decorator específico
    - Para class-based views, use ProprietarioOrTecnicoMixin (mixins.py)
    
    Segurança:
    - Verifica ownership antes de permitir acesso
    - Técnicos têm acesso universal (para atendimento)
    - Usuários comuns só acessam seus próprios tickets
    """
    
    # Import local para evitar circular import
    from tickets.models import Ticket
    
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # ✅ Técnicos têm acesso total
        if request.user.is_technician:
            return view_func(request, *args, **kwargs)
        
        # 🔍 Verifica se usuário é proprietário do ticket
        ticket_id = kwargs.get('pk') or kwargs.get('ticket_id')
        
        if ticket_id:
            try:
                ticket = Ticket.objects.get(pk=ticket_id)
                if ticket.solicitante == request.user:
                    return view_func(request, *args, **kwargs)
            except Ticket.DoesNotExist:
                # Ticket não existe - deixa a view lidar com 404
                pass
        
        # ❌ Acesso negado
        messages.error(request, 'Você não tem permissão para acessar este recurso.')
        return redirect('tickets:dashboard')
    
    return wrapper