# config/test_settings.py
"""
Settings exclusivo para a suíte de testes.

Garante que os testes rodem offline:
- Banco de dados SQLite em memória (nunca toca a Neon/Postgres de produção).
- Channel layer em memória (nunca conecta no Redis).

Uso:
    python manage.py test --settings=config.test_settings
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CHANNEL_LAYERS = {
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
}
