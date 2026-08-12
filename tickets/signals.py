import contextvars
import json
import logging
import threading
from contextlib import contextmanager

from django.conf import settings
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User
from .models import Ticket, Comentario, PushSubscription

# pywebpush com guarda: sem a lib instalada o web push fica desativado, mas o
# boot e o tempo real (Pusher) continuam funcionando normalmente.
try:
    from pywebpush import webpush, WebPushException
except ImportError:
    webpush = None
    WebPushException = None

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


def _disparar_web_push_worker(user_id, titulo, mensagem, url):
    """Dispara Web Push nativo para TODAS as inscrições do usuário (thread).

    Payload JSON {titulo, mensagem, url} → o sw.js exibe a notificação nativa
    (banner/vibração) mesmo com o app fechado. Erro 410 (Gone) significa que o
    navegador do usuário invalidou a inscrição (permissão removida): apaga o
    registro do banco para não acumular lixo nem tentar reenviar para sempre.
    """
    try:
        inscricoes = PushSubscription.objects.filter(user_id=user_id).order_by('id')
        for insc in inscricoes:
            try:
                webpush(
                    subscription_info={
                        'endpoint': insc.endpoint,
                        'keys': {'p256dh': insc.p256dh, 'auth': insc.auth},
                    },
                    data=json.dumps({'titulo': titulo, 'mensagem': mensagem, 'url': url}),
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={'sub': settings.VAPID_ADMIN_EMAIL},
                )
            except WebPushException as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 410:
                    insc.delete()  # Gone: inscrição inválida → limpa o registro
                else:
                    logger.warning('Web push falhou (HTTP %s): %s', status, exc)
            except Exception:
                logger.exception('Erro inesperado ao disparar web push')
    except Exception:
        logger.exception('Erro ao listar inscrições de push do usuário %s', user_id)


def _enviar_web_push(user_id, titulo, mensagem, url):
    """Agenda um Web Push nativo (VAPID) para o usuário, em thread paralela.

    Desativado silenciosamente se a lib ou as chaves VAPID não existirem no
    ambiente (dev/CI): o sistema segue 100% funcional só com o tempo real do
    Pusher (DOM + toasts). Nunca dispara para o próprio autor (sem eco).
    """
    if webpush is None:
        return
    if not getattr(settings, 'VAPID_PUBLIC_KEY', '') or not getattr(settings, 'VAPID_PRIVATE_KEY', ''):
        return
    if not user_id:
        return
    if getattr(settings, 'WEB_PUSH_ASSINCRONO', True):
        threading.Thread(
            target=_disparar_web_push_worker,
            args=(user_id, titulo, mensagem, url),
            daemon=True,
        ).start()
    else:
        _disparar_web_push_worker(user_id, titulo, mensagem, url)


@receiver(post_save, sender=Ticket)
def notificar_ticket_event(sender, instance, created, **kwargs):
    canal_global = ['fila-global']
    canal_ticket = [f'ticket-{instance.id}']
    url_ticket = f'/tickets/{instance.id}/'

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

        # Web Push nativo: avisa a EQUIPE TÉCNICA (quem atende a fila).
        tecnicos = User.objects.filter(
            Q(is_technician=True) | Q(is_superuser=True)
        ).exclude(id=instance.solicitante_id).values_list('id', flat=True)
        for tecnico_id in tecnicos:
            _enviar_web_push(
                tecnico_id,
                'Central de Chamados',
                f'Novo chamado #{instance.id}: {instance.titulo}',
                url_ticket,
            )
    else:
        if instance.status == Ticket.Status.CANCELADO:
            evento, acao = 'ticket_cancelado', 'ticket_cancelado'
            mensagem_push = f'Chamado #{instance.id} cancelado'
        else:
            evento, acao = 'ticket_atualizado', 'ticket_atualizado'
            mensagem_push = f'Chamado #{instance.id} atualizado'

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

        # Web Push: solicitante + técnico responsável, sem eco para o autor.
        envolvidos = {instance.solicitante_id}
        if instance.tecnico_responsavel_id:
            envolvidos.add(instance.tecnico_responsavel_id)
        envolvidos.discard(_actor_id.get())
        for usuario_id in envolvidos:
            _enviar_web_push(usuario_id, 'Central de Chamados', mensagem_push, url_ticket)


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

        # Web Push nativo: avisa os envolvidos, sem eco para quem escreveu.
        envolvidos = destinatario_ids - {instance.autor_id}
        for usuario_id in envolvidos:
            _enviar_web_push(
                usuario_id,
                'Central de Chamados',
                f'Nova mensagem no chamado #{ticket.id}',
                f'/tickets/{ticket.id}/',
            )
