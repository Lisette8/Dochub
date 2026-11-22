from django.conf import settings
from django.db import models

# Create your models here.
class Ticket(models.Model):

    class Categorie(models.TextChoices):
        TECHNIQUE = "TECHNIQUE", "Problème technique"
        DOCUMENT = "DOCUMENT", "Question sur un document"
        ACCES = "ACCES", "Demande d'accès"
        SUGGESTION = "SUGGESTION", "Suggestion"
        AUTRE = "AUTRE", "Autre"

    class Priorite(models.TextChoices):
        BASSE = "BASSE", "Basse"
        NORMALE = "NORMALE", "Normale"
        HAUTE = "HAUTE", "Haute"
        URGENTE = "URGENTE", "Urgente"

    class Statut(models.TextChoices):
        OUVERT = "OUVERT", "Ouvert"
        EN_COURS = "EN_COURS", "En cours"
        EN_ATTENTE = "EN_ATTENTE", "En attente de l'utilisateur"
        RESOLU = "RESOLU", "Résolu"
        FERME = "FERME", "Fermé"

    titre = models.CharField("titre", max_length=200)
    description = models.TextField("description")
    categorie = models.CharField(
        "catégorie", max_length=20,
        choices=Categorie.choices, default=Categorie.AUTRE,
    )
    priorite = models.CharField(
        "priorité", max_length=20,
        choices=Priorite.choices, default=Priorite.NORMALE,
    )
    statut = models.CharField(
        "statut", max_length=20,
        choices=Statut.choices, default=Statut.OUVERT,
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets",
        verbose_name="auteur",
    )
    assigne_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="tickets_assignes",
        verbose_name="assigné à",
    )
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "ticket"
        verbose_name_plural = "tickets"

    def __str__(self):
        return f"#{self.pk} - {self.titre}"

    def maj_statut_apres_reponse(self, par_admin):
            """Applique la règle de changement de statut après une réponse.
            Renvoie True si le statut a changé."""
            ancien = self.statut
            if par_admin:
                if self.statut in (self.Statut.OUVERT, self.Statut.EN_COURS):
                    self.statut = self.Statut.EN_ATTENTE
            else:
                if self.statut in (self.Statut.EN_ATTENTE, self.Statut.RESOLU):
                    self.statut = self.Statut.EN_COURS
            if self.statut != ancien:
                self.save(update_fields=["statut", "updated_at"])
                return True
            return False




class Commentaire(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="commentaires",
        verbose_name="ticket",
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commentaires_support",
        verbose_name="auteur",
    )
    contenu = models.TextField("message")
    created_at = models.DateTimeField("envoyé le", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "commentaire"
        verbose_name_plural = "commentaires"

    def __str__(self):
        return f"Commentaire #{self.pk} sur le ticket #{self.ticket_id}"
