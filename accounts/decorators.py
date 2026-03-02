# accounts/decorators.py

from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.shortcuts import redirect

from functools import wraps

 

def tecnico_required(view_func):

    """

    Decorador que verifica se o usuário está autenticado e é técnico.

    Redireciona para home com mensagem de erro se não for técnico.

    """

    @login_required

    @wraps(view_func)

    def wrapper(request, *args, **kwargs):

        if not request.user.is_technician:

            messages.error(

                request, 

                'Acesso restrito a técnicos de TI.'

            )

            return redirect('tickets:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper

 

def usuario_proprio_or_tecnico(view_func):

    """

    Decorador que permite acesso se:

    - O usuário é técnico, OU

    - O usuário é o proprietário do recurso

    Requer que a view receba um parâmetro 'pk' ou 'ticket_id'.

    """

    @login_required

    @wraps(view_func)

    def wrapper(request, *args, **kwargs):

        from tickets.models import Ticket
        # Técnicos têm acesso total

        if request.user.is_technician:

            return view_func(request, *args, **kwargs)

        

        # Verifica se o usuário é proprietário do ticket

        ticket_id = kwargs.get('pk') or kwargs.get('ticket_id')

        if ticket_id:

            try:

                ticket = Ticket.objects.get(pk=ticket_id)

                if ticket.solicitante == request.user:

                    return view_func(request, *args, **kwargs)

            except Ticket.DoesNotExist:

                pass

        

        messages.error(request, 'Você não tem permissão para acessar este recurso.')

        return redirect('tickets:dashboard')

    

    return wrapper