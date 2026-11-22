from django import template
from django.utils import timezone

register = template.Library()

MOIS_COURTS = [
    "JANV", "FÉVR", "MARS", "AVR", "MAI", "JUIN",
    "JUIL", "AOÛT", "SEPT", "OCT", "NOV", "DÉC",
]


@register.filter(expects_localtime=True)
def mois_court(valeur):
    """Mois abrégé en majuscules pour les pastilles de date : 18 / NOV."""
    if not valeur:
        return ""
    if timezone.is_aware(valeur):
        valeur = timezone.localtime(valeur)
    return MOIS_COURTS[valeur.month - 1]


@register.filter
def couleur(evenement):
    """Couleur stable d'un événement (3 variantes, comme sur la maquette)."""
    return f"c{evenement.pk % 3}"


@register.filter
def horaire(evenement):
    """Horaire affiché : "14:00 – 16:00", "14:00 – 12/12 10:00" (sur 2 jours) ou "14:00"."""
    debut = timezone.localtime(evenement.date_evenement)
    texte = debut.strftime("%H:%M")
    if evenement.date_fin:
        fin = timezone.localtime(evenement.date_fin)
        if fin.date() == debut.date():
            texte += " – " + fin.strftime("%H:%M")
        else:
            texte += " – " + fin.strftime("%d/%m %H:%M")
    return texte