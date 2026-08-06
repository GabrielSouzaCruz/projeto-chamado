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
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Pusher (tempo real). Import com guarda para não quebrar o boot sem a lib instalada.
try:
    import pusher as _pusher
except ImportError:
    _pusher = None

# Carrega o arquivo .env da raiz do projeto
load_dotenv()

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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Arquivos de mídia (uploads dos usuários: anexos de tickets)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

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
# E-MAIL
# =============================================================================

# ✅ Console backend para desenvolvimento (emails vão para o terminal)
# ⚠️ Para produção, configure SMTP real:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'seu-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'sua-senha'

EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
DEFAULT_FROM_EMAIL = 'sistema@localhost'

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

# =============================================================================
# LOGGING (Opcional - para debug em produção)
# =============================================================================

# Para habilitar logs em produção, descomente e ajuste:
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'file': {
#             'level': 'ERROR',
#             'class': 'logging.FileHandler',
#             'filename': BASE_DIR / 'logs' / 'django_errors.log',
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['file'],
#             'level': 'ERROR',
#             'propagate': True,
#         },
#     },
# }