from django.db.models import Q, QuerySet, Count, Avg, DurationField, F
from django.utils import timezone

from .models import Ticket


def get_tickets_dashboard(usuario, busca: str = None, status: str = None) -> QuerySet:
    """Retorna a base de tickets do dashboard segundo o nível de acesso do usuário."""
    if getattr(usuario, 'is_technician', False) or usuario.is_superuser:
        qs = Ticket.objects.all()
    else:
        qs = Ticket.objects.filter(solicitante=usuario)

    if busca:
        qs = qs.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(id__icontains=busca)
        )
    if status and status.upper() != 'TODOS':
        qs = qs.filter(status__iexact=status)

    return qs.select_related('solicitante', 'tecnico_responsavel', 'categoria').order_by('-criado_em')


def get_estatisticas_dashboard(usuario) -> dict:
    """Retorna os contadores do dashboard numa única consulta agregada."""
    if getattr(usuario, 'is_technician', False) or usuario.is_superuser:
        qs = Ticket.objects.all()
    else:
        qs = Ticket.objects.filter(solicitante=usuario)

    return qs.aggregate(
        total=Count('id'),
        abertos=Count('id', filter=Q(status=Ticket.Status.ABERTO)),
        em_andamento=Count('id', filter=Q(status=Ticket.Status.EM_ANDAMENTO)),
        resolvidos=Count('id', filter=Q(status=Ticket.Status.RESOLVIDO)),
    )


def get_estatisticas_fila_admin() -> dict:
    """Estatísticas específicas para a visão da Fila do Administrador."""
    hoje = timezone.now().date()
    return {
        'total_hoje': Ticket.objects.filter(criado_em__date=hoje).count(),
        'sem_tecnico': Ticket.objects.filter(tecnico_responsavel__isnull=True).exclude(status__iexact='CANCELADO').count(),
        'criticos': Ticket.objects.filter(prioridade__iexact='critica').exclude(status__iexact='RESOLVIDO').count(),
    }


def get_historico_tickets(filtros: dict) -> QuerySet:
    """Processa a filtragem complexa do histórico de chamados."""
    tickets_qs = Ticket.objects.all()

    busca = filtros.get('busca')
    if busca:
        tickets_qs = tickets_qs.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(solicitante__username__icontains=busca) |
            Q(id__icontains=busca)
        )

    data_inicio = filtros.get('data_inicio')
    if data_inicio:
        tickets_qs = tickets_qs.filter(criado_em__date__gte=data_inicio)

    data_fim = filtros.get('data_fim')
    if data_fim:
        tickets_qs = tickets_qs.filter(criado_em__date__lte=data_fim)

    status_selecionados = filtros.get('status')
    if status_selecionados:
        tickets_qs = tickets_qs.filter(status__in=status_selecionados)

    prioridades_selecionadas = filtros.get('prioridade')
    if prioridades_selecionadas:
        tickets_qs = tickets_qs.filter(prioridade__in=prioridades_selecionadas)

    categorias_selecionadas = filtros.get('categoria')
    if categorias_selecionadas:
        tickets_qs = tickets_qs.filter(categoria_id__in=categorias_selecionadas)

    tecnico_id = filtros.get('tecnico')
    if tecnico_id and tecnico_id != 'todos':
        tickets_qs = tickets_qs.filter(tecnico_responsavel_id=tecnico_id)

    ordenar = filtros.get('ordenar', '-criado_em')

    return tickets_qs.order_by(ordenar).select_related('solicitante', 'tecnico_responsavel', 'categoria')


def get_estatisticas_historico(tickets_qs: QuerySet) -> dict:
    """Calcula contagem por status e tempo médio de resolução numa consulta agregada."""
    stats = tickets_qs.aggregate(
        total=Count('id'),
        resolvidos=Count('id', filter=Q(status__iexact='RESOLVIDO')),
        cancelados=Count('id', filter=Q(status__iexact='CANCELADO')),
        tempo_medio=Avg(
            F('resolvido_em') - F('criado_em'),
            filter=Q(status__iexact='RESOLVIDO', resolvido_em__isnull=False),
            output_field=DurationField(),
        ),
    )

    if stats['tempo_medio']:
        stats['tempo_medio_resolucao'] = stats['tempo_medio'].total_seconds() / 3600
    else:
        stats['tempo_medio_resolucao'] = None
    del stats['tempo_medio']

    return stats
