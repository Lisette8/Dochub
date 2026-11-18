from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    """Formulaire de connexion par email + mot de passe."""

    username = forms.EmailField(
        label="Adresse e-mail",
        max_length=254,
        widget=forms.EmailInput(attrs={
            "autofocus": True, "autocomplete": "email", "placeholder": "prenom.nom@organisation.tn",
        }),
        error_messages={
            "required": "L'adresse email est obligatoire.",
            "invalid": "Saisissez une adresse email valide.",
        },
    )
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "placeholder": "••••••••"}),
        error_messages={"required": "Le mot de passe est obligatoire."},
    )
    remember_me = forms.BooleanField(label="Se souvenir de moi", required=False)

    error_messages = {
        # Message volontairement identique (email inconnu, mauvais mot de passe
        # ou compte désactivé) pour ne pas révéler quels comptes existent.
        "invalid_login": "Email ou mot de passe incorrect, ou compte désactivé.",
        "inactive": "Ce compte est désactivé.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()
