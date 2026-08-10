"""Cria os dados mínimos para rodar a suíte de testes E2E (Cypress).

A suíte intercepta TODAS as chamadas de dados via ``cy.intercept``, mas o
navegador ainda precisa de um documento renderizado e de um usuário real
para autenticar. Este comando garante um estado estável e idempotente:

- Usuário técnico  ``qa_tecnico``   (superusuário, tecnico) — senha ``qa-senha-123``
- Usuário comum    ``qa_solicitante`` — senha ``qa-senha-123``
- Chamado demo de ID fixo 1 (''Categoria'' também criada se faltar)

Uso:
    python manage.py seed_e2e

Rode ANTES de ``npx cypress open`` ou ``npm run test:e2e``.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from tickets.models import Categoria, Ticket


class Command(BaseCommand):
    help = 'Cria usuários e chamado demo para a suíte de testes E2E (Cypress).'

    def _criar_usuario(self, username, senha, **campos):
        User = get_user_model()
        usuario, _ = User.objects.get_or_create(username=username)
        usuario.is_active = True
        for campo, valor in campos.items():
            setattr(usuario, campo, valor)
        usuario.set_password(senha)
        usuario.save()
        return usuario

    def handle(self, *args, **options):
        User = get_user_model()

        # Usuários demo (idempotente: atualiza se já existirem)
        tecnico = self._criar_usuario(
            'qa_tecnico',
            'qa-senha-123',
            is_technician=True,
            is_staff=True,
            is_superuser=True,
            first_name='QA',
            last_name='Técnico',
        )
        solicitante = self._criar_usuario(
            'qa_solicitante',
            'qa-senha-123',
            is_technician=False,
            first_name='QA',
            last_name='Solicitante',
        )

        # Categoria (obrigatória no Ticket)
        categoria, _ = Categoria.objects.get_or_create(
            nome='Testes E2E',
            defaults={'descricao': 'Categoria criada pelo seed_e2e para testes automatizados.'},
        )

        # Chamado de ID fixo 1 — o Cypress visita /tickets/1/
        ticket, criado = Ticket.objects.get_or_create(
            id=1,
            defaults={
                'titulo': 'Chamado Demo E2E',
                'descricao': 'Chamado de teste criado pelo comando seed_e2e para a suíte Cypress.',
                'solicitante': solicitante,
                'categoria': categoria,
                'status': Ticket.Status.ABERTO,
                'prioridade': Ticket.Prioridade.ALTA,
            },
        )

        self.stdout.write(self.style.SUCCESS('Seed E2E concluído:'))
        self.stdout.write(f'  - Técnico:    {tecnico.username} / qa-senha-123')
        self.stdout.write(f'  - Solicitante: {solicitante.username} / qa-senha-123')
        if criado:
            self.stdout.write(self.style.SUCCESS(f'  - Chamado #{ticket.pk} criado (Demo E2E).'))
        else:
            self.stdout.write(f'  - Chamado #{ticket.pk} já existia (mantido).')
        self.stdout.write(self.style.SUCCESS(f'  - Categoria: {categoria.nome}'))

        total_tecnicos = User.objects.filter(is_technician=True).count()
        self.stdout.write(f'  (total de técnicos no banco: {total_tecnicos})')
