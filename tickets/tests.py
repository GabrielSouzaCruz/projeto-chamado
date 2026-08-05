from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Categoria, Comentario, Ticket
from .services import (
    adicionar_comentario_service,
    alterar_status_ticket_service,
    assumir_ticket_service,
    cancelar_ticket_service,
)

User = get_user_model()

# Usa o channel layer em memória para os testes não dependerem de Redis.
MEMORIA_CHANNEL_LAYERS = {
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
}


class FakeChannelLayer:
    """Channel layer fake cujo group_send é async (como no Redis de verdade)."""

    def __init__(self):
        self.calls = []

    async def group_send(self, group, message):
        self.calls.append((group, message))


@override_settings(CHANNEL_LAYERS=MEMORIA_CHANNEL_LAYERS)
class BaseChamadoTest(TestCase):
    """Configuração comum: usuários, categoria e criação de chamados."""

    def setUp(self):
        self.solicitante = User.objects.create_user(username='fulano', password='senha123')
        self.outro_usuario = User.objects.create_user(username='beltrano', password='senha123')
        self.tecnico = User.objects.create_user(
            username='tecnico1', password='senha123', is_technician=True
        )
        self.superuser = User.objects.create_superuser(
            username='admin', password='senha123', email='admin@example.com'
        )
        self.categoria = Categoria.objects.create(nome='Hardware')

    def criar_ticket(self, status=Ticket.Status.ABERTO, solicitante=None):
        return Ticket.objects.create(
            titulo='PC não liga',
            descricao='O computador não liga de jeito nenhum.',
            solicitante=solicitante or self.solicitante,
            categoria=self.categoria,
            status=status,
        )


class TesteSinais(BaseChamadoTest):
    """Valida que os signals disparam corretamente via WebSocket."""

    def test_ticket_criado_dispara_notificacao_globais(self):
        fake = FakeChannelLayer()
        with patch('tickets.signals.get_channel_layer', return_value=fake):
            ticket = self.criar_ticket()

        self.assertEqual(len(fake.calls), 1)
        grupo, mensagem = fake.calls[0]
        self.assertEqual(grupo, 'notificacoes_globais')
        self.assertEqual(mensagem['type'], 'enviar_alerta')
        self.assertEqual(mensagem['tipo'], 'info')
        self.assertEqual(mensagem['ticket_id'], ticket.id)
        self.assertIn(ticket.titulo, mensagem['mensagem'])

    def test_ticket_cancelado_dispara_tipo_danger(self):
        ticket = self.criar_ticket()
        fake = FakeChannelLayer()
        with patch('tickets.signals.get_channel_layer', return_value=fake):
            ticket.status = Ticket.Status.CANCELADO
            ticket.save()

        self.assertEqual(len(fake.calls), 1)
        grupo, mensagem = fake.calls[0]
        self.assertEqual(grupo, 'notificacoes_globais')
        self.assertEqual(mensagem['tipo'], 'danger')
        self.assertEqual(mensagem['ticket_id'], ticket.id)

    def test_comentario_criado_dispara_notificacao_com_ticket_id(self):
        ticket = self.criar_ticket()
        fake = FakeChannelLayer()
        with patch('tickets.signals.get_channel_layer', return_value=fake):
            Comentario.objects.create(
                ticket=ticket, autor=self.solicitante, mensagem='Preciso de ajuda.'
            )

        self.assertEqual(len(fake.calls), 1)
        grupo, mensagem = fake.calls[0]
        self.assertEqual(grupo, 'notificacoes_globais')
        self.assertEqual(mensagem['tipo'], 'success')
        self.assertEqual(mensagem['ticket_id'], ticket.id)
        self.assertIn(str(ticket.id), mensagem['mensagem'])


class TesteServicos(BaseChamadoTest):
    """Valida as regras de negócio do service layer."""

    def test_assumir_ticket_aberto_vira_em_andamento(self):
        ticket = self.criar_ticket()
        assumir_ticket_service(ticket.id, self.tecnico)

        ticket.refresh_from_db()
        self.assertEqual(ticket.tecnico_responsavel, self.tecnico)
        self.assertEqual(ticket.status, Ticket.Status.EM_ANDAMENTO)

    def test_assumir_ticket_ja_em_andamento_preserva_status(self):
        ticket = self.criar_ticket(status=Ticket.Status.EM_ANDAMENTO)
        ticket.tecnico_responsavel = self.superuser
        ticket.save()

        assumir_ticket_service(ticket.id, self.tecnico)

        ticket.refresh_from_db()
        self.assertEqual(ticket.tecnico_responsavel, self.tecnico)
        self.assertEqual(ticket.status, Ticket.Status.EM_ANDAMENTO)

    def test_assuncoes_sequenciais_mantem_um_unico_responsavel(self):
        ticket = self.criar_ticket()
        assumir_ticket_service(ticket.id, self.tecnico)
        assumir_ticket_service(ticket.id, self.superuser)

        ticket.refresh_from_db()
        self.assertEqual(ticket.tecnico_responsavel, self.superuser)
        self.assertEqual(ticket.status, Ticket.Status.EM_ANDAMENTO)

    def test_alterar_para_resolvido_registra_resolvido_em(self):
        ticket = self.criar_ticket()
        alterar_status_ticket_service(ticket.id, Ticket.Status.RESOLVIDO)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.RESOLVIDO)
        self.assertIsNotNone(ticket.resolvido_em)

    def test_alterar_resolvido_nao_sobrescreve_data_anterior(self):
        ticket = self.criar_ticket()
        alterar_status_ticket_service(ticket.id, Ticket.Status.RESOLVIDO)

        data_primeira = Ticket.objects.get(pk=ticket.pk).resolvido_em
        alterar_status_ticket_service(ticket.id, Ticket.Status.ABERTO)
        alterar_status_ticket_service(ticket.id, Ticket.Status.RESOLVIDO)

        ticket.refresh_from_db()
        self.assertEqual(ticket.resolvido_em, data_primeira)

    def test_alterar_para_aberto_nao_registra_resolvido_em(self):
        ticket = self.criar_ticket()
        alterar_status_ticket_service(ticket.id, Ticket.Status.ABERTO)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.ABERTO)
        self.assertIsNone(ticket.resolvido_em)

    def test_cancelar_ticket_altera_status(self):
        ticket = self.criar_ticket()
        cancelar_ticket_service(ticket.id)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.CANCELADO)

    def test_adicionar_comentario_vincula_ao_ticket(self):
        ticket = self.criar_ticket()
        comentario = adicionar_comentario_service(
            ticket.id,
            self.solicitante,
            {'mensagem': 'Atualização do problema', 'interno': False},
        )

        self.assertEqual(comentario.ticket, ticket)
        self.assertEqual(comentario.autor, self.solicitante)
        self.assertEqual(comentario.mensagem, 'Atualização do problema')
        self.assertFalse(comentario.interno)


class TesteMiniAPIs(BaseChamadoTest):
    """Valida o controle de acesso das mini-APIs HTML-over-the-wire."""

    def test_dashboard_cards_usuario_comum_recebe_200(self):
        self.client.force_login(self.solicitante)
        resp = self.client.get(reverse('tickets:api_dashboard_cards'))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="stat-total"')

    def test_dashboard_table_usuario_comum_recebe_200(self):
        self.client.force_login(self.solicitante)
        resp = self.client.get(reverse('tickets:api_dashboard_table'))

        self.assertEqual(resp.status_code, 200)

    def test_dashboard_cards_usuario_comum_ve_apenas_os_proprios(self):
        self.criar_ticket(solicitante=self.solicitante)
        self.criar_ticket(solicitante=self.outro_usuario)

        self.client.force_login(self.solicitante)
        resp = self.client.get(reverse('tickets:api_dashboard_cards'))

        self.assertContains(resp, 'id="stat-total"')
        self.assertContains(resp, '<h2 class="fw-bold mb-0 text-dark" id="stat-total">1</h2>')

    def test_fila_admin_usuario_comum_recebe_403(self):
        self.client.force_login(self.solicitante)
        resp = self.client.get(reverse('tickets:api_fila_admin_rows'))

        self.assertEqual(resp.status_code, 403)
        self.assertIn('error', resp.json())

    def test_fila_admin_tecnico_recebe_200(self):
        ticket = self.criar_ticket()
        self.client.force_login(self.tecnico)
        resp = self.client.get(reverse('tickets:api_fila_admin_rows'))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'#{ticket.id}')
        self.assertContains(resp, ticket.titulo)

    def test_fila_admin_superuser_recebe_200(self):
        ticket = self.criar_ticket()
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse('tickets:api_fila_admin_rows'))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'#{ticket.id}')

    def test_status_badge_dono_recebe_200(self):
        ticket = self.criar_ticket()
        self.client.force_login(self.solicitante)
        resp = self.client.get(reverse('tickets:ticket_status_badge_partial', args=[ticket.pk]))

        self.assertEqual(resp.status_code, 200)

    def test_status_badge_tecnico_recebe_200(self):
        ticket = self.criar_ticket()
        self.client.force_login(self.tecnico)
        resp = self.client.get(reverse('tickets:ticket_status_badge_partial', args=[ticket.pk]))

        self.assertEqual(resp.status_code, 200)

    def test_status_badge_outro_usuario_comum_recebe_403(self):
        ticket = self.criar_ticket()
        self.client.force_login(self.outro_usuario)
        resp = self.client.get(reverse('tickets:ticket_status_badge_partial', args=[ticket.pk]))

        self.assertEqual(resp.status_code, 403)
        self.assertIn('error', resp.json())

    def test_comentarios_dono_recebe_200(self):
        ticket = self.criar_ticket()
        self.client.force_login(self.solicitante)
        resp = self.client.get(reverse('tickets:ticket_comentarios_partial', args=[ticket.id]))

        self.assertEqual(resp.status_code, 200)

    def test_comentarios_outro_usuario_comum_recebe_403(self):
        ticket = self.criar_ticket()
        self.client.force_login(self.outro_usuario)
        resp = self.client.get(reverse('tickets:ticket_comentarios_partial', args=[ticket.id]))

        self.assertEqual(resp.status_code, 403)
        self.assertIn('error', resp.json())
