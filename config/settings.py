# config/settings.py

import os

from pathlib import Path

from dotenv import load_dotenv

 

load_dotenv()  # Carrega variáveis do arquivo .env

 

BASE_DIR = Path(__file__).resolve().parent.parent

 

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'chave-dev-muito-secreta-temporaria')

 

DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

 

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

 

INSTALLED_APPS = [ 'django.contrib.admin',

    'django.contrib.auth',

    'django.contrib.contenttypes',

    'django.contrib.sessions',

    'django.contrib.messages',

    'django.contrib.staticfiles',

    # Apps customizados

    'accounts',

    'tickets',

]

 

MIDDLEWARE = [

    'django.middleware.security.SecurityMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',

]

 

ROOT_URLCONF = 'config.urls'

 

TEMPLATES = [{

    'BACKEND': 'django.template.backends.django.DjangoTemplates',

    'DIRS': [BASE_DIR / 'templates'],

    'APP_DIRS': True,

    'OPTIONS': {

        'context_processors': [

            'django.template.context_processors.debug',

            'django.template.context_processors.request',

            'django.contrib.auth.context_processors.auth',

            'django.contrib.messages.context_processors.messages',

        ],

    },

}]

WSGI_APPLICATION = 'config.wsgi.application'

 

# Banco de dados - SQLite para desenvolvimento, PostgreSQL para produção

DATABASES = {

    'default': {

        'ENGINE': 'django.db.backends.sqlite3',

        'NAME': BASE_DIR / 'db.sqlite3',

    }

}

 

# Para PostgreSQL em produção, use:

# DATABASES = {

#     'default': {

#         'ENGINE': 'django.db.backends.postgresql',

#         'NAME': os.getenv('DB_NAME', 'chamados_db'),

#         'USER': os.getenv('DB_USER', 'postgres'),

#         'PASSWORD': os.getenv('DB_PASSWORD', ''),

#         'HOST': os.getenv('DB_HOST', 'localhost'),

#         'PORT': os.getenv('DB_PORT', '5432'),

#     }

# }

 

AUTH_PASSWORD_VALIDATORS = [

    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},

    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},

    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},

    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},

]

 

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

 

# Configuração de arquivos estáticos e mídia

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

STATIC_ROOT = BASE_DIR / 'staticfiles'

 

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'

 

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

 

# Modelo de usuário customizado

AUTH_USER_MODEL = 'accounts.User'

# config/settings.py (adicione ao final)

 

# Configuração de E-mail

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')

EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))

EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'

EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')

EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

SERVER_EMAIL = DEFAULT_FROM_EMAIL

 

# Para desenvolvimento sem SMTP real, use console:

# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# config/settings.py - Seção de produção

 

import os

from django.core.management.utils import get_random_secret_key

 

# Segurança em produção

if not DEBUG:

    SECURE_SSL_REDIRECT = True

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SECURE_BROWSER_XSS_FILTER = True

    SECURE_CONTENT_TYPE_NOSNIFF = True

    X_FRAME_OPTIONS = 'DENY'

    SECURE_HSTS_SECONDS = 31536000  # 1 ano

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True

 

# Validação de hosts (obrigatório em produção)

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

 

# Arquivos estáticos coletados

STATIC_ROOT = BASE_DIR / 'staticfiles'

 

# Log em produção

LOGGING = {

    'version': 1,

    'disable_existing_loggers': False,

    'formatters': {

        'verbose': {

            'format': '{levelname} {asctime} {module} {message}',

            'style': '{',
            },

    },

    'handlers': {

        'file': {

            'level': 'ERROR',

            'class': 'logging.FileHandler',

            'filename': BASE_DIR / 'logs' / 'django.log',

            'formatter': 'verbose',

        },

    },

    'loggers': {

        'django': {

            'handlers': ['file'],

            'level': 'ERROR',

            'propagate': True,

        },

    },

}