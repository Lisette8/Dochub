from django.db import models


class Actualite(models.Model):

    class Categorie(models.TextChoices):
        ANNONCE = "ANNONCE", "Annonce"
        EVENEMENT = "EVENEMENT", "Événement"
        INFO_GENERALE = "INFO_GENERALE", "Information générale"

    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        PUBLIE = "PUBLIE", "Publié"

    titre = models.CharField(max_length=200)
    description = models.TextField()
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