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
        null=True,  # Oracle traite "" comme NULL — null=True évite les bugs silencieux
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

        # Titre : vide, que des espaces, ou trop court
        if self.titre is not None:
            titre_clean = self.titre.strip()
            if not titre_clean:
                erreurs["titre"] = "Le titre ne peut pas être vide ou contenir seulement des espaces."
            elif len(titre_clean) < 3:
                erreurs["titre"] = "Le titre doit contenir au moins 3 caractères."

        # Dates
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
        """Synthèse des indicateurs de la période (US-32).
        Tolère l'absence des autres modules avec django.apps.apps.get_model.
        """
        from django.apps import apps

        User = get_user_model()
        total_utilisateurs = User.objects.count()
        nouveaux = User.objects.filter(
            date_joined__date__range=(self.date_debut, self.date_fin)
        ).count()

        def _get_model(app_labels, model_name):
            for app_label in app_labels:
                try:
                    return apps.get_model(app_label, model_name)
                except LookupError:
                    continue
            return None

        def _compter(model, **filtres):
            if model is None:
                return 0
            try:
                qs = model.objects.all()
                if filtres:
                    qs = qs.filter(**filtres)
                return qs.count()
            except Exception:
                return 0

        total_documents = _compter(_get_model(["DocumentApp", "documents"], "Document"))
        total_actualites = _compter(_get_model(["actualites"], "Actualite"))
        total_evenements = _compter(_get_model(["evenements"], "Evenement"))
        tickets_ouverts = _compter(_get_model(["support", "tickets"], "Ticket"), statut="OUVERT")

        d_deb = self.date_debut.strftime("%d/%m/%Y")
        d_fin = self.date_fin.strftime("%d/%m/%Y")

        return (
            f"====================================================\n"
            f"         RAPPORT STATISTIQUE D'ACTIVITÉ DOCHUB      \n"
            f"====================================================\n"
            f"Titre du rapport   : {self.titre}\n"
            f"Synthèse du {d_deb} au {d_fin}\n"
            f"Format du document : {self.format}\n"
            f"----------------------------------------------------\n"
            f"DONNÉES CHIFFRÉES SUR LA PÉRIODE :\n"
            f"  • Utilisateurs au total                : {total_utilisateurs}\n"
            f"  • Nouveaux utilisateurs sur la période : {nouveaux}\n"
            f"  • Documents partagés                   : {total_documents}\n"
            f"  • Actualités publiées                  : {total_actualites}\n"
            f"  • Événements enregistrés               : {total_evenements}\n"
            f"  • Tickets de support ouverts           : {tickets_ouverts}\n"
            f"----------------------------------------------------\n"
            f"Génération automatique DocHub — Module Statistiques."
        )