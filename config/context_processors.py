from django.conf import settings


def pusher_config(request):
    """Expõe a configuração pública do Pusher para os templates.

    Key e cluster são públicos (enviados ao navegador); o secret fica no servidor.
    VAPID_PUBLIC_KEY também é pública (o navegador usa para assinar o PushManager).
    """
    return {
        'PUSHER_ENABLED': getattr(settings, 'PUSHER_CLIENT', None) is not None,
        'PUSHER_KEY': getattr(settings, 'PUSHER_KEY', '') or '',
        'PUSHER_CLUSTER': getattr(settings, 'PUSHER_CLUSTER', '') or '',
        'VAPID_PUBLIC_KEY': getattr(settings, 'VAPID_PUBLIC_KEY', '') or '',
    }


def vapid_keys(request):
    return {'VAPID_PUBLIC_KEY': getattr(settings, 'VAPID_PUBLIC_KEY', '')}