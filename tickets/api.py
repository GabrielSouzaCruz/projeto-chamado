# tickets/api.py
"""
Endpoints de API / AJAX do app de tickets.

Responsabilidade Única (SRP): aqui vivem apenas as views que servem o
frontend via fetch/WebSocket — mini-APIs HTML (partials) e endpoints que
retornam JsonResponse ou processam ações em tempo real com o Pusher.
As views clássicas (páginas HTML) continuam em views.py.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache

from accounts.decorators import tecnico_required

from .forms import ComentarioForm
from .models import Ticket
from . import services

# =============================================================================
# MINI-APIs HTML (FAST PATHS PARA O JAVASCRIPT)
# =============================================================================

@login_required
@never_cache
def api_dashboard_cards(request):
    """Devolve apenas o HTML dos cartões de contagem do Dashboard."""
    user = request.user
    sou_tecnico = getattr(user, 'is_technician', False) or user.is_superuser

    qs = Ticket.objects.all() if sou_tecnico else Ticket.objects.filter(solicitante=user)

    stats = {
        'total': qs.count(),
        'abertos': qs.filter(status__iexact='aberto').count(),
        'em_andamento': qs.filter(status__iexact='em_andamento').count(),
        'resolvidos': qs.filter(status__iexact='resolvido').count(),
    }

    return render(request, 'tickets/_dashboard_stats.html', {'stats': stats})


@login_required
@never_cache
def api_dashboard_table(request):
    """Devolve apenas o HTML da lista de chamados do Dashboard."""
    user = request.user
    sou_tecnico = getattr(user, 'is_technician', False) or user.is_superuser

    qs = Ticket.objects.all() if sou_tecnico else Ticket.objects.filter(solicitante=user)

    status_req = request.GET.get('status', '').upper()
    if status_req and status_req != 'TODOS':
        qs = qs.filter(status__iexact=status_req)

    busca = request.GET.get('busca')
    if busca:
        qs = qs.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(id__icontains=busca)
        )

    tickets_recentes = qs.select_related(
        'solicitante', 'tecnico_responsavel', 'categoria'
    ).order_by('-criado_em')[:20]

    return render(request, 'tickets/_dashboard_cards.html', {
        'tickets': tickets_recentes,
        'is_technician': sou_tecnico,
    })


@tecnico_required
@never_cache
def api_fila_admin_rows(request):
    """Devolve apenas as linhas (<tr>) atualizadas da Fila Admin."""
    tickets_base = Ticket.objects.all()

    status_f = request.GET.get('status', 'todos').strip().lower()
    if status_f and status_f != 'todos':
        tickets_base = tickets_base.filter(status__iexact=status_f)
    else:
        tickets_base = tickets_base.exclude(status__iexact='RESOLVIDO').exclude(status__iexact='CANCELADO').exclude(status__iexact='FECHADO')

    cat_f = request.GET.get('categoria', '').strip()
    if cat_f and cat_f.isdigit():
        tickets_base = tickets_base.filter(categoria_id=cat_f)

    tickets = tickets_base.select_related(
        'solicitante', 'tecnico_responsavel', 'categoria'
    ).order_by('-criado_em')[:50]

    novo_id = request.GET.get('novo_id')
    tickets_novos_ids = [int(novo_id)] if novo_id and novo_id.isdigit() else []

    return render(request, 'tickets/_fila_table.html', {
        'tickets': tickets,
        'tickets_novos_ids': tickets_novos_ids,
    })

# =============================================================================
# APIs DE TICKET (DETALHES E COMENTÁRIOS AJAX)
# =============================================================================

@login_required
def ticket_status_badge_partial(request, pk):
    """Mini-API: devolve apenas o badge de status atualizado do ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_technician and not request.user.is_superuser and ticket.solicitante != request.user:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    return render(request, 'tickets/_ticket_status_badge.html', {'ticket': ticket})

@login_required
def ticket_comentarios_partial(request, ticket_id):
    """
    Mini-API que devolve apenas o HTML limpo da lista de comentários.
    """
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if not request.user.is_technician and not request.user.is_superuser and ticket.solicitante != request.user:
        return JsonResponse({'error': 'Sem permissão'}, status=403)

    comentarios = ticket.comentarios.select_related('autor').order_by('criado_em')

    return render(request, 'tickets/_comentarios_list.html', {
        'ticket': ticket,
        'comentarios': comentarios,
    })

# =============================================================================
# AÇÕES AJAX EM TEMPO REAL (via fetch + Pusher)
# =============================================================================

@login_required
def adicionar_comentario(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_technician and not request.user.is_superuser and ticket.solicitante != request.user:
        messages.error(request, "Permissão negada.")
        return redirect('tickets:dashboard')

    if request.method == 'POST':
        form = ComentarioForm(request.POST, request.FILES, usuario=request.user)

        if form.is_valid():
            services.adicionar_comentario_service(
                ticket_id=pk,
                autor=request.user,
                dados_comentario=form.cleaned_data,
                arquivos=request.FILES
            )
            messages.success(request, "Comentário adicionado!")
    return redirect('tickets:detail', pk=pk)

@login_required
def assumir_ticket(request, pk):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not request.user.is_technician and not request.user.is_superuser:
        if is_ajax:
            return JsonResponse({'status': 'error', 'mensagem': 'Apenas técnicos podem assumir chamados.'}, status=403)
        messages.error(request, "Apenas técnicos podem assumir chamados.")
        return redirect('tickets:dashboard')

    services.assumir_ticket_service(ticket_id=pk, tecnico=request.user)
    messages.success(request, f"Você assumiu o chamado #{pk}")

    if is_ajax:
        return JsonResponse({'status': 'success'})

    return redirect('tickets:detail', pk=pk)

@tecnico_required
def alterar_status(request, pk):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        novo_status = request.POST.get('status')
        if novo_status:
            try:
                services.alterar_status_ticket_service(ticket_id=pk, novo_status=novo_status)
            except ValidationError:
                messages.error(request, 'Erro ao atualizar: Status inválido.')
                if is_ajax:
                    return JsonResponse({'status': 'error', 'mensagem': 'Status inválido.'}, status=400)
                return redirect('tickets:detail', pk=pk)
            messages.success(request, f'Status do chamado #{pk} atualizado com sucesso!')
            if is_ajax:
                return JsonResponse({'status': 'success'})
        else:
            messages.error(request, 'Erro ao atualizar: Status inválido.')
            if is_ajax:
                return JsonResponse({'status': 'error', 'mensagem': 'Status inválido.'}, status=400)

    return redirect('tickets:detail', pk=pk)
