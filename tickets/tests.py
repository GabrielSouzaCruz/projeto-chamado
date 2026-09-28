from unittest.mock import patch, Mock
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse

from . import selectors
from .health import health_check_view
from .models import Categoria, Comentario, Ticket, PushSubscription
from .services import (
    adicionar_comentario_service,
    alterar_status_ticket_service,
    assumir_ticket_service,
    cancelar_ticket_service,
)
from .signals import _disparar_web_push_worker, _enviar_web_push, evento_do_usuario

from pywebpush import WebPushException

User = get_user_model()


class FakePusherClient:
    """Fake do client do Pusher, cujo trigger() registra os disparos."""

    def __init__(self):
        self.calls = []

    def trigger(self, canais, evento, dados):
        self.calls.append((canais, evento, dados))


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
    """Valida os eventos Pusher: novo_comentario no canal do ticket, e
    dashboard-update no canal global para criação/atualização/cancelamento."""

    def _com_pusher(self, fake):
        return patch.object(settings, 'PUSHER_CLIENT', fake)

    def test_ticket_criado_dispara_dashboard_update_no_global(self):
        fake = FakePusherClient()
        with self._com_pusher(fake):
            ticket = self.criar_ticket()

        canais_global = [c for c, e, _ in fake.calls if 'global-notifications' in c]
        self.assertEqual(len(canais_global), 1)
        _, evento, dados = fake.calls[0]
        self.assertEqual(evento, 'dashboard-update')
        self.assertEqual(dados['action'], 'ticket_created')
        self.assertEqual(dados['ticket_id'], ticket.id)

    def test_ticket_cancelado_dispara_dashboard_update_no_global(self):
        ticket = self.criar_ticket()
        fake = FakePusherClient()
        with self._com_pusher(fake):
            ticket.status = Ticket.Status.CANCELADO
            ticket.save()

        canais_global = [c for c, e, _ in fake.calls if 'global-notifications' in c]
        self.assertEqual(len(canais_global), 1)
        _, evento, dados = fake.calls[0]
        self.assertEqual(evento, 'dashboard-update')
        self.assertEqual(dados['status'], Ticket.Status.CANCELADO)

    def test_ticket_atualizado_dispara_dashboard_update_no_global(self):
        ticket = self.criar_ticket(status=Ticket.Status.EM_ANDAMENTO)
        fake = FakePusherClient()
        with self._com_pusher(fake):
            ticket.status = Ticket.Status.RESOLVIDO
            ticket.save()

        canais_global = [c for c, e, _ in fake.calls if 'global-notifications' in c]
        self.assertEqual(len(canais_global), 1)
        _, evento, dados = fake.calls[0]
        self.assertEqual(evento, 'dashboard-update')
        self.assertEqual(dados['status'], Ticket.Status.RESOLVIDO)

    def test_comentario_dispara_novo_comentario_e_dashboard_update(self):
        ticket = self.criar_ticket()
        fake = FakePusherClient()
        with self._com_pusher(fake):
            Comentario.objects.create(
                ticket=ticket, autor=self.solicitante, mensagem='Preciso de ajuda.'
            )

        canais_ticket = [c for c, _, _ in fake.calls if f'ticket-{ticket.id}' in c]
        canais_global = [c for c, _, _ in fake.calls if 'global-notifications' in c]
        self.assertEqual(len(canais_ticket), 1)
        self.assertEqual(len(canais_global), 1)

        _, evento, dados = fake.calls[0]
        self.assertEqual(evento, 'novo_comentario')
        self.assertEqual(dados['ticket_id'], ticket.id)
        self.assertEqual(dados['action'], 'novo_comentario')
        self.assertEqual(dados['remetente_nome'], self.solicitante.username)
        # Autor é removido da lista de destinatários (sem eco)
        self.assertNotIn(self.solicitante.id, dados['destinatario_ids'])

    def test_payload_comentario_inclui_titulo_do_chamado(self):
        """O título vai no payload de novo_comentario (exibido no chat)."""
        ticket = self.criar_ticket()
        fake = FakePusherClient()
        with self._com_pusher(fake):
            Comentario.objects.create(
                ticket=ticket, autor=self.tecnico, mensagem='Vou ver.'
            )

        eventos_ticket = [(e, d) for _, e, d in fake.calls if e == 'novo_comentario']
        self.assertEqual(len(eventos_ticket), 1)
        _, dados = eventos_ticket[0]
        self.assertEqual(dados['titulo'], ticket.titulo)

    def test_actor_id_do_comentario_e_o_autor(self):
        """actor_id aponta o autor do comentário (filtra o eco no frontend)."""
        ticket = self.criar_ticket()
        fake = FakePusherClient()
        with self._com_pusher(fake):
            Comentario.objects.create(
                ticket=ticket, autor=self.tecnico, mensagem='Vou verificar.'
            )

        eventos_ticket = [(e, d) for _, e, d in fake.calls if e == 'novo_comentario']
        _, dados = eventos_ticket[0]
        self.assertEqual(dados['actor_id'], self.tecnico.id)

    def test_destinatarios_incluem_solicitante_sem_eco_ao_autor(self):
        ticket = self.criar_ticket()
        ticket.tecnico_responsavel = self.tecnico
        ticket.save()
        fake = FakePusherClient()
        with self._com_pusher(fake):
            Comentario.objects.create(
                ticket=ticket, autor=self.tecnico, mensagem='Verificando.'
            )

        eventos_ticket = [(e, d) for _, e, d in fake.calls if e == 'novo_comentario']
        _, dados = eventos_ticket[0]
        self.assertIn(self.solicitante.id, dados['destinatario_ids'])
        self.assertNotIn(self.tecnico.id, dados['destinatario_ids'])  # autor removido


class TesteResumoNotificacoes(BaseChamadoTest):
    """Valida o endpoint de Polling do Sino (api_resumo_notificacoes)."""

    def setUp(self):
        super().setUp()
        self.url = reverse('tickets:api_resumo_notificacoes')

    def test_exige_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_solicitante_conta_mensagem_de_terceiros_no_seu_chamado(self):
        ticket = self.criar_ticket()
        Comentario.objects.create(ticket=ticket, autor=self.tecnico, mensagem='Oi')

        self.client.force_login(self.solicitante)
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['qtd'], 1)

    def test_solicitante_nao_conta_proprias_mensagens(self):
        ticket = self.criar_ticket()
        Comentario.objects.create(ticket=ticket, autor=self.solicitante, mensagem='Eu')

        self.client.force_login(self.solicitante)
        resp = self.client.get(self.url)

        self.assertEqual(resp.json()['qtd'], 0)

    def test_tecnico_conta_novo_chamado_aberto(self):
        self.criar_ticket()

        self.client.force_login(self.tecnico)
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['qtd'], 1)

    def test_comentario_interno_nao_conta_para_solicitante(self):
        ticket = self.criar_ticket()
        Comentario.objects.create(
            ticket=ticket, autor=self.tecnico, mensagem='Nota interna', interno=True
        )

        self.client.force_login(self.solicitante)
        resp = self.client.get(self.url)

        self.assertEqual(resp.json()['qtd'], 0)


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

    def test_comentarios_dono_versao_igual_retorna_204(self):
        ticket = self.criar_ticket()
        Comentario.objects.create(ticket=ticket, autor=self.solicitante, mensagem='Olá')
        comentarios = ticket.comentarios.filter(interno=False).order_by('criado_em', 'id')
        versao_atual = selectors.versao_de(comentarios, 'criado_em')
        from urllib.parse import quote
        self.client.force_login(self.solicitante)
        resp = self.client.get(
            reverse('tickets:ticket_comentarios_partial', args=[ticket.id]) + f'?versao={quote(versao_atual)}',
            HTTP_HX_Request='true',
        )
        self.assertEqual(resp.status_code, 204)

    def test_comentarios_dono_versao_diferente_retorna_200_com_container_e_versao_na_url(self):
        ticket = self.criar_ticket()
        self.client.force_login(self.solicitante)
        # Versão diferente da atual (vazia) para forçar mudança e renderização
        resp = self.client.get(
            reverse('tickets:ticket_comentarios_partial', args=[ticket.id]) + '?versao=diferente',
            HTTP_HX_Request='true',
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="comentarios-container"', html)
        self.assertIn('?versao=', html)

    def test_comentario_interno_ausente_no_partial_para_solicitante(self):
        """O parcial do container não exibe comentário interno para solicitante."""
        ticket = self.criar_ticket()
        Comentario.objects.create(
            ticket=ticket, autor=self.tecnico,
            mensagem='Nota interna sigilosa', interno=True,
        )
        self.client.force_login(self.solicitante)
        # Passar versão diferente para forçar renderização do container
        resp = self.client.get(
            reverse('tickets:ticket_comentarios_partial', args=[ticket.id]) + '?versao=diferente',
            HTTP_HX_Request='true',
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertNotIn('Nota interna sigilosa', html)

    def test_comentario_ajax_devolve_json_success(self):
        """O envio de comentário via AJAX devolve JSON limpo (sem redirect 302)."""
        ticket = self.criar_ticket()
        self.client.force_login(self.solicitante)
        resp = self.client.post(
            reverse('tickets:add_comment', args=[ticket.id]),
            data={'mensagem': 'Teste AJAX', 'interno': 'false'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'status': 'success'})
        self.assertTrue(ticket.comentarios.filter(mensagem='Teste AJAX').exists())

    def test_comentario_sem_ajax_redireciona(self):
        """Envio tradicional (não-AJAX) continua a redirecionar para o detalhe."""
        ticket = self.criar_ticket()
        self.client.force_login(self.solicitante)
        resp = self.client.post(
            reverse('tickets:add_comment', args=[ticket.id]),
            data={'mensagem': 'Teste normal', 'interno': 'false'},
        )

        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('tickets:detail', args=[ticket.id]))
        self.assertTrue(ticket.comentarios.filter(mensagem='Teste normal').exists())


class TesteFilaPermissoes(BaseChamadoTest):
    """Fila: @tecnico_required (sem @admin_required), filtro SSR
    ABERTO/EM_ANDAMENTO e ProprietarioOrTecnicoMixin liberando técnicos."""

    def _criar(self, titulo, status, solicitante=None):
        return Ticket.objects.create(
            titulo=titulo,
            descricao='Descrição do chamado para o teste.',
            solicitante=solicitante or self.solicitante,
            categoria=self.categoria,
            status=status,
        )

    def test_tecnico_nao_superuser_acessa_fila_com_200(self):
        self.client.force_login(self.tecnico)
        resp = self.client.get(reverse('tickets:fila_admin'))

        self.assertEqual(resp.status_code, 200)

    def test_fila_ssr_mostra_chamado_aberto_no_html_inicial(self):
        aberto = self._criar('Chamado Aberto SSR', Ticket.Status.ABERTO)
        self.client.force_login(self.tecnico)
        resp = self.client.get(reverse('tickets:fila_admin'))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, aberto.titulo)

    def test_fila_filtro_ssr_so_mostra_abertos_e_em_andamento(self):
        em_aberto = self._criar('Chamado em Aberto', Ticket.Status.ABERTO)
        em_andamento = self._criar('Chamado em Andamento', Ticket.Status.EM_ANDAMENTO)
        self._criar('Chamado Resolvido', Ticket.Status.RESOLVIDO)
        self._criar('Chamado Cancelado', Ticket.Status.CANCELADO)

        self.client.force_login(self.tecnico)
        resp = self.client.get(reverse('tickets:fila_admin'))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, em_aberto.titulo)
        self.assertContains(resp, em_andamento.titulo)
        self.assertNotContains(resp, 'Chamado Resolvido')
        self.assertNotContains(resp, 'Chamado Cancelado')

        statuses = set(resp.context['tickets'].values_list('status', flat=True))
        self.assertEqual(
            statuses, {Ticket.Status.ABERTO, Ticket.Status.EM_ANDAMENTO}
        )

    def test_fila_usuario_comum_e_redirecionado(self):
        self.client.force_login(self.solicitante)
        resp = self.client.get(reverse('tickets:fila_admin'))

        self.assertRedirects(
            resp, reverse('tickets:dashboard'), fetch_redirect_response=False
        )

    def test_tecnico_nao_dono_acessa_detalhe(self):
        ticket = self._criar('Chamado de Outro', Ticket.Status.ABERTO)
        self.client.force_login(self.tecnico)
        resp = self.client.get(reverse('tickets:detail', args=[ticket.pk]))

        self.assertEqual(resp.status_code, 200)

    def test_tecnico_nao_dono_acessa_edicao(self):
        ticket = self._criar('Chamado de Outro Edit', Ticket.Status.ABERTO)
        self.client.force_login(self.tecnico)
        resp = self.client.get(reverse('tickets:update', args=[ticket.pk]))

        self.assertEqual(resp.status_code, 200)

    def test_outro_comum_nao_dono_continua_redirecionado(self):
        ticket = self._criar('Chamado do Fulano', Ticket.Status.ABERTO)
        self.client.force_login(self.outro_usuario)
        resp = self.client.get(reverse('tickets:detail', args=[ticket.pk]))

        self.assertRedirects(
            resp, reverse('tickets:dashboard'), fetch_redirect_response=False
        )


class TestePushSubscriptionAPI(BaseChamadoTest):
    """Valida a API POST /api/save-push-subscription/ (Web Push nativo)."""

    def setUp(self):
        super().setUp()
        self.url = reverse('save_push_subscription')
        self.payload = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/xyz123',
            'keys': {'p256dh': 'B' * 87, 'auth': 'A' * 22},
        }

    def _post(self, dados):
        return self.client.post(
            self.url, json.dumps(dados), content_type='application/json'
        )

    def test_exige_login(self):
        resp = self._post(self.payload)
        self.assertEqual(resp.status_code, 302)

    def test_salva_inscricao_do_usuario(self):
        self.client.force_login(self.solicitante)
        resp = self._post(self.payload)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])
        inscricao = PushSubscription.objects.get(user=self.solicitante)
        self.assertEqual(inscricao.endpoint, self.payload['endpoint'])
        self.assertEqual(inscricao.p256dh, 'B' * 87)
        self.assertEqual(inscricao.auth, 'A' * 22)

    def test_mesmo_endpoint_nao_duplica(self):
        self.client.force_login(self.solicitante)
        self._post(self.payload)
        self._post(self.payload)

        self.assertEqual(PushSubscription.objects.filter(user=self.solicitante).count(), 1)

    def test_chaves_planas_tambem_sao_aceitas(self):
        self.client.force_login(self.solicitante)
        resp = self._post({'endpoint': 'https://fcm.googleapis.com/fcm/send/plano',
                           'p256dh': 'C' * 87, 'auth': 'D' * 22})

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(PushSubscription.objects.filter(user=self.solicitante).exists())

    def test_dados_incompletos_retorna_400(self):
        self.client.force_login(self.solicitante)
        resp = self._post({'endpoint': 'https://fcm.googleapis.com/fcm/send/incompleto'})

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PushSubscription.objects.exists())

    def test_json_invalido_retorna_400(self):
        self.client.force_login(self.solicitante)
        resp = self.client.post(self.url, data='{nao-é-json', content_type='application/json')

        self.assertEqual(resp.status_code, 400)

    def test_get_retorna_405(self):
        self.client.force_login(self.solicitante)
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 405)

    # -- SSRF: allowlist de hosts de push --

    def test_endpoint_http_interno_retorna_400(self):
        self.client.force_login(self.solicitante)
        resp = self._post({**self.payload, 'endpoint': 'http://127.0.0.1/push'})

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])
        self.assertFalse(PushSubscription.objects.exists())

    def test_endpoint_host_falso_com_path_de_fcm_retorna_400(self):
        self.client.force_login(self.solicitante)
        resp = self._post({**self.payload, 'endpoint': 'https://evil.com/fcm.googleapis.com'})

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PushSubscription.objects.exists())

    def test_endpoint_host_sufixado_malicioso_retorna_400(self):
        self.client.force_login(self.solicitante)
        resp = self._post({**self.payload, 'endpoint': 'https://fcm.googleapis.com.evil.com/fcm/send/x'})

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PushSubscription.objects.exists())

    def test_endpoint_fcm_valido_retorna_200(self):
        self.client.force_login(self.solicitante)
        resp = self._post({**self.payload, 'endpoint': 'https://fcm.googleapis.com/fcm/send/x'})

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])

    def test_endpoint_sufixos_confiables_retornam_200(self):
        self.client.force_login(self.solicitante)
        endpoints = [
            'https://updates.push.services.mozilla.com/wpush/v2/abc',
            'https://db3.notify.windows.com/canaldenotificacao',
            'https://web.push.apple.com/QWxhZG8',
        ]
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                resp = self._post({**self.payload, 'endpoint': endpoint})
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(resp.json()['ok'])


class TesteWebPush(BaseChamadoTest):
    """Valida o disparo de Web Push nativo (VAPID) e o cleanup de 410 Gone."""

    def _criar_inscricao(self, user, endpoint='https://push.example.com/abc'):
        return PushSubscription.objects.create(
            user=user, endpoint=endpoint, p256dh='B' * 87, auth='A' * 22
        )

    def test_410_gone_remove_a_inscricao(self):
        inscricao = self._criar_inscricao(self.solicitante)
        with patch('tickets.signals.webpush') as wp:
            wp.side_effect = WebPushException('Gone', response=Mock(status_code=410))
            _disparar_web_push_worker(self.solicitante.id, 'T', 'M', '/tickets/1/')

        self.assertFalse(PushSubscription.objects.filter(pk=inscricao.pk).exists())

    def test_404_not_found_remove_a_inscricao(self):
        inscricao = self._criar_inscricao(self.solicitante)
        with patch('tickets.signals.webpush') as wp:
            wp.side_effect = WebPushException('Not Found', response=Mock(status_code=404))
            _disparar_web_push_worker(self.solicitante.id, 'T', 'M', '/tickets/1/')

        self.assertFalse(PushSubscription.objects.filter(pk=inscricao.pk).exists())

    def test_outro_erro_mantem_a_inscricao(self):
        inscricao = self._criar_inscricao(self.solicitante)
        with patch('tickets.signals.webpush') as wp:
            wp.side_effect = WebPushException('Falha', response=Mock(status_code=500))
            _disparar_web_push_worker(self.solicitante.id, 'T', 'M', '/tickets/1/')

        self.assertTrue(PushSubscription.objects.filter(pk=inscricao.pk).exists())

    def test_sucesso_envia_payload_json_para_todas_as_inscricoes(self):
        inscricao = self._criar_inscricao(self.solicitante)
        self._criar_inscricao(self.solicitante, endpoint='https://push.example.com/outro')

        with patch('tickets.signals.webpush') as wp:
            _disparar_web_push_worker(self.solicitante.id, 'Título', 'Mensagem', '/tickets/5/')

        self.assertEqual(wp.call_count, 2)
        args, kwargs = wp.call_args_list[0]
        self.assertEqual(kwargs['subscription_info']['endpoint'], inscricao.endpoint)
        self.assertEqual(kwargs['subscription_info']['keys']['p256dh'], inscricao.p256dh)
        payload = json.loads(kwargs['data'])
        self.assertEqual(payload, {
            'title': 'Título',
            'body': 'Mensagem',
            'url': '/tickets/5/',
            'tag': 'ticket-5',
            'renotify': True,
            'actions': [{'action': 'abrir_chamado', 'title': 'Abrir Chamado'}],
            'unread_count': 0,
        })
        expected_sub = settings.VAPID_ADMIN_EMAIL if settings.VAPID_ADMIN_EMAIL.startswith('mailto:') else f'mailto:{settings.VAPID_ADMIN_EMAIL}'
        self.assertEqual(kwargs['vapid_claims'], {'sub': expected_sub})

    def test_vapid_admin_email_vazio_usa_fallback(self):
        """VAPID_ADMIN_EMAIL vazio → fallback 'mailto:admin@localhost.com'."""
        inscricao = self._criar_inscricao(self.solicitante)
        with (
            patch('tickets.signals.webpush') as wp,
            patch.object(settings, 'VAPID_ADMIN_EMAIL', ''),
        ):
            _disparar_web_push_worker(self.solicitante.id, 'T', 'M', '/tickets/5/')

        args, kwargs = wp.call_args_list[0]
        self.assertEqual(kwargs['vapid_claims'], {'sub': 'mailto:admin@localhost.com'})

    def test_vapid_admin_email_ja_normalizado_mantem_prefixo(self):
        """VAPID_ADMIN_EMAIL já com 'mailto:' não é duplicado."""
        inscricao = self._criar_inscricao(self.solicitante)
        with (
            patch('tickets.signals.webpush') as wp,
            patch.object(settings, 'VAPID_ADMIN_EMAIL', 'mailto:admin@example.com'),
        ):
            _disparar_web_push_worker(self.solicitante.id, 'T', 'M', '/tickets/5/')

        args, kwargs = wp.call_args_list[0]
        self.assertEqual(kwargs['vapid_claims'], {'sub': 'mailto:admin@example.com'})

    def test_sem_chaves_vapid_nao_dispara_nada(self):
        self._criar_inscricao(self.solicitante)
        with (
            patch('tickets.signals.webpush') as wp,
            patch.object(settings, 'VAPID_PUBLIC_KEY', ''),
            patch.object(settings, 'VAPID_PRIVATE_KEY', ''),
        ):
            _enviar_web_push(self.solicitante.id, 'T', 'M', '/tickets/1/')

        wp.assert_not_called()

    def test_novo_ticket_push_para_tecnicos_sem_eco_ao_solicitante(self):
        with (
            patch('tickets.signals._enviar_web_push') as envia,
            patch.object(settings, 'VAPID_PUBLIC_KEY', 'pub'),
            patch.object(settings, 'VAPID_PRIVATE_KEY', 'priv'),
        ):
            ticket = self.criar_ticket()

        ids = [call.args[0] for call in envia.call_args_list]
        self.assertIn(self.tecnico.id, ids)
        self.assertIn(self.superuser.id, ids)
        self.assertNotIn(self.solicitante.id, ids)
        payload_url = envia.call_args.args[3]
        self.assertEqual(payload_url, f'/tickets/{ticket.id}/')

    def test_comentario_push_para_envolvidos_sem_eco_ao_autor(self):
        ticket = self.criar_ticket()
        ticket.tecnico_responsavel = self.tecnico
        ticket.save()

        with (
            patch('tickets.signals._enviar_web_push') as envia,
            patch.object(settings, 'VAPID_PUBLIC_KEY', 'pub'),
            patch.object(settings, 'VAPID_PRIVATE_KEY', 'priv'),
        ):
            Comentario.objects.create(ticket=ticket, autor=self.solicitante, mensagem='Olá')

        ids = [call.args[0] for call in envia.call_args_list]
        self.assertIn(self.tecnico.id, ids)
        self.assertNotIn(self.solicitante.id, ids)

    def test_cancelamento_push_para_solicitante_e_tecnico_sem_eco_ao_autor(self):
        ticket = self.criar_ticket()
        ticket.tecnico_responsavel = self.tecnico
        ticket.save()

        with (
            patch('tickets.signals._enviar_web_push') as envia,
            patch.object(settings, 'VAPID_PUBLIC_KEY', 'pub'),
            patch.object(settings, 'VAPID_PRIVATE_KEY', 'priv'),
        ):
            with patch.object(settings, 'PUSHER_CLIENT', FakePusherClient()):
                with evento_do_usuario(self.tecnico):  # técnico executa o cancelamento
                    cancelar_ticket_service(ticket.id)

        ids = [call.args[0] for call in envia.call_args_list]
        self.assertIn(self.solicitante.id, ids)
        self.assertNotIn(self.tecnico.id, ids)  # técnico é o autor do cancelamento


# =============================================================================
# TESTES DE RATE LIMIT
# =============================================================================

from django.core.cache import cache
from django.test.client import Client


class TesteRateLimit(TestCase):

    def setUp(self):
        self.client = Client()
        self.solicitante = User.objects.create_user(
            username='solicitante.rl',
            password='senha-teste-123!',
            email='sol_rl@example.com',
            is_technician=False,
        )
        self.outro = User.objects.create_user(
            username='outro.rl',
            password='senha-teste-123!',
            email='outro_rl@example.com',
            is_technician=False,
        )
        self.categoria = Categoria.objects.create(nome='Teste RL')
        self.ticket = Ticket.objects.create(
            titulo='Ticket RL',
            descricao='Desc',
            solicitante=self.solicitante,
            categoria=self.categoria,
        )
        cache.clear()

    # -- TICKET CREATE --

    def test_10_criacoes_ok_11_bloqueada(self):
        self.client.login(username='solicitante.rl', password='senha-teste-123!')
        url = reverse('tickets:create')
        for i in range(10):
            resp = self.client.post(url, {
                'titulo': f'Ticket {i}',
                'descricao': 'Desc',
                'categoria': self.categoria.pk,
                'prioridade': 'media',
            })
            self.assertIn(resp.status_code, [302, 200], f'Iteracao {i} falhou')
        # 11a deve ser bloqueada
        resp = self.client.post(url, {
            'titulo': 'Ticket bloqueado',
            'descricao': 'Desc',
            'categoria': self.categoria.pk,
            'prioridade': 'media',
        })
        self.assertRedirects(resp, reverse('tickets:dashboard'), fetch_redirect_response=False)

    def test_usuarios_diferentes_nao_compartilham_contador(self):
        # Usuario 1: 10 criacoes
        self.client.login(username='solicitante.rl', password='senha-teste-123!')
        url = reverse('tickets:create')
        for i in range(10):
            self.client.post(url, {
                'titulo': f'Ticket {i}',
                'descricao': 'Desc',
                'categoria': self.categoria.pk,
                'prioridade': 'media',
            })
        # Usuario 2: ainda pode criar
        self.client.login(username='outro.rl', password='senha-teste-123!')
        resp = self.client.post(url, {
            'titulo': 'Ticket do outro',
            'descricao': 'Desc',
            'categoria': self.categoria.pk,
            'prioridade': 'media',
        })
        self.assertIn(resp.status_code, [302, 200])

    def test_apos_expirar_janela_criacao_liberada(self):
        self.client.login(username='solicitante.rl', password='senha-teste-123!')
        url = reverse('tickets:create')
        for i in range(10):
            self.client.post(url, {
                'titulo': f'Ticket {i}',
                'descricao': 'Desc',
                'categoria': self.categoria.pk,
                'prioridade': 'media',
            })
        # Forca expiracao do cache
        cache_key = f'rate_ticket_create_{self.solicitante.id}'
        cache.delete(cache_key)
        resp = self.client.post(url, {
            'titulo': 'Ticket pos-expiracao',
            'descricao': 'Desc',
            'categoria': self.categoria.pk,
            'prioridade': 'media',
        })
        self.assertIn(resp.status_code, [302, 200])

    # -- COMENTARIO --

    def test_30_comentarios_ok_31_bloqueada_ajax(self):
        self.client.login(username='solicitante.rl', password='senha-teste-123!')
        url = reverse('tickets:add_comment', args=[self.ticket.pk])
        for i in range(30):
            resp = self.client.post(
                url,
                {'mensagem': f'Comentario {i}'},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )
            self.assertIn(resp.status_code, [200, 302], f'Iteracao {i} falhou')
        # 31o deve retornar 429
        resp = self.client.post(
            url,
            {'mensagem': 'Bloqueado'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 429)

    def test_30_comentarios_ok_31_bloqueada_normal(self):
        self.client.login(username='solicitante.rl', password='senha-teste-123!')
        url = reverse('tickets:add_comment', args=[self.ticket.pk])
        for i in range(30):
            self.client.post(url, {'mensagem': f'Comentario {i}'})
        # 31o deve redirecionar
        resp = self.client.post(url, {'mensagem': 'Bloqueado'})
        self.assertRedirects(resp, reverse('tickets:detail', args=[self.ticket.pk]), fetch_redirect_response=False)

    def test_comentario_usuarios_diferentes_nao_compartilham(self):
        # Solicitante: 30 comentarios
        self.client.login(username='solicitante.rl', password='senha-teste-123!')
        url = reverse('tickets:add_comment', args=[self.ticket.pk])
        for i in range(30):
            self.client.post(url, {'mensagem': f'Comentario {i}'})
        # Tecnico no mesmo ticket: pode comentar (contator proprio)
        from accounts.models import User as UserModel
        tecnico = UserModel.objects.create_user(
            username='tecnico.rl',
            password='senha-teste-123!',
            email='tec_rl@example.com',
            is_technician=True,
        )
        self.client.login(username='tecnico.rl', password='senha-teste-123!')
        resp = self.client.post(url, {'mensagem': 'Comentario do tecnico'})
        self.assertIn(resp.status_code, [200, 302])


class TesteComentarioInterno(BaseChamadoTest):
    """Comentário interno só é visível para técnico/superusuário."""

    def setUp(self):
        super().setUp()
        self.outro_tecnico = User.objects.create_user(
            username='tecnico2', password='senha123', is_technician=True
        )
        self.ticket = self.criar_ticket()
        self.mensagem_publica = 'Resposta publica ao solicitante'
        self.mensagem_interna = 'Nota interna sigilosa'
        Comentario.objects.create(
            ticket=self.ticket, autor=self.tecnico, mensagem=self.mensagem_publica
        )
        Comentario.objects.create(
            ticket=self.ticket, autor=self.tecnico,
            mensagem=self.mensagem_interna, interno=True,
        )

    def _html(self, resp):
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    # -- DETALHE --

    def test_solicitante_nao_ve_comentario_interno_no_detalhe(self):
        self.client.force_login(self.solicitante)
        html = self._html(self.client.get(
            reverse('tickets:detail', args=[self.ticket.id])
        ))
        self.assertIn(self.mensagem_publica, html)
        self.assertNotIn(self.mensagem_interna, html)

    def test_tecnico_ve_comentario_interno_no_detalhe(self):
        ticket = self.criar_ticket(solicitante=self.tecnico)
        Comentario.objects.create(
            ticket=ticket, autor=self.outro_tecnico,
            mensagem=self.mensagem_interna, interno=True,
        )
        self.client.force_login(self.tecnico)
        html = self._html(self.client.get(
            reverse('tickets:detail', args=[ticket.id])
        ))
        self.assertIn(self.mensagem_interna, html)

    def test_superuser_ve_comentario_interno_no_detalhe(self):
        self.client.force_login(self.superuser)
        html = self._html(self.client.get(
            reverse('tickets:detail', args=[self.ticket.id])
        ))
        self.assertIn(self.mensagem_interna, html)

    # -- PARTIAL (AJAX) --

    def test_solicitante_nao_ve_comentario_interno_no_partial(self):
        self.client.force_login(self.solicitante)
        resp = self.client.get(
            reverse('tickets:ticket_comentarios_partial', args=[self.ticket.id])
        )
        html = self._html(resp)
        self.assertIn(self.mensagem_publica, html)
        self.assertNotIn(self.mensagem_interna, html)

    def test_tecnico_ve_comentario_interno_no_partial(self):
        self.client.force_login(self.tecnico)
        resp = self.client.get(
            reverse('tickets:ticket_comentarios_partial', args=[self.ticket.id])
        )
        self.assertIn(self.mensagem_interna, self._html(resp))

    def test_superuser_ve_comentario_interno_no_partial(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(
            reverse('tickets:ticket_comentarios_partial', args=[self.ticket.id])
        )
        self.assertIn(self.mensagem_interna, self._html(resp))

    # -- CRIAÇÃO --

    def test_post_solicitante_com_interno_on_salva_interno_false(self):
        self.client.force_login(self.solicitante)
        resp = self.client.post(
            reverse('tickets:add_comment', args=[self.ticket.id]),
            {'mensagem': 'Tentativa de nota interna', 'interno': 'on'},
        )
        self.assertEqual(resp.status_code, 302)
        comentario = Comentario.objects.get(mensagem='Tentativa de nota interna')
        self.assertFalse(comentario.interno)

    def test_post_tecnico_com_interno_on_salva_interno_true(self):
        self.client.force_login(self.tecnico)
        resp = self.client.post(
            reverse('tickets:add_comment', args=[self.ticket.id]),
            {'mensagem': 'Nota interna do tecnico', 'interno': 'on'},
        )
        self.assertEqual(resp.status_code, 302)
        comentario = Comentario.objects.get(mensagem='Nota interna do tecnico')
        self.assertTrue(comentario.interno)

    def test_post_superuser_com_interno_on_salva_interno_true(self):
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse('tickets:add_comment', args=[self.ticket.id]),
            {'mensagem': 'Nota interna do admin', 'interno': 'on'},
        )
        self.assertEqual(resp.status_code, 302)
        comentario = Comentario.objects.get(mensagem='Nota interna do admin')
        self.assertTrue(comentario.interno)

    def test_servico_forca_interno_false_para_nao_tecnico(self):
        comentario = adicionar_comentario_service(
            ticket_id=self.ticket.id,
            autor=self.solicitante,
            dados_comentario={'mensagem': 'Chamada direta ao servico', 'interno': True},
        )
        self.assertFalse(comentario.interno)

    def test_servico_preserva_interno_para_tecnico(self):
        comentario = adicionar_comentario_service(
            ticket_id=self.ticket.id,
            autor=self.tecnico,
            dados_comentario={'mensagem': 'Chamada direta tecnico', 'interno': True},
        )
        self.assertTrue(comentario.interno)

    # -- NOTIFICAÇÕES (SINO/GAVETA) --

    def test_resumo_solicitante_nao_conta_comentario_interno(self):
        ticket = self.criar_ticket()
        Comentario.objects.create(
            ticket=ticket, autor=self.tecnico,
            mensagem=self.mensagem_interna, interno=True,
        )
        self.client.force_login(self.solicitante)
        resp = self.client.get(reverse('tickets:api_resumo_notificacoes'))
        self.assertEqual(resp.status_code, 200)
        resumos = [
            item['resumo'] for item in resp.json()['items']
            if item['tipo'] == 'comentario'
        ]
        self.assertNotIn(self.mensagem_interna, resumos)
        self.assertEqual(len(resumos), 1)

    def test_resumo_tecnico_conta_comentario_interno(self):
        ticket = self.criar_ticket(status=Ticket.Status.RESOLVIDO, solicitante=self.tecnico)
        Comentario.objects.create(
            ticket=ticket, autor=self.outro_tecnico,
            mensagem=self.mensagem_interna, interno=True,
        )
        self.client.force_login(self.tecnico)
        resp = self.client.get(reverse('tickets:api_resumo_notificacoes'))
        self.assertEqual(resp.status_code, 200)
        resumos = [
            item['resumo'] for item in resp.json()['items']
            if item['tipo'] == 'comentario'
        ]
        self.assertIn(self.mensagem_interna, resumos)


class TesteAcoesSomentePost(BaseChamadoTest):
    """Ações de estado aceitam apenas POST: GET responde 405."""

    def setUp(self):
        super().setUp()
        self.ticket = self.criar_ticket()

    def test_get_cancelar_retorna_405(self):
        resp = self.client.get(reverse('tickets:cancelar', args=[self.ticket.id]))

        self.assertEqual(resp.status_code, 405)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.ABERTO)

    def test_get_apagar_retorna_405(self):
        resp = self.client.get(reverse('tickets:apagar', args=[self.ticket.id]))

        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Ticket.objects.filter(id=self.ticket.id).exists())

    def test_get_assumir_retorna_405(self):
        resp = self.client.get(reverse('tickets:take', args=[self.ticket.id]))

        self.assertEqual(resp.status_code, 405)

    def test_get_alterar_status_retorna_405(self):
        resp = self.client.get(reverse('tickets:change_status', args=[self.ticket.id]))

        self.assertEqual(resp.status_code, 405)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.ABERTO)

    def test_get_adicionar_comentario_retorna_405(self):
        resp = self.client.get(reverse('tickets:add_comment', args=[self.ticket.id]))

        self.assertEqual(resp.status_code, 405)
        self.assertEqual(self.ticket.comentarios.count(), 0)

    def test_post_cancelar_continua_funcionando(self):
        self.client.force_login(self.solicitante)
        resp = self.client.post(reverse('tickets:cancelar', args=[self.ticket.id]))

        self.assertEqual(resp.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CANCELADO)


class TesteFormPostNaFila(BaseChamadoTest):
    """Assumir chamado na fila é <form method="post"> com csrf, nunca <a href>."""

    def setUp(self):
        super().setUp()
        self.ticket = self.criar_ticket()
        self.client.force_login(self.tecnico)
        self.acao = reverse('tickets:take', args=[self.ticket.id])

    def test_partial_de_linhas_renderiza_form_post_com_csrf(self):
        resp = self.client.get(reverse('tickets:api_fila_admin_rows'))
        html = resp.content.decode()

        self.assertEqual(resp.status_code, 200)
        self.assertIn(f'<form method="post" action="{self.acao}"', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('<button type="submit"', html)
        self.assertNotIn(f'<a href="{self.acao}"', html)

    def test_nenhum_template_usa_href_para_as_acoes_post(self):
        from pathlib import Path

        rotas = (
            'tickets:take', 'tickets:cancelar', 'tickets:apagar',
            'tickets:change_status', 'tickets:add_comment',
        )
        raiz = Path(settings.BASE_DIR) / 'templates'

        for caminho in raiz.rglob('*.html'):
            linhas = caminho.read_text(encoding='utf-8').splitlines()
            for numero, linha in enumerate(linhas, 1):
                if 'href' not in linha:
                    continue
                for rota in rotas:
                    self.assertNotIn(
                        f"'{rota}'", linha,
                        f'{caminho}:{numero} declara href para {rota}',
                    )


class TesteEndurecimentoConfiguracao(BaseChamadoTest):
    """DEBUG vem da env (default False), ordenação do histórico usa whitelist
    e o health check não expõe a mensagem da exceção."""

    def _carregar_settings_isolado(self, **extras):
        """Reexecuta config/settings.py num módulo novo e sem a env herdada."""
        import importlib.util
        import os
        from pathlib import Path

        import config as pacote_config

        caminho = Path(pacote_config.__file__).resolve().parent / 'settings.py'
        spec = importlib.util.spec_from_file_location('config._settings_probe', caminho)
        modulo = importlib.util.module_from_spec(spec)

        with patch.dict(os.environ):  # devolve o ambiente original ao sair
            for chave in ('DEBUG', 'IS_PRODUCTION', 'SECRET_KEY', 'SENTRY_DSN'):
                os.environ.pop(chave, None)
            os.environ.update(extras)
            with patch('dotenv.load_dotenv'):  # ignora o .env da raiz
                spec.loader.exec_module(modulo)

        return modulo

    def test_sem_env_debug_o_settings_fica_false(self):
        self.assertFalse(self._carregar_settings_isolado().DEBUG)

    def test_env_debug_true_liga_o_debug(self):
        self.assertTrue(self._carregar_settings_isolado(DEBUG='true').DEBUG)

    def test_ordenar_fora_da_whitelist_usa_o_default(self):
        qs = selectors.get_historico_tickets({'ordenar': 'solicitante__password'})

        self.assertEqual(tuple(qs.query.order_by), ('-criado_em',))

    def test_ordenar_na_whitelist_e_aplicado(self):
        qs = selectors.get_historico_tickets({'ordenar': '-prioridade'})

        self.assertEqual(tuple(qs.query.order_by), ('-prioridade',))

    def test_ordenar_por_resolvido_em_e_aplicado(self):
        qs = selectors.get_historico_tickets({'ordenar': '-resolvido_em'})

        self.assertEqual(tuple(qs.query.order_by), ('-resolvido_em',))

        qs_asc = selectors.get_historico_tickets({'ordenar': 'resolvido_em'})

        self.assertEqual(tuple(qs_asc.query.order_by), ('resolvido_em',))

    def test_view_do_historico_sanitiza_o_parametro_ordenar(self):
        self.client.force_login(self.tecnico)
        resp = self.client.get(
            reverse('tickets:historico'), {'ordenar': 'solicitante__password'}
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['filtros']['ordenar'], '-criado_em')

    def test_health_com_banco_ok_retorna_200(self):
        resp = self.client.get(reverse('health_check'))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'status': 'healthy'})

    def test_health_com_banco_falhando_nao_expoe_a_mensagem(self):
        with patch('tickets.health.connection') as conexao:
            conexao.cursor.side_effect = Exception('senha-interna-123')
            with self.assertLogs('tickets', level='ERROR') as registros:
                resp = health_check_view(RequestFactory().get('/health/'))

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(json.loads(resp.content.decode()), {'status': 'unhealthy'})
        self.assertNotIn('senha-interna-123', resp.content.decode())
        self.assertTrue(
            any('Health check falhou' in linha for linha in registros.output)
        )


class Migracao0010Tests(TransactionTestCase):
    """0010 blindada: ticket com categoria NULL no estado 0009 vira
    'Não categorizado' antes do AlterField que torna a coluna NOT NULL."""

    estado_0009 = [('tickets', '0009_remover_rls')]
    estado_0010 = [(
        'tickets',
        '0010_alter_comentario_anexo_alter_ticket_anexo_and_more',
    )]

    def test_ticket_com_categoria_null_vira_nao_categorizado(self):
        usuario = User.objects.create_user(username='migracao', password='senha123')

        executor = MigrationExecutor(connection)
        executor.migrate(self.estado_0009)
        executor.loader.build_graph()
        apps_0009 = executor.loader.project_state(self.estado_0009).apps

        TicketAntigo = apps_0009.get_model('tickets', 'Ticket')
        ticket = TicketAntigo.objects.create(
            titulo='Chamado sem categoria',
            descricao='Criado no estado 0009 com categoria NULL.',
            solicitante_id=usuario.pk,
            categoria_id=None,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.estado_0010)

        migrado = Ticket.objects.get(pk=ticket.pk)
        self.assertEqual(migrado.categoria.nome, 'Não categorizado')
        self.assertTrue(
            Categoria.objects.filter(nome='Não categorizado', ativa=True).exists()
        )
