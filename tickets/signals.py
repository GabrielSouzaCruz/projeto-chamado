from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Ticket, Comentario

@receiver(post_save, sender=Ticket)
def notificar_ticket_event(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    
    if created:
        # Quando um novo ticket é criado
        mensagem = f"Novo chamado aberto: #{instance.id} - {instance.titulo}"
        tipo = 'info'
    else:
        # Quando um ticket existente é alterado (ex: cancelado, assumido, status mudou)
        if instance.status == 'cancelado':
            mensagem = f"O chamado #{instance.id} foi cancelado!"
            tipo = 'danger'
        else:
            mensagem = f"O chamado #{instance.id} foi atualizado ({instance.get_status_display()})."
            tipo = 'info'

    # Dispara para todo mundo via WebSocket
    async_to_sync(channel_layer.group_send)(
        'notificacoes_globais',
        {
            'type': 'enviar_alerta',
            'mensagem': mensagem,
            'tipo': tipo,
            'ticket_id': instance.id  # 💡 A PEÇA QUE FALTAVA!
        }
    )

@receiver(post_save, sender=Comentario)
def notificar_novo_comentario(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        mensagem = f"Nova mensagem no chamado #{instance.ticket.id} por {instance.autor.username}"
        
        async_to_sync(channel_layer.group_send)(
            'notificacoes_globais',
            {
                'type': 'enviar_alerta',
                'mensagem': mensagem,
                'tipo': 'success',
                'ticket_id': instance.ticket.id  # 💡 AQUI TAMBÉM (via relação)
            }
        )