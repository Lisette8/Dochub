from django import forms
from users.models import User
from .models import Commentaire, Ticket


class TicketForm(forms.ModelForm):
    """Formulaire de création et modification d'un ticket pour les utilisateurs avec contrôle de saisie strict."""

    class Meta:
        model = Ticket
        fields = ["titre", "categorie", "priorite", "description"]
        labels = {
            "titre": "Titre de la demande",
            "categorie": "Catégorie",
            "priorite": "Niveau de priorité",
            "description": "Description détaillée",
        }
        widgets = {
            "titre": forms.TextInput(attrs={
                "placeholder": "Ex : Impossible d'accéder au document RH #42...",
                "autofocus": True,
                "id": "ticket-titre",
            }),
            "categorie": forms.Select(attrs={"id": "ticket-categorie"}),
            "priorite": forms.Select(attrs={"id": "ticket-priorite"}),
            "description": forms.Textarea(attrs={
                "rows": 6,
                "placeholder": "Décrivez précisément le problème rencontré, les étapes pour le reproduire ou vos attentes...",
                "id": "ticket-description",
            }),
        }

    def clean_titre(self):
        titre = self.cleaned_data.get("titre", "").strip()
        if not titre:
            raise forms.ValidationError("Le titre du ticket ne peut pas être vide.")
        if len(titre) < 5:
            raise forms.ValidationError(
                f"Le titre doit contenir au moins 5 caractères (actuellement : {len(titre)}). Ex : « Problème de téléchargement »."
            )
        if len(titre) > 200:
            raise forms.ValidationError(
                f"Le titre ne peut pas dépasser 200 caractères (actuellement : {len(titre)})."
            )
        return titre

    def clean_description(self):
        description = self.cleaned_data.get("description", "").strip()
        if not description:
            raise forms.ValidationError("La description détaillée de votre demande est obligatoire.")
        if len(description) < 15:
            raise forms.ValidationError(
                f"La description doit comporter au moins 15 caractères pour détailler votre besoin (actuellement : {len(description)})."
            )
        if len(description) > 5000:
            raise forms.ValidationError(
                f"La description ne peut pas dépasser 5000 caractères (actuellement : {len(description)})."
            )
        return description


class CommentaireForm(forms.ModelForm):
    """Formulaire d'envoi d'une réponse dans la discussion d'un ticket avec validation."""

    class Meta:
        model = Commentaire
        fields = ["contenu"]
        labels = {"contenu": "Votre réponse"}
        widgets = {
            "contenu": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Écrivez votre message ou précisez votre réponse…",
                "id": "commentaire-contenu",
            })
        }

    def clean_contenu(self):
        contenu = self.cleaned_data.get("contenu", "").strip()
        if not contenu:
            raise forms.ValidationError("Votre message de réponse ne peut pas être vide.")
        if len(contenu) < 2:
            raise forms.ValidationError("Votre réponse doit contenir au moins 2 caractères.")
        if len(contenu) > 3000:
            raise forms.ValidationError(
                f"Votre réponse ne peut pas dépasser 3000 caractères (actuellement : {len(contenu)})."
            )
        return contenu


class AdminTicketModifierForm(forms.ModelForm):
    """Permet à l'administrateur de modifier tous les champs d'un ticket avec contrôle de saisie strict."""

    class Meta:
        model = Ticket
        fields = ["titre", "categorie", "priorite", "statut", "assigne_a", "description"]
        labels = {
            "titre": "Titre du ticket",
            "categorie": "Catégorie",
            "priorite": "Priorité",
            "statut": "Statut",
            "assigne_a": "Assigné à",
            "description": "Description",
        }
        widgets = {
            "titre": forms.TextInput(attrs={
                "placeholder": "Titre du ticket",
                "id": "admin-ticket-titre",
            }),
            "categorie": forms.Select(attrs={"id": "admin-ticket-categorie"}),
            "priorite": forms.Select(attrs={"id": "admin-ticket-priorite"}),
            "statut": forms.Select(attrs={"id": "admin-ticket-statut"}),
            "assigne_a": forms.Select(attrs={"id": "admin-ticket-assigne"}),
            "description": forms.Textarea(attrs={
                "rows": 6,
                "placeholder": "Description détaillée de la demande…",
                "id": "admin-ticket-description",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigne_a"].queryset = User.objects.filter(role=User.Role.ADMIN)
        self.fields["assigne_a"].empty_label = "Non assigné"
        self.fields["assigne_a"].required = False

    def clean_titre(self):
        titre = self.cleaned_data.get("titre", "").strip()
        if not titre:
            raise forms.ValidationError("Le titre du ticket ne peut pas être vide.")
        if len(titre) < 5:
            raise forms.ValidationError(
                f"Le titre doit contenir au moins 5 caractères (actuellement : {len(titre)})."
            )
        if len(titre) > 200:
            raise forms.ValidationError(
                f"Le titre ne peut pas dépasser 200 caractères (actuellement : {len(titre)})."
            )
        return titre

    def clean_description(self):
        description = self.cleaned_data.get("description", "").strip()
        if not description:
            raise forms.ValidationError("La description ne peut pas être vide.")
        if len(description) < 15:
            raise forms.ValidationError(
                f"La description doit comporter au moins 15 caractères (actuellement : {len(description)})."
            )
        if len(description) > 5000:
            raise forms.ValidationError(
                f"La description ne peut pas dépasser 5000 caractères (actuellement : {len(description)})."
            )
        return description

    def clean_assigne_a(self):
        assigne = self.cleaned_data.get("assigne_a")
        if assigne and getattr(assigne, "role", None) != User.Role.ADMIN:
            raise forms.ValidationError("Le ticket ne peut être assigné qu'à un utilisateur avec le rôle Administrateur.")
        return assigne


class TicketFiltreForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Recherche",
        widget=forms.TextInput(attrs={"placeholder": "Titre, description ou email…"}),
    )
    statut = forms.ChoiceField(
        required=False,
        label="Statut",
        choices=[("", "Tous")] + Ticket.Statut.choices,
    )
    priorite = forms.ChoiceField(
        required=False,
        label="Priorité",
        choices=[("", "Toutes")] + Ticket.Priorite.choices,
    )
    categorie = forms.ChoiceField(
        required=False,
        label="Catégorie",
        choices=[("", "Toutes")] + Ticket.Categorie.choices,
    )
    assigne = forms.ModelChoiceField(
        required=False,
        label="Assigné à",
        empty_label="Tous",
        queryset=User.objects.filter(role=User.Role.ADMIN),
    )
