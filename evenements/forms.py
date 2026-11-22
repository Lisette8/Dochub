from django import forms
from django.utils import timezone

from .models import Evenement

# Format des champs <input type="datetime-local"> du navigateur
FORMAT_DATETIME_LOCAL = "%Y-%m-%dT%H:%M"


class EvenementForm(forms.ModelForm):
    """Formulaire de création / modification d'un événement (interface DocHub, réservé à l'admin).

    Les règles métier (titre, lieu, date passée à la création, heure de fin,
    capacité inférieure au nombre d'inscrits) sont dans Evenement.clean() :
    un ModelForm les appelle automatiquement.
    """

    class Meta:
        model = Evenement
        fields = ["titre", "description", "date_evenement", "date_fin", "lieu", "capacite"]
        labels = {
            "titre": "Titre",
            "description": "Description",
            "date_evenement": "Date et heure de début",
            "date_fin": "Date et heure de fin",
            "lieu": "Lieu",
            "capacite": "Capacité (places)",
        }
        widgets = {
            "titre": forms.TextInput(attrs={
                "placeholder": "Ex. : Atelier Git & Scrum", "maxlength": 200, "autocomplete": "off",
            }),
            "description": forms.Textarea(attrs={
                "rows": 4, "placeholder": "Objectif, programme, public concerné, matériel à apporter…",
            }),
            "date_evenement": forms.DateTimeInput(
                format=FORMAT_DATETIME_LOCAL, attrs={"type": "datetime-local"},
            ),
            "date_fin": forms.DateTimeInput(
                format=FORMAT_DATETIME_LOCAL, attrs={"type": "datetime-local"},
            ),
            "lieu": forms.TextInput(attrs={
                "placeholder": "Ex. : Salle B12, Amphi A, en ligne (lien Teams)…",
                "maxlength": 255, "autocomplete": "off",
            }),
            "capacite": forms.NumberInput(attrs={"min": 1, "placeholder": "Illimitée"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Accepte le format envoyé par <input type="datetime-local">
        for nom in ("date_evenement", "date_fin"):
            self.fields[nom].input_formats = [FORMAT_DATETIME_LOCAL, "%Y-%m-%dT%H:%M:%S"]

    def clean_date_fin(self):
        """La date de fin ne peut pas être dans le passé (ex. : la date d'hier).

        La règle ne s'applique que si le champ est rempli ou modifié : on peut
        toujours corriger la description d'un événement déjà terminé sans
        toucher à sa date de fin.
        """
        date_fin = self.cleaned_data.get("date_fin")
        if not date_fin:
            return date_fin

        # Valeur déjà enregistrée (modification). Le navigateur envoie l'heure à la
        # minute près : on compare donc à la minute près.
        ancienne = self.instance.date_fin if self.instance.pk else None
        inchangee = ancienne is not None and (
            date_fin.replace(second=0, microsecond=0) == ancienne.replace(second=0, microsecond=0)
        )
        if not inchangee and date_fin < timezone.now():
            raise forms.ValidationError("La date de fin ne peut pas être dans le passé.")
        return date_fin

    def clean_capacite(self):
        capacite = self.cleaned_data.get("capacite")
        if capacite is not None and capacite < 1:
            raise forms.ValidationError(
                "La capacité doit être d'au moins 1 place (laissez vide pour une capacité illimitée)."
            )
        return capacite