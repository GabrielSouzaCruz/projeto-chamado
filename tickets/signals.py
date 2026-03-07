# tickets/signals.py
"""
Signals do app tickets.

Nota: Notificações por e-mail estão desabilitadas intencionalmente.
Para reativar: descomente as funções de envio e os receivers correspondentes.
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Ticket


@receiver(pre_save, sender=Ticket)
def salvar_status_antigo(sender, instance, **kwargs):
    """
    Armazena o status anterior do ticket antes de salvar.
    
    Por que isso é necessário?
    - Django não fornece nativamente acesso ao valor antigo de um campo
    - Este signal permite comparar status_antigo vs status_novo em post_save
    - Usado para detectar mudanças de status sem bibliotecas extras
    
    Funcionamento:
    1. Executa ANTES do save() do modelo
    2. Busca o registro atual no banco (se já existir)
    3. Armazena o status antigo em instance._status_antigo (atributo temporário)
    4. O valor fica disponível para outros signals ou lógica pós-save
    """
    if instance.pk:
        try:
            antigo = Ticket.objects.get(pk=instance.pk)
            instance._status_antigo = antigo.status
        except Ticket.DoesNotExist:
            instance._status_antigo = None