# accounts/mixins.py
"""
Mixins de autenticação e autorização para class-based views.

Mixins disponíveis:
- TecnicoRequiredMixin: Restringe acesso a usuários is_technician=True
- ProprietarioOrTecnicoMixin: Permite acesso ao proprietário do objeto OU técnico

Uso em views:
    class MinhaView(TecnicoRequiredMixin, View):
        ...

    class MinhaView(ProprietarioOrTecnicoMixin, DetailView):
        ...

⚠️ Ordem de importação importa! Mixins devem vir ANTES da view base:
    ✅ CORRETO: class MinhaView(TecnicoRequiredMixin, DetailView)
    ❌ ERRADO: class MinhaView(DetailView, TecnicoRequiredMixin)
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin


class TecnicoRequiredMixin(LoginRequiredMixin):
    """
    Mixin que restringe acesso a usuários com is_technician=True.
    
    Herda de LoginRequiredMixin, então:
    1. Primeiro verifica se usuário está logado (LoginRequiredMixin)
    2. Depois verifica se é técnico (este mixin)
    
    Uso:
        class FilaAdminView(TecnicoRequiredMixin, View):
            def get(self, request):
                # Apenas técnicos chegam aqui
                ...
    
    Segurança:
    - Redireciona para dashboard se não for técnico
    - Exibe mensagem de erro informativa
    - Não expõe informações sobre o recurso protegido
    
    ⚠️ IMPORTANTE: Este mixin deve vir PRIMEIRO na herança:
        ✅ CORRETO: class View(TecnicoRequiredMixin, DetailView)
        ❌ ERRADO: class View(DetailView, TecnicoRequiredMixin)
    
    Por que a ordem importa?
    - Python executa MRO (Method Resolution Order) da esquerda para direita
    - Se DetailView vier primeiro, o dispatch() dele pode rodar antes do check
    """
    
    def dispatch(self, request, *args, **kwargs):
        """
        Verifica permissão de técnico antes de processar a requisição.
        
        Fluxo:
        1. LoginRequiredMixin verifica se usuário está autenticado
        2. Este mixin verifica se user.is_technician == True
        3. Se passar, continua para a view
        4. Se falhar, redireciona com mensagem de erro
        
        Args:
            request: Request do Django
            *args, **kwargs: Argumentos da URL
            
        Returns:
            Response da view ou redirect para dashboard
        """
        # LoginRequiredMixin já garantiu que user.is_authenticated == True
        
        if not request.user.is_technician:
            messages.error(request, 'Acesso restrito a técnicos de TI.')
            return redirect('tickets:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class ProprietarioOrTecnicoMixin(LoginRequiredMixin):
    """
    Mixin que permite acesso ao proprietário do objeto OU a técnicos.
    
    Regra de acesso:
    - ✅ Técnicos (is_technician=True) podem acessar qualquer objeto
    - ✅ Proprietário (solicitante ou autor) pode acessar seu próprio objeto
    - ❌ Outros usuários são bloqueados
    
    Uso:
        class TicketDetailView(ProprietarioOrTecnicoMixin, DetailView):
            model = Ticket
            
        class ComentarioUpdateView(ProprietarioOrTecnicoMixin, UpdateView):
            model = Comentario
    
    Segurança:
    - Verifica ownership antes de permitir acesso
    - Suporta objetos com atributo 'solicitante' (Ticket) ou 'autor' (Comentario)
    - Redireciona com mensagem de erro se não tiver permissão
    
    ⚠️ IMPORTANTE: Este mixin assume que a view tem get_object()
    - Funciona com: DetailView, UpdateView, DeleteView
    - NÃO funciona com: View, TemplateView (não têm get_object)
    
    Para views sem get_object(), use @login_required + verificação manual no dispatch
    """
    
    def dispatch(self, request, *args, **kwargs):
        """
        Verifica permissão de ownership antes de processar a requisição.
        
        Fluxo:
        1. LoginRequiredMixin verifica se usuário está autenticado
        2. Se for técnico, permite acesso imediato
        3. Se não for técnico, verifica se é proprietário do objeto
        4. Se for proprietário, permite acesso
        5. Caso contrário, bloqueia com mensagem de erro
        
        Args:
            request: Request do Django
            *args, **kwargs: Argumentos da URL
            
        Returns:
            Response da view ou redirect para dashboard
            
        Raises:
            AttributeError: Se a view não tiver método get_object()
        """
        # LoginRequiredMixin já garantiu que user.is_authenticated == True
        
        # ✅ Técnicos podem acessar qualquer objeto
        if request.user.is_technician:
            return super().dispatch(request, *args, **kwargs)
        
        # ⚠️ Para usuários comuns, verificar ownership
        try:
            obj = self.get_object()
        except AttributeError:
            # View não tem get_object() (ex: View, TemplateView)
            # Neste caso, nega acesso por segurança
            messages.error(request, 'Você não tem permissão para acessar este recurso.')
            return redirect('tickets:dashboard')
        except Exception:
            # Objeto não existe ou outro erro
            # Deixa a view original lidar com 404
            return super().dispatch(request, *args, **kwargs)
        
        # ✅ Verifica se usuário é o proprietário (solicitante ou autor)
        if hasattr(obj, 'solicitante') and obj.solicitante == request.user:
            return super().dispatch(request, *args, **kwargs)
        
        if hasattr(obj, 'autor') and obj.autor == request.user:
            return super().dispatch(request, *args, **kwargs)
        
        # ❌ Acesso negado
        messages.error(request, 'Você não tem permissão para acessar este recurso.')
        return redirect('tickets:dashboard')