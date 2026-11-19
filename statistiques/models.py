from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models
from django.utils import timezone

DATE_MIN = date(2000, 1, 1)


class Rapport(models.Model):
    class Format(models.TextChoices):
        PDF = "PDF", "PDF"
        HTML = "HTML", "HTML"
        TXT = "TXT", "TXT"

    class Statut(models.TextChoices):
        NOUVEAU = "NOUVEAU", "Nouveau"
        EN_COURS = "EN_COURS", "En cours de traitement"
        TRAITE = "TRAITE", "Traité"

    titre = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(3, "Le titre doit contenir au moins 3 caractères.")],
    )
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(1000, "La description ne doit pas dépasser 1000 caractères.")],
    )
    contenu = models.TextField(blank=True)  # généré automatiquement
    format = models.CharField(max_length=4, choices=Format.choices, default=Format.PDF)
    date_debut = models.DateField()
    date_fin = models.DateField()
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.NOUVEAU)
    note = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(500, "La note ne doit pas dépasser 500 caractères.")],
    )
    archive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Rapport"
        verbose_name_plural = "Rapports"

    def __str__(self):
        return self.titre

    def clean(self):
        erreurs = {}
        aujourd_hui = timezone.localdate()

        if self.titre and not self.titre.strip():
            erreurs["titre"] = "Le titre ne peut pas contenir seulement des espaces."

        if self.date_debut:
            if self.date_debut < DATE_MIN:
                erreurs["date_debut"] = "La date de début ne peut pas être avant 2000."
            elif self.date_debut > aujourd_hui:
                erreurs["date_debut"] = "La date de début ne peut pas être dans le futur."

        if self.date_fin:
            if self.date_fin > aujourd_hui:
                erreurs["date_fin"] = "La date de fin ne peut pas être dans le futur."
            elif self.date_debut and self.date_fin < self.date_debut:
                erreurs["date_fin"] = "La date de fin doit être postérieure ou égale à la date de début."

        if erreurs:
            raise ValidationError(erreurs)

    def generer_contenu(self):
        """Synthèse des indicateurs de la période (US32)."""
        User = get_user_model()
        total_utilisateurs = User.objects.count()
        nouveaux = User.objects.filter(
            date_joined__date__range=(self.date_debut, self.date_fin)
        ).count()
        return (
            f"Synthèse du {self.date_debut} au {self.date_fin}\n"
            f"- Utilisateurs au total : {total_utilisateurs}\n"
            f"- Nouveaux utilisateurs sur la période : {nouveaux}\n"
        )