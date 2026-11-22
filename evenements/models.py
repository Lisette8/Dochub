from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Evenement(models.Model):
    """
    Événement géré par un administrateur (US-12)
    et consulté par les utilisateurs (US-13).
    """

    titre = models.CharField("titre", max_length=200)
    description = models.TextField("description", blank=True)
    date_evenement = models.DateTimeField("date de l'événement")
    lieu = models.CharField("lieu", max_length=255)

    # Administrateur qui a créé l'événement (association "Gérer" du diagramme)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evenements_crees",
        verbose_name="créé par",
    )

    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        verbose_name = "événement"
        verbose_name_plural = "événements"
        ordering = ["date_evenement"]

    def __str__(self):
        return f"{self.titre} ({self.date_evenement:%d/%m/%Y %H:%M})"

    @property
    def est_a_venir(self):
        """True si l'événement n'est pas encore passé."""
        return self.date_evenement >= timezone.now()

    def clean(self):
        """
        Validations métier, appelées automatiquement par les formulaires
        (dont ceux de l'admin Django) avant l'enregistrement.
        """
        super().clean()
        erreurs = {}

        # Titre et lieu : on refuse les valeurs composées uniquement d'espaces
        if self.titre is not None:
            self.titre = self.titre.strip()
            if not self.titre:
                erreurs["titre"] = "Le titre ne peut pas être vide."
            elif len(self.titre) < 3:
                erreurs["titre"] = "Le titre doit contenir au moins 3 caractères."

        if self.lieu is not None:
            self.lieu = self.lieu.strip()
            if not self.lieu:
                erreurs["lieu"] = "Le lieu ne peut pas être vide."

        # Date : à la création, un événement ne peut pas être dans le passé.
        # (À la modification on l'autorise, pour pouvoir corriger un événement déjà passé.)
        if self.date_evenement and self._state.adding:
            if self.date_evenement < timezone.now():
                erreurs["date_evenement"] = (
                    "La date de l'événement ne peut pas être dans le passé."
                )

        if erreurs:
            raise ValidationError(erreurs)