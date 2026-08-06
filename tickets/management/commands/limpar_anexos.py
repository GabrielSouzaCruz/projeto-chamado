"""Remove anexos antigos para liberar armazenamento.

Regra de política:
- Anexos de comentários são removidos quando o comentário tem mais de ``--dias``.
- Anexo inicial do chamado é removido apenas quando o chamado está finalizado
  (resolvido/cancelado) há mais de ``--dias`` — preserva evidência de chamados ativos.

Uso em produção (Render Cron / agendador):
    python manage.py limpar_anexos --dias 30
"""

import datetime
import traceback

from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.models import Comentario, Ticket


class Command(BaseCommand):
    help = 'Remove anexos antigos dos chamados e comentários.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Idade (dias) a partir da qual o anexo é removido. Padrão: 30.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas lista o que seria removido, sem apagar nada.',
        )

    def handle(self, *args, **options):
        dias = options['dias']
        dry = options['dry_run']
        corte = timezone.now() - datetime.timedelta(days=dias)

        comentarios = Comentario.objects.filter(
            anexo__isnull=False,
            criado_em__lt=corte,
        ).exclude(anexo='')

        tickets = Ticket.objects.filter(
            anexo__isnull=False,
            status__in=[Ticket.Status.RESOLVIDO, Ticket.Status.CANCELADO],
            criado_em__lt=corte,
        ).exclude(anexo='')

        removidos = 0
        removidos += self._limpar(comentarios, 'comentario', dry)
        removidos += self._limpar(tickets, 'chamado', dry)

        resultado = 'seria(m) removido(s)' if dry else 'removido(s)'
        self.stdout.write(self.style.SUCCESS(f'{removidos} anexo(s) {resultado}.'))

    def _limpar(self, queryset, rotulo, dry):
        removidos = 0
        for obj in queryset.iterator():
            anexo = getattr(obj, 'anexo')
            if not anexo:
                continue
            self.stdout.write(f'  - {rotulo} {obj.pk}: {anexo.name}')
            if not dry:
                try:
                    anexo.delete(save=True)
                    removidos += 1
                except Exception:
                    traceback.print_exc()
            else:
                removidos += 1
        return removidos