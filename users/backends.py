from django.contrib.auth.backends import ModelBackend


class StatutBackend(ModelBackend):
    """Connexion par email qui respecte le statut du compte.

    Une suspension terminée est levée automatiquement au moment où l'utilisateur
    se reconnecte. Les autres règles (seul un compte « Ouvert » peut se connecter)
    passent par is_active, que User.save() déduit du statut.

    Ce contrôle s'applique aussi à chaque requête d'une session déjà ouverte :
    un compte suspendu, bloqué ou fermé est déconnecté immédiatement.
    """

    def user_can_authenticate(self, user):
        if user is not None:
            user.lever_suspension_si_expiree()
        return super().user_can_authenticate(user)
