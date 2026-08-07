from django.db import connection
from django.http import JsonResponse


def health_check_view(request):
    """Endpoint público de health check (ex: UptimeRobot) para evitar hibernação.

    Executa uma query rápida no banco. Retorna 200/healthy se o banco
    responder ou 503/unhealthy com a mensagem de erro caso contrário.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=503)

    return JsonResponse({'status': 'healthy'}, status=200)
