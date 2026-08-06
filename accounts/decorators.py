from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.http import JsonResponse

def tecnico_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_technician or request.user.is_superuser:
            return view_func(request, *args, **kwargs)

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