"""Middleware de segurança do app accounts.

Contém:
- ForcePasswordChangeMiddleware: bloqueia o sistema até o utilizador trocar a
  senha inicial (must_change_password=True).
- NoCacheAuthenticatedMiddleware: headers anti-cache para utilizadores logados.
"""

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """Força a troca de senha no primeiro acesso.

    Regras (corre DEPOIS do AuthenticationMiddleware, pois precisa de
    request.user):
    - Utilizador autenticado com must_change_password=True → todo pedido é
      redirecionado (302) para accounts:alterar_senha, EXCETO:
        * a própria página accounts:alterar-senha/
        * accounts:logout/ (para não prender a sessão)
        * /static/* (ficheiros estáticos)
    - Pedidos AJAX/API → 403 com corpo JSON (um cliente JSON não deve seguir
      um redirect HTML).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._troca_pendente(request) and not self._caminho_isento(request):
            return self._resposta(request)
        return self.get_response(request)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _troca_pendente(request):
        """True se há utilizador autenticado com troca de senha pendente."""
        user = getattr(request, 'user', None)
        return bool(
            user is not None
            and user.is_authenticated
            and getattr(user, 'must_change_password', False)
        )

    @staticmethod
    def _caminho_isento(request):
        """Caminhos que continuam acessíveis com a flag ativa."""
        path = request.path_info
        static_url = settings.STATIC_URL or '/static/'
        if path.startswith(static_url):
            return True
        return path in (
            reverse('accounts:alterar_senha'),
            reverse('accounts:logout'),
        )

    @staticmethod
    def _quer_json(request):
        """Detecta pedidos AJAX/API (esperam JSON, não redirect HTML)."""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True
        if '/api/' in request.path_info:
            return True
        accept = request.headers.get('Accept', '')
        return 'application/json' in accept and 'text/html' not in accept

    @staticmethod
    def _resposta(request):
        destino = reverse('accounts:alterar_senha')
        if ForcePasswordChangeMiddleware._quer_json(request):
            return JsonResponse(
                {
                    'detail': 'Troca de senha obrigatória antes de continuar.',
                    'redirecionar_para': destino,
                },
                status=403,
            )
        return HttpResponseRedirect(destino)


class NoCacheAuthenticatedMiddleware:
    """Injeta headers de no-cache em todas as respostas de utilizadores logados.

    Blindagem definitiva do bug do BFCache no backend: qualquer resposta a um
    utilizador autenticado recebe headers anti-cache. Assim, mesmo que o
    frontend falhe, o navegador não pode restaurar a Dashboard/Fila de uma
    cópia local após o Logout.

    Deve ficar no FINAL de MIDDLEWARE para rodar depois do SessionMiddleware e
    AuthenticationMiddleware (que popularam o request.user).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response
