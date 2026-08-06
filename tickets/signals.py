import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Ticket, Comentario

logger = logging.getLogger(__name__)


def _enviar_evento(evento, dados, canais):
    """Dispara um evento no Pusher com apenas metadados (nunca HTML)."""
    client = getattr(settings, 'PUSHER_CLIENT', None)
    if client is None:
        return
    try:
        client.trigger(canais, evento, dados)
    except Exception:
        # Falha pontual de tempo real não deve quebrar a request
        logger.exception('Falha ao disparar evento no Pusher: %s', evento)


@receiver(post_save, sender=Ticket)
def notificar_ticket_event(sender, instance, created, **kwargs):
    canal_global = ['fila-global']
    canal_ticket = [f'ticket-{instance.id}']

    if created:
        _enviar_evento(
            'novo_ticket',
            {'ticket_id': instance.id, 'action': 'novo_ticket'},
            canal_global,
        )
    else:
        if instance.status == Ticket.Status.CANCELADO:
            evento, acao = 'ticket_cancelado', 'ticket_cancelado'
        else:
            evento, acao = 'ticket_atualizado', 'ticket_atualizado'

        _enviar_evento(
            evento,
            {'ticket_id': instance.id, 'action': acao, 'status': instance.status},
            canal_global + canal_ticket,
        )


@receiver(post_save, sender=Comentario)
def notificar_novo_comentario(sender, instance, created, **kwargs):
    if created:
        _enviar_evento(
            'novo_comentario',
            {'ticket_id': instance.ticket.id, 'action': 'novo_comentario'},
            [f'ticket-{instance.ticket.id}'],
        )
