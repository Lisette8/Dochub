from django import forms

from .models import Actualite


class ActualiteForm(forms.ModelForm):
    class Meta:
        model = Actualite
        fields = ["titre", "description", "categorie", "statut", "epinglee"]
        labels = {"epinglee": "Épingler sur la page d'accueil"}
        widgets = {"description": forms.Textarea(attrs={"rows": 8})}