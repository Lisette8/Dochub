from django.utils.cache import add_never_cache_headers


class NoCacheForAuthenticatedMiddleware:
    """Interdit au navigateur de garder en cache les pages vues en étant connecté.

    Sans cela, après une déconnexion (ou un changement de compte), le bouton
    « Précédent » peut réafficher une copie de la page de l'ancien compte
    (ex. la page d'administration). Avec « no-store », le navigateur doit
    redemander la page au serveur, qui applique la session actuelle.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            add_never_cache_headers(response)
        return response
