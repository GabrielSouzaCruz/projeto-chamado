# config/test_settings.py
"""
Settings exclusivo para a suíte de testes.

Garante que os testes rodem offline:
- Banco de dados SQLite em memória (nunca toca a Neon/Postgres de produção).
- Sem Pusher: como não há credenciais, PUSHER_CLIENT é None (nenhum disparo real).

Uso:
    python manage.py test --settings=config.test_settings
"""
from .settings import *  # noqa: F401,F403

# Pusher síncrono: sem threads nos testes, mantendo as assertivas determinísticas.
PUSHER_ASSINCRONO = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
