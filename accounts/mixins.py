from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin

class TecnicoRequiredMixin(LoginRequiredMixin):
    """Mixin que restringe o acesso apenas a utilizadores com is_technician=True."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not getattr(request.user, 'is_technician', False):
            messages.error(request, 'Acesso restrito a técnicos de TI.')
            return redirect('tickets:dashboard')
        return super().dispatch(request, *args, **kwargs)

class ProprietarioOrTecnicoMixin(LoginRequiredMixin):
    """Mixin que permite acesso ao dono do ticket, técnicos ou superusuários."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
    
    # TESTE AGRESSIVO: Se for superuser, ignora todo o resto e entra
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # Se for utilizador comum, verifica se é o dono
        try:
            # Importante: usamos o método da View para pegar o ticket atual
            obj = self.get_object()
            if hasattr(obj, 'solicitante') and obj.solicitante == request.user:
                return super().dispatch(request, *args, **kwargs)
        except Exception:
            # Se não conseguir pegar o objeto, por segurança, bloqueia
            pass

        messages.error(request, 'Não tem permissão para ver este chamado.')
        return redirect('tickets:dashboard')