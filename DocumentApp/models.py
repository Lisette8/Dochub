import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


def document_upload_to(instance, filename):
    return f"documents/{filename}"


class Document(models.Model):
    class TypeDocument(models.TextChoices):
        PDF = "PDF", "PDF"
        MARKDOWN = "MD", "Markdown"
        TEXTE = "TXT", "Texte (.txt)"
        AUTRE = "AUTRE", "Autre"

    class Thematique(models.TextChoices):
        TECHNIQUE = "TECHNIQUE", "Technique"
        ADMINISTRATIF = "ADMINISTRATIF", "Administratif"
        RH = "RH", "Ressources Humaines"
        FORMATION = "FORMATION", "Formation & Guides"
        JURIDIQUE = "JURIDIQUE", "Juridique"
        AUTRE = "AUTRE", "Autre"

    idDocument = models.BigAutoField(primary_key=True)
    titreDocument = models.CharField(
        max_length=200,
        verbose_name="Titre du document",
    )
    descDocument = models.TextField(
        blank=True,
        max_length=1000,
        verbose_name="Description",
    )
    type_document = models.CharField(
        max_length=10,
        choices=TypeDocument.choices,
        default=TypeDocument.PDF,
        verbose_name="Type de document",
    )
    thematique = models.CharField(
        max_length=30,
        choices=Thematique.choices,
        default=Thematique.TECHNIQUE,
        verbose_name="Thématique",
    )
    fichier = models.FileField(
        upload_to=document_upload_to,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "md", "markdown", "txt"])],
        verbose_name="Fichier",
    )
    taille_fichier = models.PositiveIntegerField(
        default=0,
        verbose_name="Taille en octets",
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents_deposes",
        verbose_name="Déposé par",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return self.titreDocument

    @property
    def titre(self):
        return self.titreDocument

    @titre.setter
    def titre(self, val):
        self.titreDocument = val

    @property
    def description(self):
        return self.descDocument

    @description.setter
    def description(self, val):
        self.descDocument = val

    @property
    def nom_fichier(self):
        try:
            f = getattr(self, "fichier", None)
            if f and f.name:
                return os.path.basename(f.name)
        except Exception:
            pass
        return ""

    @property
    def extension(self):
        try:
            f = getattr(self, "fichier", None)
            if f and f.name:
                _, ext = os.path.splitext(f.name)
                return ext.lstrip(".").upper()
        except Exception:
            pass
        try:
            return self.type_document
        except Exception:
            return "DOC"

    @property
    def taille_lisible(self):
        try:
            t = getattr(self, "taille_fichier", 0)
        except Exception:
            t = 0
        if not t:
            try:
                f = getattr(self, "fichier", None)
                if f and f.name:
                    t = f.size
            except Exception:
                t = 0
        if not t:
            return "—"
        if t < 1024:
            return f"{t} o"
        elif t < 1024 * 1024:
            return f"{t / 1024:.1f} Ko"
        else:
            return f"{t / (1024 * 1024):.1f} Mo"

    def save(self, *args, **kwargs):
        # Auto-détection du type de document TOUJOURS depuis l'extension
        try:
            if self.fichier and self.fichier.name:
                _, ext = os.path.splitext(self.fichier.name.lower())
                ext_map = {
                    ".pdf": self.TypeDocument.PDF,
                    ".md": self.TypeDocument.MARKDOWN,
                    ".markdown": self.TypeDocument.MARKDOWN,
                    ".txt": self.TypeDocument.TEXTE,
                }
                if ext in ext_map:
                    self.type_document = ext_map[ext]
        except Exception:
            pass

        # Calculer la taille du fichier
        try:
            if self.fichier:
                self.taille_fichier = self.fichier.size
        except Exception:
            pass
        super().save(*args, **kwargs)
