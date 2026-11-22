from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models

from .validators import contient_une_lettre


class Actualite(models.Model):

    class Categorie(models.TextChoices):
        ANNONCE = "ANNONCE", "Annonce"
        EVENEMENT = "EVENEMENT", "Événement"
        INFO_GENERALE = "INFO_GENERALE", "Information générale"

    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        PUBLIE = "PUBLIE", "Publié"

    titre = models.CharField(
        max_length=200,
        validators=[
            MinLengthValidator(5, message="Le titre doit contenir au moins %(limit_value)d caractères."),
            contient_une_lettre,
        ],
    )
    description = models.TextField(
        validators=[
            MinLengthValidator(20, message="La description doit contenir au moins %(limit_value)d caractères."),
            MaxLengthValidator(5000, message="La description ne peut pas dépasser %(limit_value)d caractères."),
        ],
    )
    categorie = models.CharField(
        max_length=20,
        choices=Categorie.choices,
        default=Categorie.INFO_GENERALE,
    )
    statut = models.CharField(
        max_length=10,
        choices=Statut.choices,
        default=Statut.BROUILLON,
    )
    epinglee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "actualité"
        verbose_name_plural = "actualités"
        ordering = ["-created_at"]

    def __str__(self):
        return self.titre

    def clean(self):
        super().clean()
        erreurs = {}

        if self.epinglee and self.statut != self.Statut.PUBLIE:
            erreurs["epinglee"] = "Seule une actualité publiée peut être épinglée."

        if self.titre:
            doublon = Actualite.objects.filter(titre__iexact=self.titre.strip())
            if self.pk:
                doublon = doublon.exclude(pk=self.pk)
            if doublon.exists():
                erreurs["titre"] = "Une actualité avec ce titre existe déjà."

        if erreurs:
            raise ValidationError(erreurs)