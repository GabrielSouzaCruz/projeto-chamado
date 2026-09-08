"""Headers de seguranca adicionais que o Django nao configura nativamente.

Permissions-Policy: restringe APIs do navegador (camera, microphone, etc.)
em todas as respostas.
"""


class SecurityHeadersMiddleware:
    """Injeta Permissions-Policy em toda resposta HTTP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response
