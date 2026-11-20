"""Formulaires de l'admin Django pour le CRUD des comptes (admins et utilisateurs).

Mêmes contrôles de saisie que les pages DocHub (prénom / nom / email),
plus les règles de statut (suspension avec date de fin) et les garde-fous
qui empêchent un admin de se verrouiller hors de son propre compte.
"""
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserChangeForm

from .forms import CREATION_STATUTS, clean_new_email, clean_person_name
from .models import User


class _SelfProtectionMixin:
    """`acting_user` = l'admin connecté (injecté par UserAdmin.get_form)."""

    acting_user = None

    def _check_self_lockout(self, cleaned):
        if self.acting_user is None or self.instance.pk != self.acting_user.pk:
            return
        if cleaned.get("role") and cleaned["role"] != User.Role.ADMIN:
            self.add_error("role", "Vous ne pouvez pas retirer votre propre rôle d'Administrateur.")
        if cleaned.get("statut") and cleaned["statut"] != User.Statut.OUVERT:
            self.add_error("statut", "Vous ne pouvez pas suspendre, bloquer ou fermer votre propre compte.")


class UserAdminCreationForm(forms.ModelForm):
    """Création d'un compte.

    Rôle par défaut : Utilisateur (on peut choisir Administrateur).
    Mot de passe facultatif : s'il est vide, le compte est créé sans mot de passe
    et l'utilisateur reçoit un e-mail d'activation pour le choisir lui-même.
    """

    statut = forms.ChoiceField(label="Statut du compte", choices=CREATION_STATUTS, initial=User.Statut.OUVERT)
    password1 = forms.CharField(
        label="Mot de passe", required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Laissez vide pour envoyer un e-mail d'activation (recommandé).",
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe", required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "statut"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].initial = User.Role.UTILISATEUR

    def clean_first_name(self):
        return clean_person_name(self.cleaned_data["first_name"])

    def clean_last_name(self):
        return clean_person_name(self.cleaned_data["last_name"])

    def clean_email(self):
        return clean_new_email(self.cleaned_data["email"])

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Les deux mots de passe ne correspondent pas.")
            else:
                try:
                    password_validation.validate_password(p1, self.instance)
                except forms.ValidationError as e:
                    self.add_error("password1", e)
        return cleaned

    @property
    def sends_activation_email(self):
        return not self.cleaned_data.get("password1")

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.sends_activation_email:
            user.set_unusable_password()
        else:
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserAdminChangeForm(_SelfProtectionMixin, UserChangeForm):
    """Modification d'un compte : identité, rôle (promouvoir / rétrograder), statut."""

    class Meta(UserChangeForm.Meta):
        model = User
        fields = ["email", "first_name", "last_name", "role", "statut", "suspendu_jusqua", "motif_statut"]

    def clean_first_name(self):
        return clean_person_name(self.cleaned_data["first_name"])

    def clean_last_name(self):
        return clean_person_name(self.cleaned_data["last_name"])

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse email.")
        return email

    def clean(self):
        cleaned = super().clean()
        self._check_self_lockout(cleaned)
        return cleaned
