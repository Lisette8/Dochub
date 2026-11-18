"""Logique métier partagée entre les pages et l'API du module Utilisateurs."""
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import User


def activation_link(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return request.build_absolute_uri(reverse("users:activate", args=[uid, token]))


def create_account_by_admin(request, *, email, first_name, last_name, role, statut):
    """US-05 : l'admin crée un compte et lui attribue un rôle.

    Le compte est créé sans mot de passe utilisable ; un e-mail d'activation
    est envoyé pour que l'utilisateur choisisse lui-même son mot de passe
    (l'admin ne connaît donc jamais le mot de passe).
    """
    user = User.objects.create_user(
        email=email, password=None, first_name=first_name, last_name=last_name,
        role=role, statut=statut,
    )
    send_mail(
        subject="Activez votre compte DocHub",
        message=(
            f"Bonjour {user.first_name},\n\n"
            "Un administrateur vous a créé un compte DocHub "
            f"(rôle : {user.get_role_display()}).\n"
            "Pour choisir votre mot de passe et activer votre compte, ouvrez ce lien :\n\n"
            f"{activation_link(request, user)}\n\n"
            "Ce lien ne fonctionne qu'une seule fois.\n"
        ),
        from_email=None,
        recipient_list=[user.email],
    )
    return user
