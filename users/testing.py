"""Outils pour les tests : aucun mot de passe n'est écrit en dur dans le code.

Les mots de passe des tests sont générés aléatoirement à chaque exécution
(les scanners de secrets comme GitGuardian signalent tout mot de passe en clair).
"""
import secrets


def make_password():
    """Mot de passe solide et unique (passe les validateurs de Django)."""
    return "Tst-" + secrets.token_urlsafe(16)


def make_short_password():
    """Mot de passe de 3 caractères, pour tester le validateur de longueur minimale."""
    return secrets.token_hex(2)[:3]
