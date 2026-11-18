import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm

from .models import User


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


# ---------- Validation commune ----------

NAME_ERRORS = {"required": "Ce champ est obligatoire.", "max_length": "150 caractères maximum."}
EMAIL_ERRORS = {
    "required": "L'adresse email est obligatoire.",
    "invalid": "Saisissez une adresse email valide.",
}


def clean_person_name(value):
    """Prénom / nom : espaces superflus retirés, lettres (accents compris), espaces, ' et - seulement."""
    value = " ".join(value.split())
    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' -]+", value):
        raise forms.ValidationError("Lettres, espaces, apostrophes et tirets uniquement.")
    return value


def clean_new_email(value):
    """Email en minuscules, et unique (insensible à la casse)."""
    email = value.strip().lower()
    if User.objects.filter(email__iexact=email).exists():
        raise forms.ValidationError("Un compte existe déjà avec cette adresse email.")
    return email


class _AccountFieldsMixin:
    """Contrôles communs aux formulaires qui créent un compte."""

    def clean_first_name(self):
        return clean_person_name(self.cleaned_data["first_name"])

    def clean_last_name(self):
        return clean_person_name(self.cleaned_data["last_name"])

    def clean_email(self):
        return clean_new_email(self.cleaned_data["email"])


# ---------- Inscription (l'utilisateur crée son propre compte) ----------

class RegisterForm(_AccountFieldsMixin, forms.Form):
    first_name = forms.CharField(label="Prénom", max_length=150, error_messages=NAME_ERRORS,
                                 widget=forms.TextInput(attrs={"placeholder": "Prénom", "autocomplete": "given-name"}))
    last_name = forms.CharField(label="Nom", max_length=150, error_messages=NAME_ERRORS,
                                widget=forms.TextInput(attrs={"placeholder": "Nom", "autocomplete": "family-name"}))
    email = forms.EmailField(label="Adresse e-mail", max_length=254, error_messages=EMAIL_ERRORS,
                             widget=forms.EmailInput(attrs={"placeholder": "prenom.nom@organisation.tn",
                                                            "autocomplete": "email"}))
    password1 = forms.CharField(label="Mot de passe", strip=False,
                                error_messages={"required": "Le mot de passe est obligatoire."},
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password",
                                                                  "placeholder": "8 caractères minimum"}))
    password2 = forms.CharField(label="Confirmer le mot de passe", strip=False,
                                error_messages={"required": "Confirmez le mot de passe."},
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password",
                                                                  "placeholder": "••••••••"}))

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", "Les deux mots de passe ne correspondent pas.")
            else:
                # Règles de settings.AUTH_PASSWORD_VALIDATORS (longueur, trop courant, etc.)
                candidate = User(email=cleaned.get("email", ""), first_name=cleaned.get("first_name", ""),
                                 last_name=cleaned.get("last_name", ""))
                try:
                    password_validation.validate_password(p1, candidate)
                except forms.ValidationError as e:
                    self.add_error("password1", e)
        return cleaned

    def save(self):
        # Une inscription crée toujours un compte « Utilisateur » : seul l'admin peut donner le rôle Administrateur.
        d = self.cleaned_data
        return User.objects.create_user(
            email=d["email"], password=d["password1"], first_name=d["first_name"],
            last_name=d["last_name"], role=User.Role.UTILISATEUR,
        )


# ---------- US-05 : l'admin crée un compte et attribue un rôle ----------

class AdminCreateUserForm(_AccountFieldsMixin, forms.Form):
    first_name = forms.CharField(label="Prénom", max_length=150, error_messages=NAME_ERRORS,
                                 widget=forms.TextInput(attrs={"placeholder": "Prénom"}))
    last_name = forms.CharField(label="Nom", max_length=150, error_messages=NAME_ERRORS,
                                widget=forms.TextInput(attrs={"placeholder": "Nom"}))
    email = forms.EmailField(label="E-mail", max_length=254, error_messages=EMAIL_ERRORS,
                             widget=forms.EmailInput(attrs={"placeholder": "prenom.nom@dochub.tn"}))
    role = forms.ChoiceField(label="Rôle", choices=User.Role.choices, initial=User.Role.UTILISATEUR,
                             error_messages={"required": "Choisissez un rôle.",
                                             "invalid_choice": "Rôle invalide."})
    statut = forms.ChoiceField(label="Statut du compte", choices=User.Statut.choices,
                               initial=User.Statut.OUVERT,
                               error_messages={"required": "Choisissez un statut.",
                                               "invalid_choice": "Statut invalide."})


# ---------- Activation : l'utilisateur créé par l'admin choisit son mot de passe ----------

class ActivationForm(SetPasswordForm):
    error_messages = {"password_mismatch": "Les deux mots de passe ne correspondent pas."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "Mot de passe"
        self.fields["new_password2"].label = "Confirmer le mot de passe"
        self.fields["new_password1"].help_text = ""
        self.fields["new_password1"].error_messages["required"] = "Le mot de passe est obligatoire."
        self.fields["new_password2"].error_messages["required"] = "Confirmez le mot de passe."
