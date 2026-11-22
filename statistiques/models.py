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

        if self.titre and not self.titre.strip():
            erreurs["titre"] = "Le titre ne peut pas contenir seulement des espaces."

        if self.description:
            desc_clean = self.description.strip()
            if desc_clean and len(desc_clean) < 10:
                erreurs["description"] = "La description doit contenir au moins 10 caractères si elle est renseignée."

        if self.note:
            note_clean = self.note.strip()
            if note_clean and len(note_clean) < 5:
                erreurs["note"] = "La note interne doit contenir au moins 5 caractères si elle est renseignée."

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

        def _compter(app_label, model_name, **filtres):
            try:
                Model = apps.get_model(app_label, model_name)
                qs = Model.objects.all()
                if filtres:
                    qs = qs.filter(**filtres)
                return qs.count()
            except LookupError:
                return 0

        total_documents = _compter("documents", "Document")
        total_actualites = _compter("actualites", "Actualite")
        total_evenements = _compter("evenements", "Evenement")
        tickets_ouverts = _compter("tickets", "Ticket", statut="OUVERT")

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