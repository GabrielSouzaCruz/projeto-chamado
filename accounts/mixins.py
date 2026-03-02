# accounts/mixins.py

from django.contrib import messages

from django.shortcuts import redirect

from django.contrib.auth.mixins import LoginRequiredMixin

 

class TecnicoRequiredMixin(LoginRequiredMixin):

    """Mixin que restringe acesso apenas a técnicos."""

    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_technician:

            messages.error(request, 'Acesso restrito a técnicos de TI.')

            return redirect('tickets:dashboard')

        return super().dispatch(request, *args, **kwargs)
    
class ProprietarioOrTecnicoMixin(LoginRequiredMixin):

    """Mixin que permite acesso ao proprietário ou técnico."""

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_technician:

            return super().dispatch(request, *args, **kwargs)

        

        obj = self.get_object()

        if hasattr(obj, 'solicitante') and obj.solicitante == request.user:

            return super().dispatch(request, *args, **kwargs)

        

        if hasattr(obj, 'autor') and obj.autor == request.user:

            return super().dispatch(request, *args, **kwargs)

        

        messages.error(request, 'Você não tem permissão para acessar este recurso.')

        return redirect('tickets:dashboard')