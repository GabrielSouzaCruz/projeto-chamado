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