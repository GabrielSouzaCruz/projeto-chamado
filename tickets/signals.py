# tickets/signals.py

from django.db.models.signals import post_save

from django.dispatch import receiver

from django.core.mail import EmailMultiAlternatives

from django.template.loader import render_to_string

from django.conf import settings

from django.urls import reverse

from .models import Ticket, Comentario

 

 

def get_absolute_url(request, ticket_id):

    """Gera URL absoluta para o ticket."""

    relative_url = reverse('tickets:detail', kwargs={'pk': ticket_id})

    return request.build_absolute_uri(relative_url) if hasattr(request, 'build_absolute_uri') \
    else f"http://{settings.ALLOWED_HOSTS[0]}{relative_url}"

 

 

def enviar_email_notificacao(destinatarios, assunto, template_name, contexto):

    """

    Envia email HTML para lista de destinatários.

    """

    from_email = settings.DEFAULT_FROM_EMAIL

    

    # Renderiza versão texto e HTML

    texto = render_to_string(f'emails/{template_name}.txt', contexto)

    html = render_to_string(f'emails/{template_name}.html', contexto)

    

    msg = EmailMultiAlternatives(assunto, texto, from_email, destinatarios)

    msg.attach_alternative(html, 'text/html')

    

    try:

        msg.send()

        return True

    except Exception as e:

        print(f"Erro ao enviar email: {e}")

        return False

 

 

@receiver(post_save, sender=Ticket)

def notificar_novo_ticket(sender, instance, created, **kwargs):

    """Envia email quando um novo ticket é criado."""

    if created:

        # Notifica todos os técnicos ativos

        from accounts.models import User

        tecnicos = User.objects.filter(

            is_technician=True, 

            is_active=True,

            email__isnull=False

        ).exclude(email='').values_list('email', flat=True)
        if tecnicos:

            contexto = {

                'ticket': instance,

                'solicitante': instance.solicitante,

                'titulo': f'Novo Chamado #{instance.id}: {instance.titulo}',

            }

            enviar_email_notificacao(

                list(tecnicos),

                f'[Chamados] Novo Ticket #{instance.id}',

                'novo_ticket',

                contexto

            )

 

 

@receiver(post_save, sender=Ticket)

def notificar_mudanca_status(sender, instance, created, **kwargs):

    """Envia email quando o status do ticket muda."""

    if not created and instance.tracker.has_changed('status'):

        # Notifica o solicitante

        if instance.solicitante.email:

            contexto = {

                'ticket': instance,

                'novo_status': instance.get_status_display(),

            }

            enviar_email_notificacao(

                [instance.solicitante.email],

                f'[Chamados] Status atualizado - Ticket #{instance.id}',

                'mudanca_status',

                contexto

            )

 

 

@receiver(post_save, sender=Comentario)

def notificar_novo_comentario(sender, instance, created, **kwargs):

    """Envia email quando um comentário público é adicionado."""

    if created and not instance.interno:

        ticket = instance.ticket
        destinatarios = []

        

        # Sempre notifica o solicitante (exceto se ele for o autor)

        if ticket.solicitante.email and ticket.solicitante != instance.autor:

            destinatarios.append(ticket.solicitante.email)

        

        # Se quem comentou é o solicitante, notifica o técnico responsável

        if instance.autor == ticket.solicitante and ticket.tecnico_responsavel:

            if ticket.tecnico_responsavel.email:

                destinatarios.append(ticket.tecnico_responsavel.email)

        

        if destinatarios:

            contexto = {

                'ticket': ticket,

                'comentario': instance,

                'autor': instance.autor,

            }

            enviar_email_notificacao(

                destinatarios,

                f'[Chamados] Novo comentário no Ticket #{ticket.id}',

                'novo_comentario',

                contexto

            )