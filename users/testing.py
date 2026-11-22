"""Outils pour les tests : aucun mot de passe, nom ou e-mail n'est écrit en dur dans le code.

Tout est généré aléatoirement à chaque exécution
(les scanners de secrets comme GitGuardian signalent tout mot de passe en clair).
"""
import secrets
import string

from django.contrib.auth import get_user_model


def make_password():
    """Mot de passe solide et unique (passe les validateurs de Django)."""
    return "Aa-" + secrets.token_urlsafe(16)


def make_short_password():
    """Mot de passe de 3 caractères, pour tester le validateur de longueur minimale."""
    return secrets.token_hex(2)[:3]


def make_name(prefix=""):
    """Prénom ou nom aléatoire (lettres seulement)."""
    letters = "".join(secrets.choice(string.ascii_lowercase) for _ in range(12))
    return (prefix + letters).capitalize()


# Domaine aléatoire dans « .test », réservé aux tests (n'existe pas sur Internet).
_DOMAIN = f"d{secrets.token_hex(8)}.test"


def make_email(label="user"):
    """Adresse de test : même label = même adresse pendant toute l'exécution."""
    return f"{label}@{_DOMAIN}"


PASSWORD = make_password()
NEW_PASSWORD = make_password()
PRENOM, NOM = make_name(), make_name()
PRENOM_2, NOM_2 = make_name(), make_name()


def make_user(email=None, role=None, **kw):
    User = get_user_model()
    kw.setdefault("first_name", make_name())
    kw.setdefault("last_name", make_name())
    return User.objects.create_user(email=email or make_email(), password=PASSWORD,
                                    role=role or User.Role.UTILISATEUR, **kw)
