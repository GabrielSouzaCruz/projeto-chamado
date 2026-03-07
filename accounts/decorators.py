from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.http import JsonResponse # Importante para as APIs

def tecnico_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Permite se for técnico OU superusuário
        if request.user.is_technician or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Se for uma requisição AJAX/API, retorna JSON em vez de redirecionar
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/tickets/api/'):
            return JsonResponse({'error': 'Acesso restrito a técnicos.'}, status=403)

        messages.error(request, 'Acesso restrito a técnicos de TI.')
        return redirect('tickets:dashboard')
    return wrapper

def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_active and request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/tickets/api/'):
            return JsonResponse({'error': 'Acesso restrito a administradores.'}, status=403)

        return redirect('accounts:login')
    return wrapper

def usuario_proprio_or_tecnico(view_func):
    from tickets.models import Ticket
    
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Superusuários e Técnicos sempre passam
        if request.user.is_superuser or request.user.is_technician:
            return view_func(request, *args, **kwargs)
        
        ticket_id = kwargs.get('pk') or kwargs.get('ticket_id')
        if ticket_id:
            try:
                ticket = Ticket.objects.get(pk=ticket_id)
                if ticket.solicitante == request.user:
                    return view_func(request, *args, **kwargs)
            except Ticket.DoesNotExist:
                pass
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/tickets/api/'):
            return JsonResponse({'error': 'Permissão negada.'}, status=403)

        messages.error(request, 'Você não tem permissão para acessar este recurso.')
        return redirect('tickets:dashboard')
    return wrapper