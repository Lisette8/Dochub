"""Actions sur les comptes (promouvoir, suspendre, bloquer...).

Utilisées à la fois par l'admin Django (users/admin.py) et par les pages DocHub
« Utilisateurs » (users/account_views.py) : mêmes règles et mêmes messages partout.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import CHANGE, LogEntry
from django.db import transaction
from django.utils import timezone

from .models import User
from .services import send_activation_email


class AccountAction:
    """`changes` : fonction qui renvoie les champs à modifier.
    `forbidden_on_self` : verbe affiché quand l'admin se l'applique à lui-même (interdit)."""

    def __init__(self, label, done, changes, forbidden_on_self=None):
        self.label, self.done, self.changes = label, done, changes
        self.forbidden_on_self = forbidden_on_self

    def would_change(self, compte):
        """Faux si le compte a déjà ce rôle / ce statut (inutile de proposer l'action)."""
        target = self.changes()
        return any(getattr(compte, field) != target[field] for field in ("role", "statut") if field in target)


ACCOUNT_ACTIONS = {
    "promouvoir_admin": AccountAction(
        "Promouvoir en Administrateur", "promu(s) Administrateur", lambda: {"role": User.Role.ADMIN}),
    "retrograder_utilisateur": AccountAction(
        "Rétrograder en Utilisateur", "rétrogradé(s) Utilisateur", lambda: {"role": User.Role.UTILISATEUR},
        "rétrograder"),
    "suspendre": AccountAction(
        f"Suspendre {settings.SUSPENSION_JOURS} jours", f"suspendu(s) pour {settings.SUSPENSION_JOURS} jours",
        lambda: {"statut": User.Statut.SUSPENDU,
                 "suspendu_jusqua": timezone.now() + timedelta(days=settings.SUSPENSION_JOURS)},
        "suspendre"),
    "bloquer": AccountAction("Bloquer", "bloqué(s)", lambda: {"statut": User.Statut.BLOQUE}, "bloquer"),
    "fermer": AccountAction("Fermer (désactiver)", "fermé(s)", lambda: {"statut": User.Statut.FERME}, "fermer"),
    "rouvrir": AccountAction("Rouvrir", "rouvert(s)", lambda: {"statut": User.Statut.OUVERT}),
}
RENVOYER_ACTIVATION = "renvoyer_activation"

# Libellés de toutes les actions, dans l'ordre d'affichage
ACTION_LABELS = {
    **{key: a.label for key, a in ACCOUNT_ACTIONS.items()},
    RENVOYER_ACTIVATION: "Renvoyer l'e-mail d'activation",
}


def available_actions(compte, acting_user):
    """Actions utiles pour ce compte : liste de (clé, libellé) pour les boutons de sa fiche."""
    is_self = compte.pk == acting_user.pk
    keys = [k for k, a in ACCOUNT_ACTIONS.items()
            if a.would_change(compte) and not (is_self and a.forbidden_on_self)]
    if compte.est_en_attente_activation:
        keys.append(RENVOYER_ACTIVATION)
    return [(k, ACTION_LABELS[k]) for k in keys]


def exclude_self(request, queryset, what):
    """Retire l'admin connecté de la sélection (il ne peut pas se l'appliquer)."""
    if queryset.filter(pk=request.user.pk).exists():
        messages.warning(request, f"Votre propre compte a été ignoré : vous ne pouvez pas vous {what}.")
    return queryset.exclude(pk=request.user.pk)


def run_account_action(request, key, queryset):
    """Applique l'action `key` aux comptes de `queryset` et prépare les messages pour l'admin."""
    if key == RENVOYER_ACTIVATION:
        _resend_activation(request, queryset)
        return
    action = ACCOUNT_ACTIONS[key]
    if action.forbidden_on_self:
        queryset = exclude_self(request, queryset, action.forbidden_on_self)
    users = list(queryset)
    if not users:
        return
    with transaction.atomic():
        # save() sur chaque compte (et non queryset.update) pour garder is_staff / is_active cohérents.
        for user in users:
            for field, value in action.changes().items():
                setattr(user, field, value)
            user.save()
        LogEntry.objects.log_actions(request.user.pk, users, CHANGE, f"Action : {action.label}.")
    messages.success(request, f"{len(users)} compte(s) {action.done}.")


def _resend_activation(request, queryset):
    users = list(queryset)
    pending = [u for u in users if u.est_en_attente_activation]
    for user in pending:
        send_activation_email(request, user)
    if pending:
        messages.success(request, f"E-mail d'activation renvoyé à {len(pending)} compte(s).")
    skipped = len(users) - len(pending)
    if skipped:
        messages.info(request, f"{skipped} compte(s) ignoré(s) : mot de passe déjà choisi.")
