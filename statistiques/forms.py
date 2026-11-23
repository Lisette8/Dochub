from datetime import date, datetime
from django import forms
from django.utils import timezone

from .models import Rapport, DATE_MIN

DATE_INPUT_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d.%m.%Y",
]


class FlexibleDateField(forms.Field):
    """Champ de date flexible : accepte un objet date, YYYY-MM-DD, DD/MM/YYYY, ou un jour seul (ex: '10' ou '10/11')."""
    widget = forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})

    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, (date, datetime)):
            return value if isinstance(value, date) else value.date()

        val = str(value).strip()
        if not val:
            return None

        today = timezone.localdate()

        # Si l'utilisateur tape juste un jour : ex "10" -> 10 du mois et année en cours
        if val.isdigit():
            day = int(val)
            try:
                return date(today.year, today.month, day)
            except ValueError:
                raise forms.ValidationError(f"Le jour {day} n'est pas valide pour ce mois.")

        # Si l'utilisateur tape jour/mois : ex "10/11" -> 10/11 de l'année en cours
        if "/" in val and len(val.split("/")) == 2:
            parts = val.split("/")
            try:
                return date(today.year, int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                raise forms.ValidationError("Format invalide. Utilisez jj/mm.")

        # Essayer tous les formats standards
        for fmt in DATE_INPUT_FORMATS:
            try:
                return datetime.strptime(val, fmt).date()
            except (ValueError, TypeError):
                continue

        raise forms.ValidationError("Entrez une date valide (ex: 10, jj/mm/aaaa ou aaaa-mm-jj).")

    def prepare_value(self, value):
        if isinstance(value, (date, datetime)):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, str) and value.strip():
            try:
                dt = self.to_python(value)
                if dt:
                    return dt.strftime("%Y-%m-%d")
            except forms.ValidationError:
                pass
        return value


class RapportGenererForm(forms.ModelForm):
    """US-32 : Formulaire de génération d'un rapport statistique."""

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=DATE_INPUT_FORMATS,
    )
    date_fin = forms.DateField(
        label="Date de fin",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=DATE_INPUT_FORMATS,
    )
    statut = forms.ChoiceField(
        choices=Rapport.Statut.choices,
        initial=Rapport.Statut.NOUVEAU,
        required=False,
        label="Statut de traitement",
        widget=forms.Select(),
    )

    class Meta:
        model = Rapport
        fields = ["titre", "date_debut", "date_fin", "format", "description", "statut", "note"]
        widgets = {
            "titre": forms.TextInput(attrs={"placeholder": "Ex: Bilan mensuel Novembre 2026"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Description ou contexte du rapport (facultatif)"}),
            "format": forms.Select(),
            "statut": forms.Select(),
            "note": forms.Textarea(attrs={"rows": 3, "placeholder": "Note interne de suivi (facultatif)"}),
        }
        labels = {
            "titre": "Titre du rapport",
            "format": "Format du document",
            "description": "Description",
            "statut": "Statut de traitement",
            "note": "Note interne",
        }

    def clean_statut(self):
        return self.cleaned_data.get("statut") or Rapport.Statut.NOUVEAU

    def clean_titre(self):
        titre = self.cleaned_data.get("titre", "")
        titre = titre.strip() if titre else ""
        if not titre:
            raise forms.ValidationError("Le titre ne peut pas être vide.")
        if len(titre) < 3:
            raise forms.ValidationError("Le titre doit contenir au moins 3 caractères.")
        return titre

    def clean_description(self):
        desc = self.cleaned_data.get("description", "")
        desc = desc.strip() if desc else ""
        if desc and len(desc) < 10:
            raise forms.ValidationError("La description doit contenir au moins 10 caractères si elle est renseignée.")
        return desc

    def clean_note(self):
        note = self.cleaned_data.get("note")
        if not note or not note.strip():
            return None
        note = note.strip()
        if len(note) < 5:
            raise forms.ValidationError("La note interne doit contenir au moins 5 caractères si elle est renseignée.")
        return note

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        aujourd_hui = timezone.localdate()

        if date_debut:
            if date_debut < DATE_MIN:
                self.add_error("date_debut", "La date de début ne peut pas être avant 2000.")
            elif date_debut > aujourd_hui:
                self.add_error("date_debut", "La date de début ne peut pas être dans le futur.")

        if date_fin:
            if date_fin > aujourd_hui:
                self.add_error("date_fin", "La date de fin ne peut pas être dans le futur.")
            elif date_debut and date_fin < date_debut:
                self.add_error("date_fin", "La date de fin doit être postérieure ou égale à la date de début.")

        return cleaned_data


class RapportModifierForm(forms.ModelForm):
    """Formulaire complet pour modifier toutes les informations d'un rapport existant."""

    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=DATE_INPUT_FORMATS,
    )
    date_fin = forms.DateField(
        label="Date de fin",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=DATE_INPUT_FORMATS,
    )
    statut = forms.ChoiceField(
        choices=Rapport.Statut.choices,
        initial=Rapport.Statut.NOUVEAU,
        required=False,
        label="Statut de traitement",
        widget=forms.Select(),
    )

    class Meta:
        model = Rapport
        fields = ["titre", "date_debut", "date_fin", "format", "description", "statut", "note"]
        widgets = {
            "titre": forms.TextInput(attrs={"placeholder": "Titre du rapport"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Description (facultatif)"}),
            "format": forms.Select(),
            "statut": forms.Select(),
            "note": forms.Textarea(attrs={"rows": 4, "placeholder": "Note interne de suivi (facultatif)"}),
        }
        labels = {
            "titre": "Titre du rapport",
            "format": "Format du document",
            "description": "Description",
            "statut": "Statut de traitement",
            "note": "Note interne",
        }

    def clean_statut(self):
        return self.cleaned_data.get("statut") or Rapport.Statut.NOUVEAU

    def clean_titre(self):
        titre = self.cleaned_data.get("titre", "")
        titre = titre.strip() if titre else ""
        if not titre:
            raise forms.ValidationError("Le titre ne peut pas être vide.")
        if len(titre) < 3:
            raise forms.ValidationError("Le titre doit contenir au moins 3 caractères.")
        return titre

    def clean_description(self):
        desc = self.cleaned_data.get("description", "")
        desc = desc.strip() if desc else ""
        if desc and len(desc) < 10:
            raise forms.ValidationError("La description doit contenir au moins 10 caractères si elle est renseignée.")
        return desc

    def clean_note(self):
        note = self.cleaned_data.get("note")
        if not note or not note.strip():
            return None
        note = note.strip()
        if len(note) < 5:
            raise forms.ValidationError("La note interne doit contenir au moins 5 caractères si elle est renseignée.")
        return note

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        aujourd_hui = timezone.localdate()

        if date_debut:
            if date_debut < DATE_MIN:
                self.add_error("date_debut", "La date de début ne peut pas être avant 2000.")
            elif date_debut > aujourd_hui:
                self.add_error("date_debut", "La date de début ne peut pas être dans le futur.")

        if date_fin:
            if date_fin > aujourd_hui:
                self.add_error("date_fin", "La date de fin ne peut pas être dans le futur.")
            elif date_debut and date_fin < date_debut:
                self.add_error("date_fin", "La date de fin doit être postérieure ou égale à la date de début.")

        return cleaned_data


class RapportStatutForm(forms.ModelForm):
    """US-51 : Formulaire pour mettre à jour le statut et la note d'un rapport."""

    class Meta:
        model = Rapport
        fields = ["statut", "note"]
        widgets = {
            "statut": forms.Select(),
            "note": forms.Textarea(attrs={"rows": 4, "placeholder": "Ajouter ou modifier une note interne..."}),
        }
        labels = {
            "statut": "Statut de traitement",
            "note": "Note interne",
        }

    def clean_note(self):
        note = self.cleaned_data.get("note")
        return note.strip() if note and note.strip() else None


class RapportFiltreForm(forms.Form):
    """US-33 : Formulaire de filtres GET pour la liste des rapports (Recherche, Statut et État d'archivage)."""

    q = forms.CharField(
        required=False,
        label="Recherche",
        widget=forms.TextInput(attrs={
            "type": "search",
            "placeholder": "Rechercher par titre, description ou contenu…",
        }),
    )
    statut = forms.ChoiceField(
        choices=[("", "Tous les statuts")] + list(Rapport.Statut.choices),
        required=False,
        label="Statut",
        widget=forms.Select(),
    )
    archive = forms.ChoiceField(
        choices=[
            ("0", "Rapports actifs"),
            ("1", "Rapports archivés"),
            ("all", "Tous les rapports (actifs et archivés)"),
        ],
        required=False,
        initial="0",
        label="État",
        widget=forms.Select(),
    )
