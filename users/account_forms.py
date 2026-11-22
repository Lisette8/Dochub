"""Formulaires des pages DocHub « Utilisateurs ».

Ils reprennent les formulaires de l'admin Django (mêmes contrôles de saisie) ;
seul l'affichage change.
"""
from django import forms
from django.contrib.auth.forms import AdminPasswordChangeForm

from .admin_forms import UserAdminChangeForm, UserAdminCreationForm
from .forms import EMAIL_PLACEHOLDER

PLACEHOLDERS = {"first_name": "Prénom", "last_name": "Nom", "email": EMAIL_PLACEHOLDER}


def _add_placeholders(form):
    for name, text in PLACEHOLDERS.items():
        form.fields[name].widget.attrs["placeholder"] = text


class AccountCreateForm(UserAdminCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_placeholders(self)


class AccountUpdateForm(UserAdminChangeForm):
    password = None  # le mot de passe a sa propre page

    class Meta(UserAdminChangeForm.Meta):
        widgets = {"suspendu_jusqua": forms.DateTimeInput(attrs={"type": "datetime-local"},
                                                          format="%Y-%m-%dT%H:%M")}

    def __init__(self, *args, acting_user, **kwargs):
        super().__init__(*args, **kwargs)
        self.acting_user = acting_user
        _add_placeholders(self)


class AccountPasswordForm(AdminPasswordChangeForm):
    """L'admin choisit un nouveau mot de passe, ou retire l'actuel
    (l'utilisateur doit alors en choisir un avec le lien d'activation)."""

    error_messages = {"password_mismatch": "Les deux mots de passe ne correspondent pas."}

    def __init__(self, user, *args, acting_user, **kwargs):
        super().__init__(user, *args, **kwargs)
        for name, label, message in [
            ("password1", "Nouveau mot de passe", "Le mot de passe est obligatoire."),
            ("password2", "Confirmer le mot de passe", "Confirmez le mot de passe."),
        ]:
            field = self.fields[name]
            field.label, field.help_text = label, ""
            field.error_messages["required"] = message
        if user.pk == acting_user.pk:
            # Un admin ne peut pas retirer son propre mot de passe (il ne pourrait plus se connecter).
            self.fields.pop("usable_password", None)
        elif "usable_password" in self.fields:
            field = self.fields["usable_password"]
            field.label, field.help_text = "Que voulez-vous faire ?", ""
            field.choices = [("true", "Définir un nouveau mot de passe"),
                             ("false", "Retirer le mot de passe et envoyer un e-mail d'activation")]

    @property
    def removes_password(self):
        return not self.cleaned_data["set_usable_password"]
