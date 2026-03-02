# tickets/views.py

from django.shortcuts import render, redirect, get_object_or_404

from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.views.generic import ListView, DetailView, CreateView, UpdateView

from django.urls import reverse_lazy

from django.http import JsonResponse

from django.db.models import Q, Count

 

from accounts.decorators import tecnico_required

from accounts.mixins import TecnicoRequiredMixin, ProprietarioOrTecnicoMixin

from .models import Ticket, Comentario, Categoria

from .forms import TicketForm, ComentarioForm, TicketStatusForm

 

 

@login_required

def dashboard(request):

    """

    Dashboard principal. Técnicos veem todos os tickets,

    usuários comuns veem apenas seus próprios.

    """

    if request.user.is_technician:

        tickets = Ticket.objects.all().select_related(

            'solicitante', 'tecnico_responsavel', 'categoria'

        )

    else:

        tickets = Ticket.objects.filter(

            solicitante=request.user

        ).select_related('tecnico_responsavel', 'categoria')
        # Filtros

    status = request.GET.get('status')

    if status:

        tickets = tickets.filter(status=status)

    

    prioridade = request.GET.get('prioridade')

    if prioridade:

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

    

    # Estatísticas para o dashboard

    stats = {

        'total': tickets.count(),

        'abertos': tickets.filter(status=Ticket.Status.ABERTO).count(),

        'em_andamento': tickets.filter(status=Ticket.Status.EM_ANDAMENTO).count(),

        'resolvidos': tickets.filter(status=Ticket.Status.RESOLVIDO).count(),

    }

    

    categorias = Categoria.objects.filter(ativa=True)

    

    return render(request, 'tickets/dashboard.html', {

        'tickets': tickets,

        'stats': stats,

        'categorias': categorias,

        'filtros': {'status': status, 'prioridade': prioridade, 'categoria': 
                    categoria_id}

    })

 

 

class TicketCreateView(CreateView):

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

        context['comentarios'] = self.object.comentarios.all()

        context['comentario_form'] = ComentarioForm(usuario=self.request.user)

        context['status_form'] = TicketStatusForm(instance=self.object)

        return context

 

 

@login_required

def adicionar_comentario(request, pk):

    """Adiciona comentário a um ticket."""

    ticket = get_object_or_404(Ticket, pk=pk)

    

    # Verifica permissão

    if not request.user.is_technician and ticket.solicitante != request.user:

        messages.error(request, 'Você não tem permissão para comentar neste ticket.')
        return redirect('tickets:dashboard')

    

    if request.method == 'POST':

        form = ComentarioForm(request.POST, request.FILES, usuario=request.user)

        if form.is_valid():

            comentario = form.save(commit=False)

            comentario.ticket = ticket

            comentario.autor = request.user

            # Usuários comuns não podem criar comentários internos

            if not request.user.is_technician:

                comentario.interno = False

            comentario.save()

            messages.success(request, 'Comentário adicionado!')

    

    return redirect('tickets:detail', pk=pk)

 

 

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
    """Altera o status do ticket."""

    ticket = get_object_or_404(Ticket, pk=pk)

    

    if request.method == 'POST':

        form = TicketStatusForm(request.POST, instance=ticket)

        if form.is_valid():

            form.save()

            messages.success(request, 'Status atualizado com sucesso!')

    

    return redirect('tickets:detail', pk=pk)

    # tickets/views.py (adicionar ao final)

 

def page_not_found(request, exception):

    """View para página 404 customizada."""

    return render(request, '404.html', status=404)

 

def server_error(request):

    """View para página 500 customizada."""

    return render(request, '500.html', status=500)

 

def permission_denied(request, exception):

    """View para página 403 customizada."""

    return render(request, '403.html', status=403)

# tickets/views.py (adicionar ao final)

 

class TicketUpdateView(ProprietarioOrTecnicoMixin, UpdateView):

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
    # tickets/views.py (adicionar ao final)

 

@tecnico_required

def lista_categorias(request):

    """Lista todas as categorias para gestão."""

    categorias = Categoria.objects.all().annotate(

        total_tickets=Count('ticket')

    ).order_by('nome')

    return render(request, 'tickets/categoria_list.html', {'categorias': categorias})

 

 

class CategoriaCreateView(TecnicoRequiredMixin, CreateView):

    model = Categoria

    fields = ['nome', 'icone', 'descricao', 'ativa']

    template_name = 'tickets/categoria_form.html'

    success_url = reverse_lazy('tickets:categorias')
    def form_valid(self, form):

        messages.success(self.request, 'Categoria criada com sucesso!')

        return super().form_valid(form)

 

 

class CategoriaUpdateView(TecnicoRequiredMixin, UpdateView):

    model = Categoria

    fields = ['nome', 'icone', 'descricao', 'ativa']

    template_name = 'tickets/categoria_form.html'

    success_url = reverse_lazy('tickets:categorias')

    

    def form_valid(self, form):

        messages.success(self.request, 'Categoria atualizada com sucesso!')

        return super().form_valid(form)