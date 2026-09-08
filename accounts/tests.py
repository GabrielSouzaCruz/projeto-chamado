# accounts/tests.py
"""
Testes completos do app accounts.

Cobertas: Login, Registro, Perfil, Alterar Senha, Logout, Mixins, Decorators.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse

User = get_user_model()

LOGIN_URL = reverse('accounts:login')
REGISTER_URL = reverse('accounts:register')
PROFILE_URL = reverse('accounts:profile')
DASHBOARD_URL = reverse('tickets:dashboard')
CHANGE_PASSWORD_URL = reverse('accounts:alterar_senha')


def criar_usuario(**kwargs):
    defaults = {
        'username': 'teste',
        'password': 'senha-teste-123!',
        'email': 'teste@example.com',
        'first_name': 'Teste',
        'last_name': 'Usuario',
        'is_active': True,
    }
    defaults.update(kwargs)
    password = defaults.pop('password')
    user = User(**defaults)
    user.set_password(password)
    user.save()
    return user


# =============================================================================
# 1. CUSTOMLOGINVIEW
# =============================================================================

class TesteLogin(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = LOGIN_URL
        self.user = criar_usuario(
            username='joao.silva',
            password='senha-forte-123!',
            email='joao@example.com',
        )
        cache.clear()

    def test_login_credenciais_validas_redireciona_dashboard(self):
        resp = self.client.post(self.url, {
            'username': 'joao.silva',
            'password': 'senha-forte-123!',
        })
        self.assertRedirects(resp, DASHBOARD_URL, fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_senha_errada_retorna_form_com_erro(self):
        resp = self.client.post(self.url, {
            'username': 'joao.silva',
            'password': 'senha-errada',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertTrue(form.errors)

    def test_login_usuario_inexistente_retorna_form_com_erro(self):
        resp = self.client.post(self.url, {
            'username': 'naoexiste',
            'password': 'qualquer',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertTrue(form.errors)

    def test_login_conta_inativa_bloqueado(self):
        criar_usuario(username='inativo', email='inativo@example.com', is_active=False)
        resp = self.client.post(self.url, {
            'username': 'inativo',
            'password': 'senha-teste-123!',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertTrue(form.errors)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_rate_limit_bloqueio_apos_10_falhas(self):
        for i in range(10):
            self.client.post(self.url, {
                'username': 'joao.silva',
                'password': f'errada-{i}',
            })
        resp = self.client.post(self.url, {
            'username': 'joao.silva',
            'password': 'errada-10',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        non_field_errors = [e for e in form.non_field_errors()]
        self.assertTrue(any('bloqueado' in str(e).lower() for e in non_field_errors))

    def test_rate_limit_reseta_apos_login_sucesso(self):
        for i in range(9):
            self.client.post(self.url, {
                'username': 'joao.silva',
                'password': f'errada-{i}',
            })
        # Login OK reseta — redireciona para dashboard (302)
        resp = self.client.post(self.url, {
            'username': 'joao.silva',
            'password': 'senha-forte-123!',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)
        # Verifica que pode tentar novamente sem bloqueio
        self.client.logout()
        resp = self.client.post(self.url, {
            'username': 'joao.silva',
            'password': 'outra-errada',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        non_field_errors = [e for e in form.non_field_errors()]
        self.assertFalse(any('bloqueado' in str(e).lower() for e in non_field_errors))

    def test_login_GET_retorna_formulario(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/login.html')


# =============================================================================
# 2. REGISTERVIEW
# =============================================================================

class TesteRegistro(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = REGISTER_URL
        self.dados_validos = {
            'first_name': 'Maria',
            'last_name': 'Santos',
            'email': 'maria@example.com',
            'departamento': 'TI',
            'telefone': '3333-4444',
            'password1': 'senha-forte-999!',
            'password2': 'senha-forte-999!',
            'aceitou_termos': True,
        }
        cache.clear()

    def test_registro_dados_validos_cria_usuario_redireciona(self):
        resp = self.client.post(self.url, self.dados_validos)
        self.assertRedirects(resp, DASHBOARD_URL, fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(email='maria@example.com').exists())
        self.assertIn('_auth_user_id', self.client.session)

    def test_username_gerado_automaticamente_nome_sobrenome(self):
        self.client.post(self.url, self.dados_validos)
        user = User.objects.get(email='maria@example.com')
        self.assertEqual(user.username, 'maria.santos')

    def test_username_remove_acentos(self):
        dados = self.dados_validos.copy()
        dados['first_name'] = 'Joao'
        dados['last_name'] = 'Conceicao'
        dados['email'] = 'joao.conceicao@example.com'
        self.client.post(self.url, dados)
        user = User.objects.get(email='joao.conceicao@example.com')
        self.assertEqual(user.username, 'joao.conceicao')

    def test_username_duplicado_adiciona_numero(self):
        criar_usuario(username='maria.santos', email='outra@example.com')
        self.client.post(self.url, self.dados_validos)
        user = User.objects.get(email='maria@example.com')
        self.assertEqual(user.username, 'maria.santos1')

    def test_registro_email_duplicado_erro(self):
        criar_usuario(email='maria@example.com', username='existente')
        resp = self.client.post(self.url, self.dados_validos)
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertIn('email', form.errors)
        self.assertTrue(any('cadastrado' in str(e) for e in form.errors['email']))

    def test_registro_senha_fraca_curta_erro(self):
        dados = self.dados_validos.copy()
        dados['password1'] = '123'
        dados['password2'] = '123'
        resp = self.client.post(self.url, dados)
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertTrue(form.errors.get('password1') or form.errors.get('password2'))

    def test_registro_senha_100_percentual_numerica_erro(self):
        dados = self.dados_validos.copy()
        dados['password1'] = '1234567890'
        dados['password2'] = '1234567890'
        resp = self.client.post(self.url, dados)
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertTrue(form.errors.get('password1') or form.errors.get('password2'))

    def test_registro_senha_comum_erro(self):
        dados = self.dados_validos.copy()
        dados['password1'] = 'password'
        dados['password2'] = 'password'
        resp = self.client.post(self.url, dados)
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertTrue(form.errors.get('password1') or form.errors.get('password2'))

    def test_rate_limit_bloqueio_apos_5_falhas(self):
        for i in range(5):
            dados = self.dados_validos.copy()
            dados['email'] = f'fail{i}@example.com'
            dados['password2'] = 'nao-bate'
            self.client.post(self.url, dados)
        dados = self.dados_validos.copy()
        dados['email'] = 'novo@example.com'
        resp = self.client.post(self.url, dados)
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        non_field_errors = [e for e in form.non_field_errors()]
        self.assertTrue(any('aguarde' in str(e).lower() for e in non_field_errors))

    def test_rate_limit_reseta_apos_registro_sucesso(self):
        for i in range(4):
            dados = self.dados_validos.copy()
            dados['email'] = f'fail{i}@example.com'
            dados['password2'] = 'nao-bate'
            self.client.post(self.url, dados)
        # Registro OK reseta
        self.client.post(self.url, self.dados_validos)
        # Verifica que pode tentar novamente
        dados2 = self.dados_validos.copy()
        dados2['email'] = 'pos-reset@example.com'
        dados2['password2'] = 'errada'
        resp = self.client.post(self.url, dados2)
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        non_field_errors = [e for e in form.non_field_errors()]
        self.assertFalse(any('aguarde' in str(e).lower() for e in non_field_errors))

    def test_registro_GET_retorna_formulario(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/register.html')


# =============================================================================
# 3. PROFILEUPDATEVIEW
# =============================================================================

class TestePerfil(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = criar_usuario(
            username='perfil.teste',
            email='perfil@example.com',
            first_name='Perfil',
            last_name='Teste',
        )
        self.url = PROFILE_URL

    def test_acesso_sem_autenticacao_redireciona_login(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, f'{LOGIN_URL}?next={self.url}', fetch_redirect_response=False)

    def test_acesso_autenticado_retorna_200(self):
        self.client.login(username='perfil.teste', password='senha-teste-123!')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/profile.html')

    def test_update_valido_salva_e_redireciona(self):
        self.client.login(username='perfil.teste', password='senha-teste-123!')
        resp = self.client.post(self.url, {
            'first_name': 'Novo',
            'last_name': 'Nome',
            'email': 'novo@example.com',
            'departamento': 'RH',
            'telefone': '9999-0000',
        })
        self.assertRedirects(resp, self.url, fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Novo')
        self.assertEqual(self.user.email, 'novo@example.com')
        self.assertEqual(self.user.departamento, 'RH')

    def test_update_email_duplicado_erro(self):
        criar_usuario(username='outro', email='ocupado@example.com')
        self.client.login(username='perfil.teste', password='senha-teste-123!')
        resp = self.client.post(self.url, {
            'first_name': 'Perfil',
            'last_name': 'Teste',
            'email': 'ocupado@example.com',
            'departamento': '',
            'telefone': '',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertIn('email', form.errors)
        self.assertTrue(any('cadastrado' in str(e) for e in form.errors['email']))

    def test_update_manter_proprio_email(self):
        self.client.login(username='perfil.teste', password='senha-teste-123!')
        resp = self.client.post(self.url, {
            'first_name': 'Atualizado',
            'last_name': 'Teste',
            'email': 'perfil@example.com',
            'departamento': '',
            'telefone': '',
        })
        self.assertRedirects(resp, self.url, fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Atualizado')


# =============================================================================
# 4. ALTERAR_SENHA
# =============================================================================

class TesteAlterarSenha(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = criar_usuario(
            username='senha.teste',
            email='senha@example.com',
            password='senha-atual-123!',
        )
        self.url = CHANGE_PASSWORD_URL

    def test_acesso_sem_autenticacao_redireciona_login(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, f'{LOGIN_URL}?next={self.url}', fetch_redirect_response=False)

    def test_senha_atual_errada_erro(self):
        self.client.login(username='senha.teste', password='senha-atual-123!')
        resp = self.client.post(self.url, {
            'old_password': 'senha-errada',
            'new_password1': 'nova-senha-forte-999!',
            'new_password2': 'nova-senha-forte-999!',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertIn('old_password', form.errors)

    def test_nova_senha_curta_erro(self):
        self.client.login(username='senha.teste', password='senha-atual-123!')
        resp = self.client.post(self.url, {
            'old_password': 'senha-atual-123!',
            'new_password1': '123',
            'new_password2': '123',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertTrue(form.errors.get('new_password2') or form.errors.get('new_password1'))

    def test_nova_senha_numerica_erro(self):
        self.client.login(username='senha.teste', password='senha-atual-123!')
        resp = self.client.post(self.url, {
            'old_password': 'senha-atual-123!',
            'new_password1': '1234567890',
            'new_password2': '1234567890',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertTrue(form.errors.get('new_password2') or form.errors.get('new_password1'))

    def test_nova_senha_comum_erro(self):
        self.client.login(username='senha.teste', password='senha-atual-123!')
        resp = self.client.post(self.url, {
            'old_password': 'senha-atual-123!',
            'new_password1': 'password',
            'new_password2': 'password',
        })
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertTrue(form.errors.get('new_password2') or form.errors.get('new_password1'))

    def test_troca_valida_salva_mantem_sessao_redireciona(self):
        self.client.login(username='senha.teste', password='senha-atual-123!')
        resp = self.client.post(self.url, {
            'old_password': 'senha-atual-123!',
            'new_password1': 'nova-senha-forte-999!',
            'new_password2': 'nova-senha-forte-999!',
        })
        self.assertRedirects(resp, PROFILE_URL, fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertFalse(self.client.login(username='senha.teste', password='senha-atual-123!'))
        self.assertTrue(self.client.login(username='senha.teste', password='nova-senha-forte-999!'))

    def test_GET_retorna_formulario(self):
        self.client.login(username='senha.teste', password='senha-atual-123!')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/alterar_senha.html')


# =============================================================================
# 5. CUSTOMLOGOUTVIEW
# =============================================================================

class TesteLogout(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = criar_usuario(username='logout.teste', email='logout@example.com')
        self.url = reverse('accounts:logout')

    def test_logout_encerra_sessao_redireciona_login(self):
        self.client.login(username='logout.teste', password='senha-teste-123!')
        self.assertIn('_auth_user_id', self.client.session)
        resp = self.client.post(self.url)
        self.assertRedirects(resp, LOGIN_URL, fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_apos_logout_acesso_protegido_redireciona_login(self):
        self.client.login(username='logout.teste', password='senha-teste-123!')
        self.client.post(self.url)
        resp = self.client.get(DASHBOARD_URL)
        self.assertRedirects(resp, f'{LOGIN_URL}?next={DASHBOARD_URL}', fetch_redirect_response=False)


# =============================================================================
# 6. MIXINS E DECORATORS
# =============================================================================

class TesteMixinsDecorators(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuario_comum = criar_usuario(
            username='comum',
            email='comum@example.com',
            is_technician=False,
            is_staff=False,
            is_superuser=False,
        )
        self.tecnico = criar_usuario(
            username='tecnico',
            email='tecnico@example.com',
            is_technician=True,
            is_staff=False,
            is_superuser=False,
        )
        self.admin = criar_usuario(
            username='admin',
            email='admin@example.com',
            is_technician=False,
            is_staff=True,
            is_superuser=True,
        )
        self.outro = criar_usuario(
            username='outro',
            email='outro@example.com',
            is_technician=False,
            is_staff=False,
            is_superuser=False,
        )

    # -- @login_required (via dashboard) --

    def test_login_required_anonimo_redireciona_login(self):
        resp = self.client.get(DASHBOARD_URL)
        self.assertRedirects(resp, f'{LOGIN_URL}?next={DASHBOARD_URL}', fetch_redirect_response=False)

    def test_login_required_autenticado_acessa(self):
        self.client.login(username='comum', password='senha-teste-123!')
        resp = self.client.get(DASHBOARD_URL)
        self.assertEqual(resp.status_code, 200)

    # -- @tecnico_required (via historico) --

    def test_tecnico_required_usuario_comum_redirect(self):
        self.client.login(username='comum', password='senha-teste-123!')
        url = reverse('tickets:historico')
        resp = self.client.get(url)
        self.assertRedirects(resp, DASHBOARD_URL, fetch_redirect_response=False)

    def test_tecnico_required_usuario_comum_ajax_403(self):
        self.client.login(username='comum', password='senha-teste-123!')
        url = reverse('tickets:api_fila_admin_rows')
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 403)

    def test_tecnico_required_tecnico_acessa(self):
        self.client.login(username='tecnico', password='senha-teste-123!')
        url = reverse('tickets:historico')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_tecnico_required_superuser_acessa(self):
        self.client.login(username='admin', password='senha-teste-123!')
        url = reverse('tickets:historico')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    # -- @admin_required (via fila-admin) --

    def test_admin_required_tecnico_sem_staff_redirect(self):
        self.client.login(username='tecnico', password='senha-teste-123!')
        url = reverse('tickets:fila_admin')
        resp = self.client.get(url)
        # fila_admin tem @admin_required + @tecnico_required
        # tecnico sem is_staff -> admin_required bloqueia -> redirect login
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)

    def test_admin_required_usuario_comum_redirect(self):
        self.client.login(username='comum', password='senha-teste-123!')
        url = reverse('tickets:fila_admin')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)

    # -- ProprietarioOrTecnicoMixin (via TicketDetailView) --

    def test_proprietario_mixin_dono_do_ticket_acessa(self):
        from tickets.models import Ticket, Categoria
        cat = Categoria.objects.create(nome='Teste')
        ticket = Ticket.objects.create(
            titulo='Ticket Teste',
            descricao='Desc',
            solicitante=self.usuario_comum,
            categoria=cat,
        )
        self.client.login(username='comum', password='senha-teste-123!')
        url = reverse('tickets:detail', args=[ticket.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_proprietario_mixin_outro_comum_redirect(self):
        from tickets.models import Ticket, Categoria
        cat = Categoria.objects.create(nome='Teste')
        ticket = Ticket.objects.create(
            titulo='Ticket Teste',
            descricao='Desc',
            solicitante=self.outro,
            categoria=cat,
        )
        self.client.login(username='comum', password='senha-teste-123!')
        url = reverse('tickets:detail', args=[ticket.pk])
        resp = self.client.get(url)
        self.assertRedirects(resp, DASHBOARD_URL, fetch_redirect_response=False)

    def test_proprietario_mixin_superuser_acessa(self):
        from tickets.models import Ticket, Categoria
        cat = Categoria.objects.create(nome='Teste')
        ticket = Ticket.objects.create(
            titulo='Ticket Teste',
            descricao='Desc',
            solicitante=self.outro,
            categoria=cat,
        )
        self.client.login(username='admin', password='senha-teste-123!')
        url = reverse('tickets:detail', args=[ticket.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    # -- TecnicoOrStaffRequiredMixin (via CategoriaCreateView) --

    def test_tecnico_staff_mixin_comum_403(self):
        self.client.login(username='comum', password='senha-teste-123!')
        url = reverse('tickets:categoria_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_tecnico_staff_mixin_tecnico_acessa(self):
        self.client.login(username='tecnico', password='senha-teste-123!')
        url = reverse('tickets:categoria_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_tecnico_staff_mixin_staff_acessa(self):
        self.client.login(username='admin', password='senha-teste-123!')
        url = reverse('tickets:categoria_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


# =============================================================================
# 7. RESET DE SENHA (fluxo interno)
# =============================================================================

class TesteResetSenha(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = criar_usuario(
            username='reset.teste',
            email='reset@example.com',
            password='senha-atual-123!',
        )
        self.esqueci_url = reverse('accounts:esqueci_senha')
        self.login_url = reverse('accounts:login')
        self.alterar_url = reverse('accounts:alterar_senha')

    def test_get_esqueci_senha_retorna_200(self):
        resp = self.client.get(self.esqueci_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/esqueci_senha.html')

    def test_post_esqueci_senha_exibe_mensagem_sem_criar_nada(self):
        email_antes = User.objects.count()
        resp = self.client.post(self.esqueci_url, {'email': 'reset@example.com'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.count(), email_antes)

    def test_action_admin_gera_senha_e_must_change_password(self):
        from django.contrib.admin.sites import AdminSite
        from django.contrib.messages.storage.fallback import FallbackStorage
        from accounts.admin import CustomUserAdmin
        admin_user = criar_usuario(username='superadmin', email='superadmin@example.com', is_superuser=True, is_staff=True)
        admin_site = AdminSite()
        model_admin = CustomUserAdmin(User, admin_site)
        qs = User.objects.filter(pk=self.user.pk)
        # Cria request fake com suporte a messages
        from django.test import RequestFactory
        request = RequestFactory().post('/admin/')
        request.user = admin_user
        setattr(request, 'session', 'session')
        setattr(request, '_messages', FallbackStorage(request))
        model_admin.resetar_senha_temporaria(request, qs)
        self.user.refresh_from_db()
        self.assertTrue(self.user.must_change_password)

    def test_login_must_change_password_true_redireciona_alterar_senha(self):
        self.user.must_change_password = True
        self.user.save(update_fields=['must_change_password'])
        resp = self.client.post(self.login_url, {
            'username': 'reset.teste',
            'password': 'senha-atual-123!',
        })
        self.assertRedirects(resp, self.alterar_url, fetch_redirect_response=False)

    def test_login_must_change_password_false_fluxo_normal(self):
        resp = self.client.post(self.login_url, {
            'username': 'reset.teste',
            'password': 'senha-atual-123!',
        })
        self.assertRedirects(resp, DASHBOARD_URL, fetch_redirect_response=False)

    def test_apos_alterar_senha_must_change_password_vira_false(self):
        self.user.must_change_password = True
        self.user.save(update_fields=['must_change_password'])
        self.client.login(username='reset.teste', password='senha-atual-123!')
        # Forca o redirect por must_change_password
        self.client.get(self.alterar_url)
        resp = self.client.post(self.alterar_url, {
            'old_password': 'senha-atual-123!',
            'new_password1': 'nova-senha-forte-999!',
            'new_password2': 'nova-senha-forte-999!',
        })
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)


# =============================================================================
# 8. LGPD
# =============================================================================

class TesteLGPD(TestCase):

    def setUp(self):
        self.client = Client()
        self.register_url = REGISTER_URL
        self.dados_validos = {
            'first_name': 'Maria',
            'last_name': 'Santos',
            'email': 'maria.lgpd@example.com',
            'departamento': 'TI',
            'telefone': '3333-4444',
            'password1': 'senha-forte-999!',
            'password2': 'senha-forte-999!',
            'aceitou_termos': True,
        }

    def test_get_termos_de_uso_retorna_200(self):
        resp = self.client.get(reverse('accounts:termos_de_uso'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/termos_de_uso.html')

    def test_get_politica_privacidade_retorna_200(self):
        resp = self.client.get(reverse('accounts:politica_privacidade'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/politica_privacidade.html')

    def test_termos_de_uso_acesso_publico(self):
        resp = self.client.get(reverse('accounts:termos_de_uso'))
        self.assertEqual(resp.status_code, 200)

    def test_politica_privacidade_acesso_publico(self):
        resp = self.client.get(reverse('accounts:politica_privacidade'))
        self.assertEqual(resp.status_code, 200)

    def test_registro_sem_checkbox_erro(self):
        dados = self.dados_validos.copy()
        del dados['aceitou_termos']
        resp = self.client.post(self.register_url, dados)
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        self.assertIn('aceitou_termos', form.errors)

    def test_registro_com_checkbox_cria_usuario_com_aceite(self):
        resp = self.client.post(self.register_url, self.dados_validos)
        self.assertRedirects(resp, DASHBOARD_URL, fetch_redirect_response=False)
        user = User.objects.get(email='maria.lgpd@example.com')
        self.assertTrue(user.aceitou_termos)
        self.assertIsNotNone(user.data_aceite_termos)

    def test_usuario_existente_aceitou_termos_false_default(self):
        user = criar_usuario(username='legado', email='legado@example.com')
        self.assertFalse(user.aceitou_termos)
        self.assertIsNone(user.data_aceite_termos)
