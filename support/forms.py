from django import forms

from .models import Ticket


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["titre", "categorie", "priorite", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}
