# tickets/views.py
"""
Views do sistema de chamados.
Inclui dashboard, CRUD de tickets, comentários e APIs para polling em tempo real.
"""

import csv
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from accounts.decorators import tecnico_required, admin_required
from accounts.mixins import TecnicoRequiredMixin, ProprietarioOrTecnicoMixin
from accounts.models import User

from .forms import TicketForm, ComentarioForm, TicketStatusForm
from .models import Ticket, Comentario, Categoria


# =============================================================================
# DASHBOARD
# =============================================================================

logger = logging.getLogger(__name__)

@login_required
def dashboard(request):
    """
    Dashboard principal.
    Técnicos veem todos os tickets, usuários comuns veem apenas seus próprios.
    """
    is_technician = getattr(request.user, 'is_technician', False)
    
    # Queryset base com otimização de queries (evita N+1)
    if is_technician:
        tickets = Ticket.objects.all().select_related(
            'solicitante', 'tecnico_responsavel', 'categoria'
        )
    else:
        tickets = Ticket.objects.filter(
            solicitante=request.user
        ).select_related('solicitante', 'tecnico_responsavel', 'categoria')
    
    # Aplicar filtros
    status = request.GET.get('status')
    if status:
        tickets = tickets.filter(status=status)
    
    prioridade = request.GET.get('prioridade')
    if prioridade and is_technician:
        tickets = tickets.filter(prioridade=prioridade)
    
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        tickets = tickets.filter(categoria_id=categoria_id)
    
    busca = request.GET.get('busca')
    if busca:
        tickets = tickets.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(solicitante__username__icontains=busca)
        )
    
    # Estatísticas (calculadas após filtros)
    if is_technician:
        stats = {
            'total': tickets.count(),
            'abertos': tickets.filter(status=Ticket.Status.ABERTO).count(),
            'em_andamento': tickets.filter(status=Ticket.Status.EM_ANDAMENTO).count(),
            'resolvidos': tickets.filter(status=Ticket.Status.RESOLVIDO).count(),
        }
    else:
        stats = {
            'total': tickets.count(),
            'resolvidos': tickets.filter(status=Ticket.Status.RESOLVIDO).count(),
            'meus_em_aberto': tickets.filter(
                status__in=[Ticket.Status.ABERTO, Ticket.Status.EM_ANDAMENTO]
            ).count(),
        }
    
    categorias = Categoria.objects.filter(ativa=True)
    
    return render(request, 'tickets/dashboard.html', {
        'tickets': tickets,
        'stats': stats,
        'categorias': categorias,
        'filtros': {'status': status, 'prioridade': prioridade, 'categoria': categoria_id},
        'is_technician': is_technician,
        'request': request,
    })


# =============================================================================
# APIs PARA POLLING EM TEMPO REAL
# =============================================================================

@login_required
def check_novos_tickets(request):
    """
    API para verificar se há novos tickets desde o último check.
    Usada pelo áudio de notificação no base.html (polling 10s).
    """
    if not request.user.is_authenticated:
        return JsonResponse({'novos': False})
    
    ultimo_check = request.session.get('ultimo_check_tickets')
    
    if ultimo_check:
        from datetime import datetime
        ultimo_check = datetime.fromisoformat(ultimo_check)
        novos_tickets = Ticket.objects.filter(criado_em__gt=ultimo_check).count()
    else:
        novos_tickets = 0
    
    # Atualiza timestamp do último check na sessão
    request.session['ultimo_check_tickets'] = timezone.now().isoformat()
    
    return JsonResponse({
        'novos': novos_tickets > 0,
        'quantidade': novos_tickets
    })


@login_required
def api_dashboard_update(request):
    """
    API para polling do dashboard em tempo real.
    Retorna HTML parcial + estatísticas em JSON (polling 15s).
    
    IMPORTANTE: Stats são calculados ANTES do slice porque Django não permite
    filter() em um queryset já fatiado.
    """
    try:
        is_technician = getattr(request.user, 'is_technician', False)
        
        # Queryset base com otimização
        if is_technician:
            tickets_base = Ticket.objects.all().select_related(
                'solicitante', 'tecnico_responsavel', 'categoria'
            )
        else:
            tickets_base = Ticket.objects.filter(
                solicitante=request.user
            ).select_related('solicitante', 'tecnico_responsavel', 'categoria')
        
        # Aplicar filtros (ANTES do slice)
        status = request.GET.get('status')
        if status and status in [s[0] for s in Ticket.Status.choices]:
            tickets_base = tickets_base.filter(status=status)
        
        prioridade = request.GET.get('prioridade')
        if prioridade and is_technician and prioridade in [p[0] for p in Ticket.Prioridade.choices]:
            tickets_base = tickets_base.filter(prioridade=prioridade)
        
        categoria_id = request.GET.get('categoria')
        if categoria_id and categoria_id.isdigit():
            tickets_base = tickets_base.filter(categoria_id=categoria_id)
        
        # Stats calculados do queryset completo (com filtros, sem slice)
        stats = {
            'total': tickets_base.count(),
            'abertos': tickets_base.filter(status=Ticket.Status.ABERTO).count(),
            'em_andamento': tickets_base.filter(status=Ticket.Status.EM_ANDAMENTO).count(),
            'resolvidos': tickets_base.filter(status=Ticket.Status.RESOLVIDO).count(),
        }
        if not is_technician:
            stats['meus_em_aberto'] = tickets_base.filter(
                status__in=[Ticket.Status.ABERTO, Ticket.Status.EM_ANDAMENTO]
            ).count()
        
        # Slice apenas para o HTML (performance no payload)
        tickets = tickets_base.order_by('-criado_em')[:20]
        
        # ✅ CORREÇÃO: Adicionar 'request' para {% csrf_token %} funcionar no template parcial
        html = render_to_string('tickets/_dashboard_cards.html', {
            'tickets': tickets,
            'is_technician': is_technician,
            'request': request,  # ← ESSENCIAL para CSRF
        })
        
        return JsonResponse({
            'html': html,
            'stats': stats,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro em api_dashboard_update: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_comentarios_update(request, ticket_id):
    """
    API para polling de comentários em tempo real.
    Retorna HTML parcial da lista de comentários (polling 10s).
    """
    try:
        ticket = Ticket.objects.select_related(
            'solicitante', 'tecnico_responsavel'
        ).get(id=ticket_id)
    except Ticket.DoesNotExist:
        return JsonResponse({'error': 'Ticket não encontrado'}, status=404)
    
    # Segurança: apenas técnico ou solicitante podem ver comentários
    if not request.user.is_technician and ticket.solicitante != request.user:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    # ✅ CORREÇÃO: Adicionar 'request' para {% csrf_token %} funcionar no template parcial
    html = render_to_string('tickets/_comentarios_list.html', {
        'ticket': ticket,
        'comentarios': ticket.comentarios.select_related('autor').order_by('criado_em'),
        'request': request,  # ← ESSENCIAL para CSRF
    })
    
    return JsonResponse({
        'html': html,
        'count': ticket.comentarios.count(),
        'timestamp': timezone.now().isoformat()
    })


@login_required
def ticket_detail_ajax(request, pk):
    """
    API para submit de comentários via AJAX (sem refresh da página).
    Usada no ticket_detail.html.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Segurança: apenas técnico ou solicitante podem comentar
    if not request.user.is_technician and ticket.solicitante != request.user:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == 'POST':
        form = ComentarioForm(request.POST, request.FILES, usuario=request.user)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.ticket = ticket
            comentario.autor = request.user
            
            # Segurança: usuários comuns não podem criar comentários internos
            if not request.user.is_technician:
                comentario.interno = False
            
            comentario.save()
            
            # ✅ CORREÇÃO: Adicionar 'request' para {% csrf_token %} funcionar no template parcial
            html = render_to_string('tickets/_comentarios_list.html', {
                'ticket': ticket,
                'comentarios': ticket.comentarios.select_related('autor').order_by('criado_em'),
                'request': request,  # ← ESSENCIAL para CSRF
            })
            
            return JsonResponse({
                'success': True,
                'html': html,
                'count': ticket.comentarios.count(),
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            }, status=400)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)


@login_required
@admin_required
def api_fila_admin_update(request):
    """
    API para polling da fila admin em tempo real.
    Retorna HTML parcial da tabela + estatísticas (polling 10s).
    """
    status_filter = request.GET.get('status', 'aberto')
    categoria_filter = request.GET.get('categoria')
    
    # Query base com otimização
    tickets = Ticket.objects.select_related(
        'solicitante', 'tecnico_responsavel', 'categoria'
    ).prefetch_related('comentarios')
    
    # Aplicar filtros
    if status_filter and status_filter != 'todos':
        tickets = tickets.filter(status=status_filter)
    
    if categoria_filter:
        tickets = tickets.filter(categoria_id=categoria_filter)
    
    tickets = tickets.order_by('-criado_em')
    ultimos_tickets = tickets[:10]
    
    # Estatísticas
    stats = {
        'total_hoje': Ticket.objects.filter(
            criado_em__date=timezone.now().date()
        ).count(),
        'sem_tecnico': Ticket.objects.filter(
            status__in=[Ticket.Status.ABERTO, Ticket.Status.EM_ANDAMENTO],
            tecnico_responsavel__isnull=True
        ).count(),
        'criticos': Ticket.objects.filter(
            prioridade=Ticket.Prioridade.CRITICA,
            status__in=[Ticket.Status.ABERTO, Ticket.Status.EM_ANDAMENTO]
        ).count(),
    }
    
    # ✅ CORREÇÃO: Adicionar 'request' para {% csrf_token %} funcionar no template parcial
    html = render_to_string('tickets/_fila_table.html', {
        'tickets': tickets,
        'ultimos_tickets': ultimos_tickets,
        'request': request,  # ← ESSENCIAL para CSRF
    })
    
    return JsonResponse({
        'html': html,
        'stats': stats,
        'count': tickets.count(),
        'timestamp': timezone.now().isoformat()
    })


# =============================================================================
# CRUD DE TICKETS
# =============================================================================

class TicketCreateView(CreateView):
    """Criação de novos tickets (usuários logados)."""
    
    model = Ticket
    form_class = TicketForm
    template_name = 'tickets/ticket_form.html'
    success_url = reverse_lazy('tickets:dashboard')
    
    def form_valid(self, form):
        form.instance.solicitante = self.request.user
        messages.success(self.request, 'Chamado criado com sucesso!')
        return super().form_valid(form)


class TicketDetailView(ProprietarioOrTecnicoMixin, DetailView):
    """Detalhes de um ticket específico."""
    
    model = Ticket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comentarios'] = self.object.comentarios.all()
        context['comentario_form'] = ComentarioForm(usuario=self.request.user)
        context['status_form'] = TicketStatusForm(instance=self.object)
        context['status_choices'] = Ticket.Status.choices
        context['prioridade_choices'] = Ticket.Prioridade.choices
        return context


class TicketUpdateView(ProprietarioOrTecnicoMixin, UpdateView):
    """Edição de tickets (proprietário ou técnico)."""
    
    model = Ticket
    form_class = TicketForm
    template_name = 'tickets/ticket_form.html'
    
    def get_success_url(self):
        return reverse_lazy('tickets:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Chamado atualizado com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        return context


@login_required
def adicionar_comentario(request, pk):
    """Adiciona comentário a um ticket (fallback se AJAX falhar)."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Segurança: apenas técnico ou solicitante podem comentar
    if not request.user.is_technician and ticket.solicitante != request.user:
        messages.error(request, 'Você não tem permissão para comentar neste ticket.')
        return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        form = ComentarioForm(request.POST, request.FILES, usuario=request.user)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.ticket = ticket
            comentario.autor = request.user
            
            # Segurança: usuários comuns não podem criar comentários internos
            if not request.user.is_technician:
                comentario.interno = False
            
            comentario.save()
            messages.success(request, 'Comentário adicionado!')
    
    return redirect('tickets:detail', pk=pk)


@login_required
def cancelar_ticket(request, pk):
    """
    Solicitante cancela seu próprio ticket.
    Ticket permanece no histórico como "Cancelado" (soft delete).
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Segurança: apenas o solicitante pode cancelar
    if ticket.solicitante != request.user:
        messages.error(request, 'Você não tem permissão para cancelar este chamado.')
        return redirect('tickets:dashboard')
    
    # Validação: só permite cancelar se estiver em status inicial
    if ticket.status in [Ticket.Status.RESOLVIDO, Ticket.Status.FECHADO, Ticket.Status.CANCELADO]:
        messages.warning(request, 'Este chamado já está finalizado e não pode ser cancelado.')
        return redirect('tickets:detail', pk=pk)
    
    if request.method == 'POST':
        ticket.status = Ticket.Status.CANCELADO
        ticket.save()
        messages.success(request, 'Chamado cancelado com sucesso!')
        return redirect('tickets:dashboard')
    
    return redirect('tickets:detail', pk=pk)


# =============================================================================
# AÇÕES DE TÉCNICO
# =============================================================================

@tecnico_required
def assumir_ticket(request, pk):
    """Técnico assume responsabilidade pelo ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if ticket.tecnico_responsavel and ticket.tecnico_responsavel != request.user:
        messages.warning(request, f'Este ticket já foi assumido por {ticket.tecnico_responsavel}.')
    else:
        ticket.tecnico_responsavel = request.user
        if ticket.status == Ticket.Status.ABERTO:
            ticket.status = Ticket.Status.EM_ANDAMENTO
        ticket.save()
        messages.success(request, 'Você assumiu este chamado!')
    
    return redirect('tickets:detail', pk=pk)


@tecnico_required
def alterar_status(request, pk):
    """Altera o status do ticket (via form no detail)."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        form = TicketStatusForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, 'Status atualizado com sucesso!')
    
    return redirect('tickets:detail', pk=pk)


# =============================================================================
# HISTÓRICO E RELATÓRIOS
# =============================================================================

@tecnico_required
def historico_tickets(request):
    """
    Histórico de chamados com filtros avançados e exportação CSV.
    Acessível apenas para técnicos/admins.
    """
    # Filtros da URL
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    status_filter = request.GET.getlist('status')
    categoria_filter = request.GET.getlist('categoria')
    prioridade_filter = request.GET.getlist('prioridade')
    tecnico_filter = request.GET.get('tecnico')
    busca = request.GET.get('busca')
    
    # Query base com otimização
    tickets = Ticket.objects.select_related(
        'solicitante', 'tecnico_responsavel', 'categoria'
    ).prefetch_related('comentarios')
    
    # Aplicar filtros
    if data_inicio:
        tickets = tickets.filter(criado_em__date__gte=data_inicio)
    if data_fim:
        tickets = tickets.filter(criado_em__date__lte=data_fim)
    
    if status_filter:
        tickets = tickets.filter(status__in=status_filter)
    
    if categoria_filter:
        tickets = tickets.filter(categoria_id__in=categoria_filter)
    
    if prioridade_filter:
        tickets = tickets.filter(prioridade__in=prioridade_filter)
    
    if tecnico_filter and tecnico_filter != 'todos':
        tickets = tickets.filter(tecnico_responsavel_id=tecnico_filter)
    
    if busca:
        tickets = tickets.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(solicitante__username__icontains=busca) |
            Q(solicitante__first_name__icontains=busca) |
            Q(solicitante__last_name__icontains=busca)
        )
    
    ordenar = request.GET.get('ordenar', '-criado_em')
    tickets = tickets.order_by(ordenar)
    
    # Estatísticas
    stats = {
        'total': tickets.count(),
        'resolvidos': tickets.filter(status=Ticket.Status.RESOLVIDO).count(),
        'cancelados': tickets.filter(status=Ticket.Status.CANCELADO).count(),
        'tempo_medio_resolucao': None,
    }
    
    # Calcula tempo médio de resolução (apenas para resolvidos com data)
    resolvidos_com_data = tickets.filter(
        status=Ticket.Status.RESOLVIDO,
        resolvido_em__isnull=False
    )
    if resolvidos_com_data.exists():
        tempos = [
            (t.resolvido_em - t.criado_em).total_seconds() / 3600
            for t in resolvidos_com_data
        ]
        if tempos:
            stats['tempo_medio_resolucao'] = sum(tempos) / len(tempos)
    
    # Dados para filtros
    categorias = Categoria.objects.filter(ativa=True)
    tecnicos = User.objects.filter(
        is_technician=True, is_active=True
    ) if request.user.is_superuser else None
    
    # Exportação CSV
    if request.GET.get('export') == 'csv':
        return exportar_historico_csv(tickets)
    
    return render(request, 'tickets/historico.html', {
        'tickets': tickets,
        'stats': stats,
        'categorias': categorias,
        'tecnicos': tecnicos,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'status': status_filter,
            'categoria': categoria_filter,
            'prioridade': prioridade_filter,
            'tecnico': tecnico_filter,
            'busca': busca,
            'ordenar': ordenar,
        },
        'status_choices': Ticket.Status.choices,
        'prioridade_choices': Ticket.Prioridade.choices,
    })


def exportar_historico_csv(tickets):
    """Exporta histórico de tickets para CSV (Excel compatível)."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="historico_chamados_{timezone.now().date()}.csv"'
    
    # BOM para Excel reconhecer UTF-8
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response, delimiter=';')
    
    # Cabeçalho
    writer.writerow([
        'ID', 'Título', 'Solicitante', 'Técnico', 'Categoria',
        'Prioridade', 'Status', 'Criado em', 'Resolvido em',
        'Tempo (horas)', 'Comentários', 'Descrição'
    ])
    
    # Dados
    for ticket in tickets:
        tempo_resolucao = None
        if ticket.resolvido_em and ticket.criado_em:
            tempo_resolucao = round(
                (ticket.resolvido_em - ticket.criado_em).total_seconds() / 3600, 2
            )
        
        writer.writerow([
            ticket.id,
            ticket.titulo,
            ticket.solicitante.get_full_name() or ticket.solicitante.username,
            ticket.tecnico_responsavel.get_full_name() if ticket.tecnico_responsavel else 'Não atribuído',
            ticket.categoria.nome if ticket.categoria else 'Sem categoria',
            ticket.get_prioridade_display(),
            ticket.get_status_display(),
            ticket.criado_em.strftime('%d/%m/%Y %H:%M'),
            ticket.resolvido_em.strftime('%d/%m/%Y %H:%M') if ticket.resolvido_em else '',
            tempo_resolucao if tempo_resolucao else '',
            ticket.comentarios.count(),
            ticket.descricao[:100] + '...' if len(ticket.descricao) > 100 else ticket.descricao,
        ])
    
    return response


# =============================================================================
# CATEGORIAS
# =============================================================================

@tecnico_required
def lista_categorias(request):
    """Lista todas as categorias para gestão (técnicos)."""
    categorias = Categoria.objects.all().annotate(
        total_tickets=Count('ticket')
    ).order_by('nome')
    return render(request, 'tickets/categoria_list.html', {'categorias': categorias})


class CategoriaCreateView(TecnicoRequiredMixin, CreateView):
    """Criação de novas categorias."""
    
    model = Categoria
    fields = ['nome', 'icone', 'descricao', 'ativa']
    template_name = 'tickets/categoria_form.html'
    success_url = reverse_lazy('tickets:categorias')
    
    def form_valid(self, form):
        messages.success(self.request, 'Categoria criada com sucesso!')
        return super().form_valid(form)


class CategoriaUpdateView(TecnicoRequiredMixin, UpdateView):
    """Edição de categorias existentes."""
    
    model = Categoria
    fields = ['nome', 'icone', 'descricao', 'ativa']
    template_name = 'tickets/categoria_form.html'
    success_url = reverse_lazy('tickets:categorias')
    
    def form_valid(self, form):
        messages.success(self.request, 'Categoria atualizada com sucesso!')
        return super().form_valid(form)


# =============================================================================
# FILA ADMIN
# =============================================================================

@admin_required
def fila_admin(request):
    """
    Painel administrativo para gerenciar fila de chamados.
    Apenas superusers (Admins do Django) podem acessar.
    """
    # Retorna JSON para requisições AJAX de contagem (legado)
    if request.GET.get('no_ui'):
        tickets_count = Ticket.objects.filter(
            status__in=[Ticket.Status.ABERTO, Ticket.Status.EM_ANDAMENTO, Ticket.Status.AGUARDANDO]
        ).count()
        return JsonResponse({'count': tickets_count})
    
    # Filtros da URL
    status_filter = request.GET.get('status', 'aberto')
    categoria_filter = request.GET.get('categoria')
    
    # Query base
    tickets = Ticket.objects.select_related(
        'solicitante', 'tecnico_responsavel', 'categoria'
    ).prefetch_related('comentarios')
    
    # Aplicar filtros
    if status_filter and status_filter != 'todos':
        tickets = tickets.filter(status=status_filter)
    
    if categoria_filter:
        tickets = tickets.filter(categoria_id=categoria_filter)
    
    tickets = tickets.order_by('-criado_em')
    ultimos_tickets = tickets[:10]
    
    # Estatísticas rápidas
    stats = {
        'total_hoje': Ticket.objects.filter(
            criado_em__date=timezone.now().date()
        ).count(),
        'sem_tecnico': Ticket.objects.filter(
            status__in=[Ticket.Status.ABERTO, Ticket.Status.EM_ANDAMENTO],
            tecnico_responsavel__isnull=True
        ).count(),
        'criticos': Ticket.objects.filter(
            prioridade=Ticket.Prioridade.CRITICA,
            status__in=[Ticket.Status.ABERTO, Ticket.Status.EM_ANDAMENTO]
        ).count(),
    }
    
    categorias = Categoria.objects.filter(ativa=True)
    
    return render(request, 'tickets/fila_admin.html', {
        'tickets': tickets,
        'ultimos_tickets': ultimos_tickets,
        'stats': stats,
        'categorias': categorias,
        'filtros': {'status': status_filter, 'categoria': categoria_filter},
        'auto_refresh': request.GET.get('refresh', '30'),
        'request': request,
    })


# =============================================================================
# PÁGINAS DE ERRO
# =============================================================================

def error_404(request, exception):
    """Página de erro 404 customizada."""
    return render(request, '404.html', status=404)


def error_500(request):
    """Página de erro 500 customizada."""
    return render(request, '500.html', status=500)


def error_403(request, exception):
    """Página de erro 403 customizada."""
    return render(request, '403.html', status=403)