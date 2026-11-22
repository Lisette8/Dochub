import re

from django.core.exceptions import ValidationError


def contient_une_lettre(valeur):
    """Refuse les saisies du type « 12345 » ou « !!! »."""
    if not re.search(r"[^\W\d_]", valeur):
        raise ValidationError("Ce champ doit contenir au moins une lettre.")