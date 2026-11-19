from django.conf import settings
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