from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Ticket, Comentario


@transaction.atomic
def assumir_ticket_service(ticket_id: int, tecnico) -> Ticket:
    """Atribui um técnico ao ticket com bloqueio de concorrência."""
    ticket = Ticket.objects.select_for_update().get(id=ticket_id)
    ticket.tecnico_responsavel = tecnico
    if ticket.status == Ticket.Status.ABERTO:
        ticket.status = Ticket.Status.EM_ANDAMENTO

    ticket.save()
    return ticket


@transaction.atomic
def alterar_status_ticket_service(ticket_id: int, novo_status: str) -> Ticket:
    """Altera o status e registra a data de resolução, rejeitando status inválidos."""
    if novo_status not in Ticket.Status.values:
        raise ValidationError(f'Status inválido: {novo_status}')

    ticket = Ticket.objects.select_for_update().get(id=ticket_id)

    ticket.status = novo_status
    if novo_status == Ticket.Status.RESOLVIDO and not ticket.resolvido_em:
        ticket.resolvido_em = timezone.now()

    ticket.save()
    return ticket


@transaction.atomic
def cancelar_ticket_service(ticket_id: int) -> Ticket:
    """Cancela o ticket isolando a lógica de estado."""
    ticket = Ticket.objects.select_for_update().get(id=ticket_id)
    ticket.status = Ticket.Status.CANCELADO
    ticket.save()
    return ticket


@transaction.atomic
def adicionar_comentario_service(ticket_id: int, autor, dados_comentario: dict, arquivos=None) -> Comentario:
    """Insere um comentário atrelado ao lock do ticket principal."""
    ticket = Ticket.objects.select_for_update().get(id=ticket_id)

    comentario = Comentario(
        ticket=ticket,
        autor=autor,
        mensagem=dados_comentario.get('mensagem'),
        interno=dados_comentario.get('interno', False),
        anexo=arquivos.get('anexo') if arquivos else None
    )
    comentario.save()
    return comentario


@transaction.atomic
def apagar_ticket_service(ticket_id: int):
    """Apaga o ticket e suas dependências."""
    ticket = Ticket.objects.select_for_update().get(id=ticket_id)
    ticket.delete()
