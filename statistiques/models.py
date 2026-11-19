from django.db import models
from django.contrib.auth import get_user_model

class Rapport(models.Model):
    class Format(models.TextChoices):
        PDF = "PDF", "PDF"
        HTML = "HTML", "HTML"
        TXT = "TXT", "TXT"

    class Statut(models.TextChoices):
        NOUVEAU = "NOUVEAU", "Nouveau"
        EN_COURS = "EN_COURS", "En cours de traitement"
        TRAITE = "TRAITE", "Traité"

    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    contenu = models.TextField(blank=True)
    format = models.CharField(max_length=4, choices=Format.choices, default=Format.PDF)
    date_debut = models.DateField()
    date_fin = models.DateField()
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.NOUVEAU)
    note = models.TextField(blank=True)
    archive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre
    
    def generer_contenu(self):
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