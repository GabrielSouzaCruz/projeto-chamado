import logging

from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger('tickets')


def health_check_view(request):
    """Endpoint público de health check (ex: UptimeRobot) para evitar hibernação.

    Executa uma query rápida no banco. Retorna 200/healthy se o banco
    responder ou 503/unhealthy caso contrário. A mensagem da exceção NUNCA
    vai para a resposta (vazamento de detalhe interno); ela é só registrada
    no log.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        logger.exception('Health check falhou: banco de dados indisponivel')
        return JsonResponse({'status': 'unhealthy'}, status=503)

    return JsonResponse({'status': 'healthy'}, status=200)
