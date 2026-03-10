import csv
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from accounts.mixins import TecnicoRequiredMixin, ProprietarioOrTecnicoMixin
from accounts.decorators import tecnico_required, admin_required
from accounts.models import User
from .models import Ticket, Categoria, Comentario

from .forms import TicketForm, ComentarioForm, TicketStatusForm
from .models import Ticket, Comentario, Categoria

from django.db.models import Q, Avg, F
from django.utils.timezone import now
import csv
from django.http import HttpResponse

logger = logging.getLogger(__name__)

# =============================================================================
# DASHBOARD E PRINCIPAL
# =============================================================================

@login_required
def dashboard(request):
    # Definir se é técnico/admin
    is_team = request.user.is_technician or request.user.is_superuser
    
    # Base de tickets (Filtro de segurança)
    if is_team:
        tickets_base = Ticket.objects.all()
    else:
        tickets_base = Ticket.objects.filter(solicitante=request.user)

    # Capturar busca e filtros da URL
    busca = request.GET.get('busca')
    status_filtro = request.GET.get('status')

    if busca:
        tickets_base = tickets_base.filter(
            Q(titulo__icontains=busca) | 
            Q(descricao__icontains=busca) | 
            Q(id__icontains=busca)
        )
    
    if status_filtro:
        tickets_base = tickets_base.filter(status=status_filtro)

    # Cálculo das métricas (Stats)
    stats = {
        'total': tickets_base.count(),
        'abertos': tickets_base.filter(status='aberto').count(),
        'em_andamento': tickets_base.filter(status='em_andamento').count(),
        'resolvidos': tickets_base.filter(status='resolvido').count(),
    }

    tickets = tickets_base.order_by('-criado_em')

    return render(request, 'tickets/dashboard.html', {
        'tickets': tickets,
        'is_technician': is_team,
        'stats': stats  # Enviando os números para o HTML
    })

# =============================================================================
# APIs PARA POLLING EM TEMPO REAL
# =============================================================================

@login_required
def check_novos_tickets(request):
    ultimo_check = request.session.get('ultimo_check_tickets')
    if ultimo_check:
        try:
            ultimo_check_dt = datetime.fromisoformat(ultimo_check)
            novos_tickets = Ticket.objects.filter(criado_em__gt=ultimo_check_dt).count()
        except (ValueError, TypeError):
            novos_tickets = 0
    else:
        novos_tickets = 0
    
    request.session['ultimo_check_tickets'] = timezone.now().isoformat()
    return JsonResponse({'novos': novos_tickets > 0, 'quantidade': novos_tickets})

@login_required
@never_cache
def api_dashboard_update(request):
    try:
        user = request.user
        is_tech_attr = getattr(user, 'is_technician', False)
        is_admin = user.is_superuser
        sou_tecnico = is_tech_attr or is_admin

        # 1. DEFINE A BASE DE DADOS (A trava de segurança que você já tem)
        if sou_tecnico:
            # TÉCNICO VÊ TUDO DA EMPRESA
            queryset_para_stats = Ticket.objects.all()
        else:
            # USUÁRIO COMUM VÊ SÓ OS DELE
            queryset_para_stats = Ticket.objects.filter(solicitante=user)

        # 2. CÁLCULO DE ESTATÍSTICAS (Sempre baseadas na visão geral permitida)
        # Calculamos as stats ANTES de aplicar os filtros de busca da tela
        stats = {
            'total': queryset_para_stats.count(),
            'abertos': queryset_para_stats.filter(status='ABERTO').count(),
            'em_andamento': queryset_para_stats.filter(status='EM_ANDAMENTO').count(),
            'resolvidos': queryset_para_stats.filter(status='RESOLVIDO').count(),
        }

        # 3. APLICAÇÃO DE FILTROS PARA A LISTA DE CARDS (O que aparece embaixo)
        tickets_list_query = queryset_para_stats
        
        status_req = request.GET.get('status', '').upper()
        if status_req and status_req != 'TODOS':
            tickets_list_query = tickets_list_query.filter(status=status_req)

        busca = request.GET.get('busca')
        if busca:
            from django.db.models import Q
            tickets_list_query = tickets_list_query.filter(
                Q(titulo__icontains=busca) | 
                Q(descricao__icontains=busca) | 
                Q(id__icontains=busca)
            )

        # 4. BUSCA DOS DADOS PARA O HTML
        tickets_final = tickets_list_query.select_related(
            'solicitante', 'tecnico_responsavel', 'categoria'
        ).order_by('-criado_em')[:20]

        # 5. RENDERIZAÇÃO
        html = render_to_string('tickets/_dashboard_cards.html', {
            'tickets': tickets_final,
            'is_technician': sou_tecnico,
        }, request=request)
        
        return JsonResponse({
            'html': html, 
            'stats': stats, # Agora os stats são o total da visão (geral ou pessoal)
            'debug_user': user.username,
            'debug_is_tech': sou_tecnico
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
@user_passes_test(lambda u: u.is_staff or getattr(u, 'is_technician', False))
@never_cache
def api_fila_admin_update(request):
    # 1. Pegamos todos os tickets para começar
    tickets_base = Ticket.objects.all()
    
    # 2. Captura os filtros da URL (Garante que venham em minúsculo para comparar)
    status_f = request.GET.get('status', 'todos').strip().lower()
    cat_f = request.GET.get('categoria', '').strip()

    # 3. LÓGICA DE FILTRO DE STATUS (Onde está o erro)
    if status_f and status_f != 'todos':
        # Tentamos filtrar tanto em maiúsculo quanto minúsculo para não ter erro
        # O __iexact ignora se é maiúsculo ou minúsculo no banco
        tickets_base = tickets_base.filter(status__iexact=status_f)
    else:
        # No "Todos", mostramos apenas o que não foi finalizado para a fila não ficar infinita
        tickets_base = tickets_base.exclude(status__iexact='RESOLVIDO').exclude(status__iexact='CANCELADO').exclude(status__iexact='FECHADO')

    # 4. Filtro de Categoria
    if cat_f and cat_f.isdigit():
        tickets_base = tickets_base.filter(categoria_id=cat_f)

    # 5. Estatísticas (Calculadas de forma independente)
    hoje = timezone.now().date()
    stats = {
        'total_hoje': Ticket.objects.filter(criado_em__date=hoje).count(),
        'sem_tecnico': Ticket.objects.filter(tecnico_responsavel__isnull=True).exclude(status__iexact='CANCELADO').count(),
        'criticos': Ticket.objects.filter(prioridade__iexact='critica').exclude(status__iexact='RESOLVIDO').count(),
    }
    
    # 6. Ordenação: O mais novo SEMPRE no topo para o Admin ver
    tickets = tickets_base.select_related('solicitante', 'tecnico_responsavel', 'categoria').order_by('-criado_em')[:50]
    
    # 7. Renderização com o request para garantir permissões
    html = render_to_string('tickets/_fila_table.html', {
        'tickets': tickets,
    }, request=request)
    
    return JsonResponse({
        'html': html, 
        'stats': stats,
        'count': tickets_base.count() 
    })

# =============================================================================
# APIs DE TICKET (DETALHES E COMENTÁRIOS AJAX)
# =============================================================================

@login_required
def api_comentarios_update(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if not request.user.is_technician and ticket.solicitante != request.user:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    html = render_to_string('tickets/_comentarios_list.html', {
        'ticket': ticket,
        'comentarios': ticket.comentarios.select_related('autor').order_by('criado_em'),
        'request': request,
    })
    return JsonResponse({'html': html, 'count': ticket.comentarios.count()})

@login_required
def ticket_detail_ajax(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_technician and ticket.solicitante != request.user:
        return JsonResponse({'error': 'Acesso negado'}, status=403)
    
    return JsonResponse({
        'titulo': ticket.titulo,
        'status': ticket.get_status_display(),
        'prioridade': ticket.get_prioridade_display(),
        'descricao': ticket.descricao,
    })

# =============================================================================
# TICKET: DETALHES E AÇÕES
# =============================================================================

class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = 'tickets/ticket_form.html'
    success_url = reverse_lazy('tickets:dashboard')
    
    def form_valid(self, form):
        form.instance.solicitante = self.request.user
        messages.success(self.request, 'Chamado criado com sucesso!')
        return super().form_valid(form)

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
    if not request.user.is_technician and ticket.solicitante != request.user:
        messages.error(request, "Permissão negada.")
        return redirect('tickets:dashboard')

    if request.method == 'POST':
        # ADICIONE O request.FILES AQUI EMBAIXO:
        form = ComentarioForm(request.POST, request.FILES, usuario=request.user) 
        
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.ticket = ticket
            comentario.autor = request.user
            comentario.save()
            messages.success(request, "Comentário adicionado!")
    return redirect('tickets:detail', pk=pk)

@login_required
def assumir_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_technician:
        messages.error(request, "Apenas técnicos podem assumir chamados.")
        return redirect('tickets:dashboard')

    ticket.tecnico_responsavel = request.user
    # AJUSTE AQUI: Usando a constante do Model em vez de string "SOLTA"
    ticket.status = Ticket.Status.EM_ANDAMENTO 
    ticket.save()
    messages.success(request, f"Você assumiu o chamado #{ticket.id}")
    return redirect('tickets:detail', pk=pk)

@tecnico_required
def alterar_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        # Pegamos o valor direto do <select name="status"> do HTML
        novo_status = request.POST.get('status')
        
        if novo_status:
            ticket.status = novo_status
            
            # Lógica extra: Se for resolvido, salva a data da resolução
            if novo_status.upper() == 'RESOLVIDO':
                ticket.resolvido_em = timezone.now()
            
            ticket.save()
            messages.success(request, f'Status do chamado #{ticket.id} atualizado para {ticket.get_status_display()}!')
        else:
            messages.error(request, 'Erro ao atualizar: Status inválido.')
            
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
    
    # AJUSTE AQUI: Usando a constante do Model
    ticket.status = Ticket.Status.CANCELADO
    ticket.save()
    messages.warning(request, "Ticket cancelado com sucesso.")
    return redirect('tickets:dashboard')

class CategoriaCreateView(CreateView):
    model = Categoria
    fields = ['nome'] # ou os campos que sua categoria tiver
    template_name = 'tickets/categoria_form.html'
    success_url = reverse_lazy('tickets:categorias')

class CategoriaCreateView(CreateView):
    model = Categoria
    fields = ['nome', 'descricao'] # Ajuste conforme os campos do seu modelo
    template_name = 'tickets/categoria_form.html'
    success_url = reverse_lazy('tickets:categorias')

class CategoriaUpdateView(UpdateView):
    model = Categoria
    fields = ['nome', 'descricao']
    template_name = 'tickets/categoria_form.html'
    success_url = reverse_lazy('tickets:categorias')

class CategoriaDeleteView(DeleteView):
    model = Categoria
    template_name = 'tickets/categoria_confirm_delete.html'
    success_url = reverse_lazy('tickets:categorias')

# =============================================================================
# HISTÓRICO, FILA E CATEGORIAS
# =============================================================================

@login_required
def historico(request):
    # Segurança: Apenas técnicos e admins acessam o histórico completo
    if not (request.user.is_technician or request.user.is_superuser):
        messages.error(request, "Acesso negado.")
        return redirect('tickets:dashboard')

    tickets_qs = Ticket.objects.all()

    # --- CAPTURA DE FILTROS ---
    busca = request.GET.get('busca', '')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    status_selecionados = request.GET.getlist('status')
    prioridades_selecionadas = request.GET.getlist('prioridade')
    categorias_selecionadas = request.GET.getlist('categoria')
    tecnico_id = request.GET.get('tecnico')
    ordenar = request.GET.get('ordenar', '-criado_em')

    # --- APLICAÇÃO DOS FILTROS ---
    if busca:
        tickets_qs = tickets_qs.filter(
            Q(titulo__icontains=busca) | 
            Q(descricao__icontains=busca) |
            Q(solicitante__username__icontains=busca) |
            Q(id__icontains=busca)
        )

    if data_inicio:
        tickets_qs = tickets_qs.filter(criado_em__date__gte=data_inicio)
    if data_fim:
        tickets_qs = tickets_qs.filter(criado_em__date__lte=data_fim)
    
    if status_selecionados:
        tickets_qs = tickets_qs.filter(status__in=status_selecionados)
    
    if prioridades_selecionadas:
        tickets_qs = tickets_qs.filter(prioridade__in=prioridades_selecionadas)
    
    if categorias_selecionadas:
        tickets_qs = tickets_qs.filter(categoria_id__in=categorias_selecionadas)
    
    if tecnico_id and tecnico_id != 'todos':
        tickets_qs = tickets_qs.filter(tecnico_responsavel_id=tecnico_id)

    tickets_qs = tickets_qs.order_by(ordenar)

    # --- EXPORTAÇÃO CSV ---
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="historico_{now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Titulo', 'Solicitante', 'Status', 'Prioridade', 'Criado em'])
        for t in tickets_qs:
            writer.writerow([t.id, t.titulo, t.solicitante.username, t.status, t.prioridade, t.criado_em])
        return response

    # --- ESTATÍSTICAS DO RELATÓRIO ---
    stats = {
        'total': tickets_qs.count(),
        'resolvidos': tickets_qs.filter(status__iexact='RESOLVIDO').count(),
        'cancelados': tickets_qs.filter(status__iexact='CANCELADO').count(),
        'tempo_medio_resolucao': None
    }
    
    # Cálculo do Tempo Médio (apenas se houver resolvidos para não dar erro de divisão)
    tickets_resolvidos = tickets_qs.filter(status__iexact='RESOLVIDO', resolvido_em__isnull=False)
    
    if tickets_resolvidos.exists():
        # Calculamos a diferença entre resolvido_em e criado_em
        media = tickets_resolvidos.annotate(
            duracao=F('resolvido_em') - F('criado_em')
        ).aggregate(Avg('duracao'))['duracao__avg']
        
        if media:
            # Converte o timedelta para horas decimais
            stats['tempo_medio_resolucao'] = media.total_seconds() / 3600

    context = {
        'tickets': tickets_qs, # Adicione paginação aqui se desejar
        'stats': stats,
        'categorias': Categoria.objects.all(),
        'tecnicos': User.objects.filter(Q(is_technician=True) | Q(is_superuser=True)),
        'status_choices': Ticket.Status.choices,
        'prioridade_choices': Ticket.Prioridade.choices,
        'filtros': {
            'busca': busca,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'status': status_selecionados,
            'prioridade': prioridades_selecionadas,
            'categoria': categorias_selecionadas,
            'tecnico': tecnico_id,
            'ordenar': ordenar,
        }
    }
    return render(request, 'tickets/historico.html', context)

@admin_required
def fila_admin(request):
    # Pega os dados iniciais para não esperar o AJAX
    tickets = Ticket.objects.filter(status__in=['ABERTO', 'EM_ANDAMENTO']).select_related('solicitante', 'categoria')
    categorias = Categoria.objects.filter(ativa=True)
    
    # Cálculos rápidos para o primeiro carregamento
    stats = {
        'total_hoje': Ticket.objects.filter(criado_em__date=timezone.now().date()).count(),
        'sem_tecnico': Ticket.objects.filter(tecnico_responsavel__isnull=True).exclude(status='CANCELADO').count(),
        'criticos': Ticket.objects.filter(prioridade='critica').exclude(status__in=['RESOLVIDO', 'FECHADO']).count(),
    }

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

class CategoriaCreateView(CreateView):
    model = Categoria
    fields = ['nome', 'descricao']
    template_name = 'tickets/categoria_form.html'
    success_url = reverse_lazy('tickets:categorias')

class CategoriaUpdateView(UpdateView):
    model = Categoria
    fields = ['nome', 'descricao']
    template_name = 'tickets/categoria_form.html'
    success_url = reverse_lazy('tickets:categorias')

class CategoriaDeleteView(DeleteView):
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