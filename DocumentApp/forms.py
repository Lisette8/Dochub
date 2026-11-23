import os
from django import forms
from .models import Document

EXTENSIONS_AUTORISEES = [".pdf", ".md", ".markdown", ".txt"]
TAILLE_MAX_MO = 20
TAILLE_MAX_OCTETS = TAILLE_MAX_MO * 1024 * 1024

# Mapping strict entre le type sélectionné et les extensions acceptées
TYPE_EXTENSIONS_MAP = {
    Document.TypeDocument.PDF: [".pdf"],
    Document.TypeDocument.MARKDOWN: [".md", ".markdown"],
    Document.TypeDocument.TEXTE: [".txt"],
}

EXT_TO_TYPE_LABEL = {
    ".pdf": "PDF",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".txt": "Texte (.txt)",
}


class AdminDocumentForm(forms.ModelForm):
    """Formulaire de dépôt et modification d'un document pour l'administrateur avec contrôle de saisie strict."""

    class Meta:
        model = Document
        fields = [
            "titreDocument",
            "thematique",
            "type_document",
            "fichier",
            "descDocument",
        ]
        labels = {
            "titreDocument": "Titre du document",
            "thematique": "Thématique",
            "type_document": "Type de document",
            "fichier": "Fichier (PDF, Markdown ou Texte)",
            "descDocument": "Description détaillée",
        }
        widgets = {
            "titreDocument": forms.TextInput(attrs={
                "placeholder": "Ex : Spécifications techniques DocHub v2...",
                "autofocus": True,
            }),
            "thematique": forms.Select(),
            "type_document": forms.Select(),
            "descDocument": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Description détaillée du document, contexte d'utilisation, public cible...",
            }),
            "fichier": forms.FileInput(attrs={
                "accept": ".pdf,.md,.markdown,.txt",
                "id": "doc-file-input",
            }),
        }

    def clean_titreDocument(self):
        titre = self.cleaned_data.get("titreDocument", "").strip()
        if not titre:
            raise forms.ValidationError("Le titre du document ne peut pas être vide.")
        if len(titre) < 3:
            raise forms.ValidationError("Le titre doit contenir au moins 3 caractères.")
        if len(titre) > 200:
            raise forms.ValidationError("Le titre ne peut pas dépasser 200 caractères.")
        return titre

    def clean_descDocument(self):
        desc = self.cleaned_data.get("descDocument", "").strip()
        if desc and len(desc) > 1000:
            raise forms.ValidationError(f"La description ne doit pas dépasser 1000 caractères (actuellement : {len(desc)}).")
        return desc

    def clean_fichier(self):
        fichier = self.cleaned_data.get("fichier")

        # Lors de la création, le fichier est obligatoire
        if not self.instance.pk and not fichier:
            raise forms.ValidationError("Veuillez sélectionner un fichier à déposer (PDF, Markdown ou Texte).")

        if fichier:
            # Vérification de l'extension
            nom = getattr(fichier, "name", "")
            _, ext = os.path.splitext(nom.lower())
            if ext not in EXTENSIONS_AUTORISEES:
                raise forms.ValidationError(
                    f"Format « {ext} » non autorisé. Formats acceptés : PDF (.pdf), Markdown (.md, .markdown) et Texte (.txt)."
                )

            # Vérification de la taille maximale
            if hasattr(fichier, "size") and fichier.size > TAILLE_MAX_OCTETS:
                taille_mo = fichier.size / (1024 * 1024)
                raise forms.ValidationError(
                    f"Le fichier fait {taille_mo:.1f} Mo. La taille maximale autorisée est de {TAILLE_MAX_MO} Mo."
                )

        return fichier

    def clean(self):
        cleaned_data = super().clean()
        type_doc = cleaned_data.get("type_document")
        fichier = cleaned_data.get("fichier")

        # 1. Contrôle de cohérence lors d'un nouveau fichier téléversé
        if fichier and type_doc and type_doc in TYPE_EXTENSIONS_MAP:
            nom = getattr(fichier, "name", "")
            _, ext = os.path.splitext(nom.lower())
            expected_exts = TYPE_EXTENSIONS_MAP[type_doc]
            if ext not in expected_exts:
                label_attendu = dict(Document.TypeDocument.choices).get(type_doc, type_doc)
                ext_reelle = EXT_TO_TYPE_LABEL.get(ext, ext)
                msg = (
                    f"Incohérence entre le type et le fichier : vous avez sélectionné le type « {label_attendu} », "
                    f"mais le fichier « {nom} » est un fichier {ext_reelle} ({ext}). "
                    f"Veuillez ajuster le type ou sélectionner un fichier {label_attendu}."
                )
                self.add_error("type_document", msg)

        # 2. Contrôle de cohérence lors d'une modification sans nouveau fichier (fichier déjà existant)
        elif not fichier and self.instance.pk and getattr(self.instance, "fichier", None) and type_doc and type_doc in TYPE_EXTENSIONS_MAP:
            existing_nom = self.instance.nom_fichier
            _, ext = os.path.splitext(existing_nom.lower())
            expected_exts = TYPE_EXTENSIONS_MAP[type_doc]
            if ext and ext not in expected_exts:
                label_attendu = dict(Document.TypeDocument.choices).get(type_doc, type_doc)
                ext_reelle = EXT_TO_TYPE_LABEL.get(ext, ext)
                msg = (
                    f"Incohérence : le document actuel contient le fichier « {existing_nom} » ({ext_reelle}). "
                    f"Vous ne pouvez pas lui attribuer le type « {label_attendu} ». "
                    f"Veuillez sélectionner le type correspondant ({ext_reelle}) ou téléverser un fichier {label_attendu}."
                )
                self.add_error("type_document", msg)

        return cleaned_data


# Formulaire historique conservé pour rétro-compatibilité
class DocumentForm(AdminDocumentForm):
    pass
