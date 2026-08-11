"""Segurança: impede que o navegador guarde ecrãs autenticados no cache local.

Blindagem definitiva do bug do BFCache no backend: qualquer resposta a um
utilizador autenticado recebe headers anti-cache. Assim, mesmo que o frontend
falhe, o navegador não pode restaurar a Dashboard/Fila de uma cópia local após
o Logout.
"""


class NoCacheAuthenticatedMiddleware:
    """Injeta headers de no-cache em todas as respostas de utilizadores logados.

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
