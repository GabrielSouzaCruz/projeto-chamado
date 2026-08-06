import csv
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.views.decorators.cache import never_cache
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView

from accounts.mixins import ProprietarioOrTecnicoMixin, TecnicoOrStaffRequiredMixin
from accounts.decorators import tecnico_required, admin_required
from accounts.models import User

from .forms import TicketForm, ComentarioForm, TicketStatusForm
from .models import Ticket, Categoria
from . import services
from . import selectors

logger = logging.getLogger(__name__)

# =============================================================================
# DASHBOARD E PRINCIPAL
# =============================================================================

@login_required
def dashboard(request):
    busca = request.GET.get('busca')
    status_filtro = request.GET.get('status')

    tickets = selectors.get_tickets_dashboard(
        usuario=request.user,
        busca=busca,
        status=status_filtro
    )
    stats = selectors.get_estatisticas_dashboard(usuario=request.user)
    is_team = getattr(request.user, 'is_technician', False) or request.user.is_superuser

    return render(request, 'tickets/dashboard.html', {
        'tickets': tickets,
        'is_technician': is_team,
        'stats': stats
    })

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
# TICKET: DETALHES E AÇÕES
# =============================================================================

class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = 'tickets/ticket_form.html'
    
    def form_valid(self, form):
        form.instance.solicitante = self.request.user
        messages.success(self.request, 'Chamado criado com sucesso!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('tickets:detail', kwargs={'pk': self.object.pk})

class TicketDetailView(ProprietarioOrTecnicoMixin, DetailView):
    model = Ticket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comentarios'] = self.object.comentarios.all().select_related('autor').order_by('criado_em')
        context['comentario_form'] = ComentarioForm(usuario=self.request.user)
        context['status_form'] = TicketStatusForm(instance=self.object)
        return context

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

class TicketUpdateView(ProprietarioOrTecnicoMixin, UpdateView):
    model = Ticket
    form_class = TicketForm
    template_name = 'tickets/ticket_form.html'
    
    def get_success_url(self):
        return reverse_lazy('tickets:detail', kwargs={'pk': self.object.pk})

@login_required
def cancelar_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if ticket.solicitante != request.user and not request.user.is_superuser:
        messages.error(request, "Você não tem permissão para cancelar este ticket.")
        return redirect('tickets:detail', pk=pk)
    services.cancelar_ticket_service(ticket_id=pk)
    messages.warning(request, "Ticket cancelado com sucesso.")
    return redirect('tickets:dashboard')

@login_required
def apagar_ticket(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Acesso Negado: Apenas administradores podem apagar chamados do banco de dados.")
        return redirect('tickets:detail', pk=pk)
    services.apagar_ticket_service(ticket_id=pk)
    messages.success(request, f"Ticket #{pk} foi apagado permanentemente com sucesso.")
    return redirect('tickets:dashboard')


# =============================================================================
# HISTÓRICO, FILA E CATEGORIAS
# =============================================================================

@login_required
def historico(request):
    if not (request.user.is_technician or request.user.is_superuser):
        messages.error(request, "Acesso negado.")
        return redirect('tickets:dashboard')

    filtros = {
        'busca': request.GET.get('busca', ''),
        'data_inicio': request.GET.get('data_inicio'),
        'data_fim': request.GET.get('data_fim'),
        'status': request.GET.getlist('status'),
        'prioridade': request.GET.getlist('prioridade'),
        'categoria': request.GET.getlist('categoria'),
        'tecnico': request.GET.get('tecnico'),
        'ordenar': request.GET.get('ordenar', '-criado_em'),
    }

    tickets_qs = selectors.get_historico_tickets(filtros)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="historico_{now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Titulo', 'Solicitante', 'Status', 'Prioridade', 'Criado em'])
        for t in tickets_qs:
            writer.writerow([t.id, t.titulo, t.solicitante.username, t.status, t.prioridade, t.criado_em])
        return response

    stats = selectors.get_estatisticas_historico(tickets_qs)

    context = {
        'tickets': tickets_qs,
        'stats': stats,
        'categorias': Categoria.objects.all(),
        'tecnicos': User.objects.filter(Q(is_technician=True) | Q(is_superuser=True)),
        'status_choices': Ticket.Status.choices,
        'prioridade_choices': Ticket.Prioridade.choices,
        'filtros': filtros
    }
    return render(request, 'tickets/historico.html', context)

@admin_required
def fila_admin(request):
    # Dados iniciais para não depender da atualização AJAX
    tickets = Ticket.objects.filter(status__in=['ABERTO', 'EM_ANDAMENTO']).select_related('solicitante', 'categoria')
    categorias = Categoria.objects.filter(ativa=True)

    stats = selectors.get_estatisticas_fila_admin()

    return render(request, 'tickets/fila_admin.html', {
        'tickets': tickets,
        'categorias': categorias,
        'stats': stats,
        'filtros': request.GET
    })

@tecnico_required
def lista_categorias(request):
    categorias = Categoria.objects.all().annotate(total_tickets=Count('ticket')).order_by('nome')
    return render(request, 'tickets/categoria_list.html', {'categorias': categorias})

class CategoriaCreateView(TecnicoOrStaffRequiredMixin, CreateView):
    model = Categoria
    fields = ['nome', 'descricao']
    template_name = 'tickets/categoria_form.html'
    success_url = reverse_lazy('tickets:categorias')

class CategoriaUpdateView(TecnicoOrStaffRequiredMixin, UpdateView):
    model = Categoria
    fields = ['nome', 'descricao']
    template_name = 'tickets/categoria_form.html'
    success_url = reverse_lazy('tickets:categorias')

class CategoriaDeleteView(TecnicoOrStaffRequiredMixin, DeleteView):
    model = Categoria
    template_name = 'tickets/categoria_confirm_delete.html'
    success_url = reverse_lazy('tickets:categorias')
    
# =============================================================================
# PÁGINAS DE ERRO (Handlers)
# =============================================================================

def error_404(request, exception=None):
    """Página de erro 404 - Não Encontrado."""
    return render(request, '404.html', status=404)

def error_500(request):
    """Página de erro 500 - Erro Interno do Servidor."""
    return render(request, '500.html', status=500)

def error_403(request, exception=None):
    """Página de erro 403 - Acesso Negado."""
    return render(request, '403.html', status=403)