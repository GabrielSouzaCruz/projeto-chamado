import contextvars
import logging
import threading
from contextlib import contextmanager

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Ticket, Comentario

logger = logging.getLogger(__name__)

# Contexto: autor (request.user) da ação atual, lido pelos signals para
# incluir actor_id no payload do Pusher (filtra o "eco" no frontend).
_actor_id = contextvars.ContextVar('pusher_actor_id', default=None)


@contextmanager
def evento_do_usuario(usuario):
    """Marca o usuário que executa a ação; limpa ao sair (reset seguro via token)."""
    token = _actor_id.set(getattr(usuario, 'id', None))
    try:
        yield
    finally:
        _actor_id.reset(token)


def _disparar_no_pusher(client, evento, dados, canais):
    """Executa a chamada de rede do Pusher (rodada em thread paralela)."""
    try:
        client.trigger(canais, evento, dados)
    except Exception:
        # Falha pontual de tempo real não deve quebrar a request
        logger.exception('Falha ao disparar evento no Pusher: %s', evento)


def _enviar_evento(evento, dados, canais):
    """Dispara um evento no Pusher com apenas metadados (nunca HTML).

    A rede (Pusher) é resolvida numa thread paralela (daemon) para que o
    usuário receba o Response HTTP 200 instantaneamente, sem o latch da
    chamada síncrona. Os dados já vêm serializados (dict de primitivas),
    então a thread não toca no banco.
    """
    client = getattr(settings, 'PUSHER_CLIENT', None)
    if client is None:
        return
    if getattr(settings, 'PUSHER_ASSINCRONO', True):
        threading.Thread(
            target=_disparar_no_pusher,
            args=(client, evento, dados, list(canais)),
            daemon=True,
        ).start()
    else:
        _disparar_no_pusher(client, evento, dados, list(canais))


def _nome_usuario(usuario):
    """Nome de exibição: nome completo, com fallback para o username."""
    if usuario is None:
        return ''
    return usuario.get_full_name() or usuario.username


@receiver(post_save, sender=Ticket)
def notificar_ticket_event(sender, instance, created, **kwargs):
    canal_global = ['fila-global']
    canal_ticket = [f'ticket-{instance.id}']

    if created:
        _enviar_evento(
            'novo_ticket',
            {
                'ticket_id': instance.id,
                'action': 'novo_ticket',
                'titulo': instance.titulo,
                'actor_id': instance.solicitante_id,
                'remetente_nome': _nome_usuario(instance.solicitante),
            },
            canal_global,
        )
    else:
        if instance.status == Ticket.Status.CANCELADO:
            evento, acao = 'ticket_cancelado', 'ticket_cancelado'
        else:
            evento, acao = 'ticket_atualizado', 'ticket_atualizado'

        _enviar_evento(
            evento,
            {
                'ticket_id': instance.id,
                'action': acao,
                'status': instance.status,
                'titulo': instance.titulo,
                'actor_id': _actor_id.get(),
            },
            canal_global + canal_ticket,
        )


@receiver(post_save, sender=Comentario)
def notificar_novo_comentario(sender, instance, created, **kwargs):
    if created:
        ticket = instance.ticket
        destinatario_ids = {ticket.solicitante_id}
        if ticket.tecnico_responsavel_id:
            destinatario_ids.add(ticket.tecnico_responsavel_id)

        _enviar_evento(
            'novo_comentario',
            {
                'ticket_id': ticket.id,
                'action': 'novo_comentario',
                'titulo': ticket.titulo,
                'actor_id': instance.autor_id,
                'remetente_nome': _nome_usuario(instance.autor),
                'destinatario_ids': sorted(destinatario_ids),
            },
            ['fila-global', f'ticket-{ticket.id}'],
        )
