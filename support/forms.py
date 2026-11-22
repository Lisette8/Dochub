from django import forms

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
