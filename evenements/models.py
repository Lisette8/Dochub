from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone


class Evenement(models.Model):
    """
    Événement géré par un administrateur (US-12),
    consulté par les utilisateurs (US-13) qui peuvent s'y inscrire (US-28).
    """

    titre = models.CharField("titre", max_length=200)
    description = models.TextField("description", blank=True)
    date_evenement = models.DateTimeField("date de l'événement")
    date_fin = models.DateTimeField(
        "heure de fin",
        null=True,
        blank=True,
        help_text="Facultatif. Doit être postérieure à la date de début.",
    )
    lieu = models.CharField("lieu", max_length=255)
    capacite = models.PositiveIntegerField(
        "capacité",
        null=True,
        blank=True,
        help_text="Nombre de places disponibles. Laissez vide pour un accès illimité.",
    )

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

    # ------------------------------------------------------------------
    # Statut dans le temps
    # ------------------------------------------------------------------
    @property
    def est_a_venir(self):
        """True si l'événement n'a pas encore commencé."""
        return self.date_evenement >= timezone.now()

    @property
    def est_en_cours(self):
        """True si l'événement a commencé et que son heure de fin n'est pas passée."""
        maintenant = timezone.now()
        return bool(self.date_fin) and self.date_evenement < maintenant <= self.date_fin

    @property
    def statut(self):
        """Libellé affiché : "À venir", "En cours" ou "Terminé"."""
        if self.est_a_venir:
            return "À venir"
        if self.est_en_cours:
            return "En cours"
        return "Terminé"

    # ------------------------------------------------------------------
    # Participants (classe d'association Participation)
    # ------------------------------------------------------------------
    @property
    def nombre_participants(self):
        """/nombreParticipants du diagramme.

        Les vues ajoutent un compteur `nb_inscrits` avec annotate() pour éviter
        une requête par événement ; sinon on compte directement en base.
        """
        if "nb_inscrits" in self.__dict__:
            return self.__dict__["nb_inscrits"]
        if self.pk is None:
            return 0
        return self.participations.count()

    @property
    def places_restantes(self):
        """Nombre de places libres, ou None si les places sont illimitées."""
        if self.capacite is None:
            return None
        return max(self.capacite - self.nombre_participants, 0)

    @property
    def est_complet(self):
        return self.capacite is not None and self.nombre_participants >= self.capacite

    @property
    def taux_remplissage(self):
        """Pourcentage de places occupées (0 à 100), ou None si illimité."""
        if self.capacite is None:
            return None
        if self.capacite == 0:
            return 100
        return min(round(self.nombre_participants * 100 / self.capacite), 100)

    @property
    def presque_complet(self):
        """Au moins 90 % des places prises, sans être complet."""
        taux = self.taux_remplissage
        return taux is not None and taux >= 90 and not self.est_complet

    @property
    def inscription_ouverte(self):
        """On peut s'inscrire tant que l'événement n'a pas commencé et n'est pas complet."""
        return self.est_a_venir and not self.est_complet

    # ------------------------------------------------------------------
    # Validations
    # ------------------------------------------------------------------
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

        # Heure de fin : doit être après le début
        if self.date_fin and self.date_evenement and self.date_fin <= self.date_evenement:
            erreurs["date_fin"] = "L'heure de fin doit être postérieure à la date de début."

        # Capacité : on ne peut pas la descendre sous le nombre d'inscrits actuel
        if self.capacite is not None and self.pk:
            inscrits = self.participations.count()
            if self.capacite < inscrits:
                erreurs["capacite"] = (
                    f"La capacité ne peut pas être inférieure au nombre d'inscrits ({inscrits})."
                )

        if erreurs:
            raise ValidationError(erreurs)


class Participation(models.Model):
    """
    Classe d'association entre un utilisateur et un événement (US-28).
    Un utilisateur ne peut s'inscrire qu'une seule fois au même événement.
    """

    evenement = models.ForeignKey(
        Evenement,
        on_delete=models.CASCADE,
        related_name="participations",
        verbose_name="événement",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="participations",
        verbose_name="utilisateur",
    )
    date_inscription = models.DateTimeField("date d'inscription", auto_now_add=True)
    present = models.BooleanField("présent", default=False)

    class Meta:
        verbose_name = "participation"
        verbose_name_plural = "participations"
        ordering = ["date_inscription"]
        constraints = [
            models.UniqueConstraint(
                fields=["evenement", "utilisateur"],
                name="unique_participation",
            )
        ]

    def __str__(self):
        return f"{self.utilisateur} → {self.evenement.titre}"

    def clean(self):
        """Règles vérifiées aussi quand l'admin ajoute un participant à la main."""
        super().clean()
        if not self._state.adding or not self.evenement_id:
            return
        # L'administrateur organise les événements : il ne s'y inscrit pas.
        if self.utilisateur_id and getattr(self.utilisateur, "is_admin", False):
            raise ValidationError(
                {"utilisateur": "Un administrateur organise les événements et ne peut pas s'y inscrire."}
            )
        evenement = self.evenement
        if not evenement.est_a_venir:
            raise ValidationError(
                {"evenement": "Impossible de s'inscrire à un événement qui a déjà commencé."}
            )
        if evenement.capacite is not None and evenement.participations.count() >= evenement.capacite:
            raise ValidationError({"evenement": "Cet événement est complet."})


def avec_nb_inscrits(queryset):
    """Ajoute à chaque événement son nombre d'inscrits (`nb_inscrits`) en une seule requête.

    On utilise une sous-requête plutôt que annotate(Count("participations")) :
    avec Count, Django fait un GROUP BY sur toutes les colonnes de l'événement,
    y compris `description` (type NCLOB sous Oracle), ce qu'Oracle refuse
    (erreur ORA-22848). La sous-requête ne regroupe que sur l'id de l'événement.
    """
    compte = (
        Participation.objects.filter(evenement=OuterRef("pk"))
        .order_by()
        .values("evenement")
        .annotate(total=Count("pk"))
        .values("total")
    )
    return queryset.annotate(
        nb_inscrits=Coalesce(Subquery(compte, output_field=IntegerField()), Value(0))
    )