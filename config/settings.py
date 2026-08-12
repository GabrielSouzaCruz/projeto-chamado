# config/settings.py
"""
Configurações principais do projeto Django.

Estrutura:
- Configurações básicas (BASE_DIR, SECRET_KEY, DEBUG)
- Apps e Middleware
- Banco de dados
- Templates
- Arquivos estáticos e mídia
- Segurança
- Internacionalização
- Configurações do projeto

Nota: Este arquivo é configurado para DESENVOLVIMENTO.
Para produção, ajuste: DEBUG=False, ALLOWED_HOSTS, DATABASES, etc.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Sentry (observabilidade/rastreamento de erros). Import com guarda para não
# quebrar o boot sem a lib instalada.
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Pusher (tempo real). Import com guarda para não quebrar o boot sem a lib instalada.
try:
    import pusher as _pusher
except ImportError:
    _pusher = None

# Carrega o arquivo .env da raiz do projeto
load_dotenv()

# =============================================================================
# SENTRY — OBSERVABILIDADE E RASTREAMENTO DE ERROS
# =============================================================================
# Só inicializa se a variável SENTRY_DSN existir no ambiente (produção).
# Sem a chave (ex: testes locais), o Sentry é pulado e o app funciona normal.
if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[DjangoIntegration()],
        # Captura 100% das transações (traces)
        traces_sample_rate=1.0,
        # Envia dados pessoais (nome/ID do usuário logado que causou o erro)
        send_default_pii=True,
    )

# =============================================================================
# CONFIGURAÇÕES BÁSICAS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET_KEY segura (via .env)
SECRET_KEY = os.getenv('SECRET_KEY', 'uma-chave-padrao-para-dev-apenas')

# DEBUG seguro: converte string para booleano real
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['projeto-chamado.onrender.com', '127.0.0.1', 'localhost']

CSRF_TRUSTED_ORIGINS = [
    'https://projeto-chamado.onrender.com',
]

# =============================================================================
# APPS INSTALADOS
# =============================================================================

INSTALLED_APPS = [
    # Django contrib (ordem importa: auth antes de admin)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 3rd party — Cloudinary (media storage)
    'cloudinary',
    'cloudinary_storage',
    
    # Apps do projeto
    'accounts',
    'tickets',
]

# =============================================================================
# MIDDLEWARE
# =============================================================================

# ⚠️ A ordem importa! Middleware é executado top-to-bottom na request,
# bottom-to-top na response. SecurityMiddleware deve vir primeiro.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Aplica os headers CSP em toda resposta (logo após o SecurityMiddleware)
    'csp.middleware.CSPMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Anti-cache para autenticados (no-store): roda após Session/Auth middleware
    'accounts.middleware.NoCacheAuthenticatedMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Templates globais (404, 500, base.html)
        'APP_DIRS': True,  # Habilita templates dentro de cada app
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'config.context_processors.pusher_config',
            ],
        },
    },
]

# =============================================================================
# BANCO DE DADOS
# =============================================================================

# ✅ SQLite para desenvolvimento (simples, sem configuração)
# ⚠️ Para produção, use PostgreSQL ou MySQL
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# =============================================================================
# VALIDAÇÃO DE SENHAS
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {'user_attributes': ['username', 'email', 'first_name']},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
]

# =============================================================================
# INTERNACIONALIZAÇÃO
# =============================================================================

# Force UTC para evitar anomalias de fuso horário
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# =============================================================================
# ARQUIVOS ESTÁTICOS E MÍDIA
# =============================================================================

# Arquivos estáticos (CSS, JS, imagens do sistema)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  # Pasta para coletar com collectstatic
STATIC_ROOT = BASE_DIR / 'staticfiles'    # Pasta para produção (Nginx serve daqui)

# =============================================================================
# CLOUDINARY — STORAGE DE MÍDIA (ANEXOS) NA NUVEM
# O Render Free Tier tem disco EFÊMERO: arquivos em /media/ somem a cada
# deploy/restart. Com o Cloudinary como storage default, os uploads vão para a
# CDN e sobrevivem a deploys. As credenciais são lidas do .env / ambiente:
#
#   CLOUDINARY_CLOUD_NAME
#   CLOUDINARY_API_KEY
#   CLOUDINARY_API_SECRET
#
# Prioridade das credenciais:
#   1) Chaves nomeadas acima (dict CLOUDINARY_STORAGE) — caminho recomendado.
#   2) CLOUDINARY_URL (cloudinary://api_key:api_secret@cloud_name) — legado.
#   3) Nenhuma → mídia local em /media/ (dev sem nuvem), servida por urls.py.
#
# ⚠️ CLOUDINARY_STORAGE só é definido quando as 3 chaves nomeadas existem. O SDK
# do Cloudinary sobrescreve a config com valores None: um dict com chaves None
# apagaria a config vinda do CLOUDINARY_URL. O backend de storage só é ativado
# quando há credenciais — sem elas o app segue 100% funcional com disco local.
# =============================================================================
_CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
_CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
_CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
_CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")

if _CLOUDINARY_CLOUD_NAME and _CLOUDINARY_API_KEY and _CLOUDINARY_API_SECRET:
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": _CLOUDINARY_CLOUD_NAME,
        "API_KEY": _CLOUDINARY_API_KEY,
        "API_SECRET": _CLOUDINARY_API_SECRET,
        "SECURE": True,  # URLs https://
    }
    _STORAGE_DEFAULT_BACKEND = "cloudinary_storage.storage.MediaCloudinaryStorage"
elif _CLOUDINARY_URL:
    # Legado: só a URL presente → o SDK do Cloudinary carrega as credenciais
    # por conta própria. O dict sem as 3 chaves faz o app_settings cair no
    # caminho que preserva a config vinda da URL (evita cloudinary.config(None)).
    CLOUDINARY_STORAGE = {"SECURE": True}
    _STORAGE_DEFAULT_BACKEND = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    # Dev/CI sem credenciais: mídia local em /media/ (disco efêmero, ok p/ dev).
    CLOUDINARY_STORAGE = {"SECURE": True}
    _STORAGE_DEFAULT_BACKEND = "django.core.files.storage.FileSystemStorage"

# Garante URLs https:// desde o boot (o app_settings do cloudinary_storage também
# força secure=True, mas só quando o backend é instanciado; aqui fica
# determinístico. config() só atualiza o parâmetro passado — não toca nas credenciais).
if _STORAGE_DEFAULT_BACKEND == "cloudinary_storage.storage.MediaCloudinaryStorage":
    import cloudinary  # noqa: E402
    cloudinary.config(secure=True)

STORAGES = {
    "default": {
        "BACKEND": _STORAGE_DEFAULT_BACKEND,
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# =============================================================================
# Arquivos de mídia (uploads dos usuários: anexos de tickets e comentários)
# =============================================================================
# MEDIA_URL/MEDIA_ROOT são o caminho local (FileSystemStorage). Quando
# STORAGES["default"] é o Cloudinary, `anexo.url` aponta para a CDN; caso
# contrário (sem CLOUDINARY_URL), os anexos gravam aqui e são servidos pelo
# Django em /media/ (dev e produção — Render WSGI puro, sem Nginx).
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =============================================================================
# MODELO DE USUÁRIO CUSTOMIZADO
# =============================================================================

# ⚠️ IMPORTANTE: Definir antes de criar migrations
# Aponta para o modelo User personalizado no app accounts
AUTH_USER_MODEL = 'accounts.User'

# =============================================================================
# AUTENTICAÇÃO
# =============================================================================

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'tickets:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Segurança de sessão
SESSION_COOKIE_SECURE = not DEBUG  # Apenas HTTPS em produção
SESSION_COOKIE_HTTPONLY = True  # Previne acesso via JavaScript (XSS)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Sessão persiste após fechar navegador
SESSION_COOKIE_AGE = 1209600  # 2 semanas em segundos

# Segurança de CSRF
CSRF_COOKIE_SECURE = not DEBUG  # Apenas HTTPS em produção
CSRF_COOKIE_HTTPONLY = True  # Previne acesso via JavaScript

# =============================================================================
# SEGURANÇA
# =============================================================================

# ⚠️ Headers de segurança (SecurityMiddleware usa estes valores)
SECURE_BROWSER_XSS_FILTER = True  # Protege contra XSS (navegadores antigos)
SECURE_CONTENT_TYPE_NOSNIFF = True  # Previne MIME sniffing
X_FRAME_OPTIONS = 'DENY'  # Previne clickjacking

# ⚠️ Limites de upload (proteção contra DoS)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB por request
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB por arquivo

# =============================================================================
# TEMPO REAL (PUSHER)
# =============================================================================

PUSHER_APP_ID = os.environ.get('PUSHER_APP_ID')
PUSHER_KEY = os.environ.get('PUSHER_KEY')
PUSHER_SECRET = os.environ.get('PUSHER_SECRET')
PUSHER_CLUSTER = os.environ.get('PUSHER_CLUSTER')

if _pusher and PUSHER_APP_ID and PUSHER_KEY and PUSHER_SECRET and PUSHER_CLUSTER:
    PUSHER_CLIENT = _pusher.Pusher(
        app_id=PUSHER_APP_ID,
        key=PUSHER_KEY,
        secret=PUSHER_SECRET,
        cluster=PUSHER_CLUSTER,
        ssl=True,
    )
else:
    # Sem credenciais (ou lib ausente): o sistema segue 100% funcional sem tempo real.
    PUSHER_CLIENT = None

# Dispara eventos do Pusher em thread paralela (daemon) para o usuário receber
# o Response HTTP instantaneamente. Em testes é forçado para False (test_settings)
# para manter as assertivas sobre os payloads determinísticas e síncronas.
PUSHER_ASSINCRONO = True

# =============================================================================
# WEB PUSH NATIVO (VAPID / PUSH API)
# =============================================================================
# Notificações nativas do SO via Push API (100% gratuitas, sem infra extra).
# O Pusher passa a cuidar SOMENTE do tempo real do DOM; o push visual nativo
# (app fechado, banner, vibração) vem daqui, disparado pelo sw.js.
#
# As chaves VAPID são geradas localmente com:
#     pywebpush --gen-vapid-keys
# VAPID_PUBLIC_KEY é pública (vai para o navegador assinar o PushManager);
# VAPID_PRIVATE_KEY é segredo absoluto (fica só no servidor).
#
# Sem chaves VAPID no ambiente: o sistema funciona normalmente, sem push nativo
# (o guard no signals.py sai cedo e nada quebra).
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_ADMIN_EMAIL = os.getenv('VAPID_ADMIN_EMAIL', 'mailto:admin@seudominio.com')

# Web Push também roda em thread paralela (daemon), como o Pusher, para o
# Response HTTP voltar instantâneo. Em testes é forçado para False
# (test_settings), mantendo as assertivas determinísticas e sem threads.
WEB_PUSH_ASSINCRONO = True

# =============================================================================
# LOGGING — Logs estruturados para o terminal do Render (stdout)
# =============================================================================
# Nota: não colide com o Sentry — o Sentry captura via suas próprias
# integrações (LoggingIntegration) e não depende deste dicionário.
LOGGING = {
    'version': 1,
    # Nunca desabilita loggers de apps de terceiros (Pusher, Sentry, etc.)
    'disable_existing_loggers': False,
    'formatters': {
        # Formatador padrão: data/hora + nível + módulo + mensagem
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        # Saída para sys.stdout: o Render captura 100% do que sai no stdout
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        # Em DEBUG o terminal polui fácil → sobe o nível; em produção = INFO
        'level': 'WARNING' if DEBUG else 'INFO',
    },
    'loggers': {
        # Django: avisos e erros (evita propagação para não duplicar)
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Ações sensíveis do nosso app de segurança (ex: bloqueio de IP
        # por rate limit no login). Ajuste o nível conforme o necessário.
        'accounts': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Eventos críticos dos chamados (ex: alterações de status/técnicos)
        'tickets': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# SECURITY & CSP SETTINGS — Headers de Segurança + Content Security Policy
# =============================================================================

# -----------------------------------------------------------------------------
# Headers Nativos (Sempre ativos) — emitidos pelo SecurityMiddleware
# -----------------------------------------------------------------------------
# Protege contra XSS em navegadores antigos (X-XSS-Protection)
SECURE_BROWSER_XSS_FILTER = True
# Previne MIME type sniffing (X-Content-Type-Options)
SECURE_CONTENT_TYPE_NOSNIFF = True
# Previne clickjacking (X-Frame-Options: DENY)
X_FRAME_OPTIONS = 'DENY'

# -----------------------------------------------------------------------------
# Proteções de Produção (Apenas se NÃO DEBUG) — reforços de transporte/sessão
# -----------------------------------------------------------------------------
if not DEBUG:
    # Redireciona todo HTTP -> HTTPS (SECURE_SSL_REDIRECT)
    SECURE_SSL_REDIRECT = True
    # Cookies só trafegam via HTTPS (pacote nunca vazado em texto plano)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS: força HTTPS por 1 ano, incluindo subdomínios e habilitando preload
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# -----------------------------------------------------------------------------
# Configuração do CSP (Content Security Policy) — via django-csp
# -----------------------------------------------------------------------------
# NOTA: django-csp >= 3.0 usa a API moderna CONTENT_SECURITY_POLICY (dict),
# substituindo os antigos settings CSP_* (API legada do django-csp 2.x).
# Django 6 exige django-csp recente (3.8+/4.x), que é a versão mantida e segura.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        # Fontes base: apenas o próprio domínio
        "default-src": ["'self'"],

        # Scripts: self + inline (ainda usamos scripts inline no base.html) +
        # Pusher + CDNs públicas (Bootstrap/jsdelivr, FontAwesome/cloudflare)
        "script-src": [
            "'self'",
            "'unsafe-inline'",
            "https://js.pusher.com",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
        ],

        # Estilos: self + inline + Bootstrap (jsdelivr) + FontAwesome (cloudflare) + Google Fonts
        "style-src": [
            "'self'",
            "'unsafe-inline'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://fonts.googleapis.com",
        ],

        # Imagens: self + data: (miniatura base64/FileReader) + Cloudinary (anexos)
        "img-src": [
            "'self'",
            "data:",
            "https://res.cloudinary.com",
        ],

        # Conexões (fetch/XHR/WebSocket): self + Pusher (wss para o realtime) +
        # jsDelivr (source maps do Bootstrap baixados pelo navegador)
        "connect-src": [
            "'self'",
            "wss://*.pusher.com",
            "https://*.pusher.com",
            "https://cdn.jsdelivr.net",
        ],

        # Fontes: self + data: (ícones) + FontAwesome (cloudflare) + Google Fonts (gstatic)
        "font-src": [
            "'self'",
            "data:",
            "https://cdnjs.cloudflare.com",
            "https://fonts.gstatic.com",
        ],
    },
}