"""Crée les comptes de démonstration (développement / démo uniquement).

    python manage.py seed_demo
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from users.models import User

DEMO_ACCOUNTS = [
    # email, prénom, nom, rôle, mot de passe (comptes de démo, jamais en production)
    ("admin@dochub.test", "Admin", "DocHub", User.Role.ADMIN, "Admin-Demo-2026"),
    ("user@dochub.test", "Sami", "Utilisateur", User.Role.UTILISATEUR, "User-Demo-2026"),
]


class Command(BaseCommand):
    help = "Crée (ou réinitialise) les comptes de démonstration."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo est réservé au développement (DEBUG=True).")
        for email, first, last, role, password in DEMO_ACCOUNTS:
            user, created = User.objects.get_or_create(
                email=email, defaults={"first_name": first, "last_name": last, "role": role}
            )
            user.first_name, user.last_name, user.role, user.statut = first, last, role, User.Statut.OUVERT
            if role == User.Role.ADMIN:
                user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(f"{'Créé' if created else 'Mis à jour'} : {email} ({user.get_role_display()})")
