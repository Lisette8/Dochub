from django import forms
from users.models import User
from .models import Commentaire, Ticket


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["titre", "categorie", "priorite", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}

class CommentaireForm(forms.ModelForm):
    class Meta:
        model = Commentaire
        fields = ["contenu"]
        labels = {"contenu": "Votre réponse"}
        widgets = {"contenu": forms.Textarea(attrs={"rows": 4, "placeholder": "Écrivez votre message…"})}


class TicketFiltreForm(forms.Form):
    q = forms.CharField(
        required=False, label="Recherche",
        widget=forms.TextInput(attrs={"placeholder": "Titre, description ou email…"}),
    )
    statut = forms.ChoiceField(
        required=False, label="Statut", choices=[("", "Tous")] + Ticket.Statut.choices)
    priorite = forms.ChoiceField(
        required=False, label="Priorité", choices=[("", "Toutes")] + Ticket.Priorite.choices)
    categorie = forms.ChoiceField(
        required=False, label="Catégorie", choices=[("", "Toutes")] + Ticket.Categorie.choices)
    assigne = forms.ModelChoiceField(
        required=False, label="Assigné à", empty_label="Tous",
        queryset=User.objects.filter(role=User.Role.ADMIN),
    )
