from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Gestionnaire d'utilisateurs : l'email remplace le nom d'utilisateur."""

    use_in_migrations = True

    def get_by_natural_key(self, username):
        # Connexion insensible à la casse : majuscules et minuscules sont équivalentes
        # (admin Django, JWT et API passent tous par ici).
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username.strip()})

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.UTILISATEUR)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["role"] = User.Role.ADMIN
        extra_fields["is_superuser"] = True
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Compte de la plateforme DocHub (classe « Compte » du diagramme de classes).

    - connexion par email (pas de nom d'utilisateur) ;
    - deux rôles : Utilisateur et Administrateur ;
    - statut du compte (diagramme de classes : OUVERT / BLOQUÉ / FERMÉ, + SUSPENDU) ;
      seul un compte « Ouvert » peut se connecter (is_active est déduit du statut).

    Statuts :
      OUVERT   : compte normal, connexion autorisée ;
      SUSPENDU : interdit de connexion jusqu'à `suspendu_jusqua`, puis rouvert automatiquement ;
      BLOQUE   : interdit de connexion jusqu'à ce qu'un admin le rouvre (sécurité, abus) ;
      FERME    : compte fermé / désactivé (US-22), plus de connexion.
    """

    class Role(models.TextChoices):
        UTILISATEUR = "UTILISATEUR", "Utilisateur"
        ADMIN = "ADMIN", "Administrateur"

    class Statut(models.TextChoices):
        OUVERT = "OUVERT", "Ouvert"
        SUSPENDU = "SUSPENDU", "Suspendu"
        BLOQUE = "BLOQUE", "Bloqué"
        FERME = "FERME", "Fermé"

    username = None
    email = models.EmailField("adresse email", unique=True)
    first_name = models.CharField("prénom", max_length=150)
    last_name = models.CharField("nom", max_length=150)
    role = models.CharField(
        "rôle", max_length=20, choices=Role.choices, default=Role.UTILISATEUR
    )
    statut = models.CharField(
        "statut du compte", max_length=10, choices=Statut.choices, default=Statut.OUVERT
    )
    suspendu_jusqua = models.DateTimeField(
        "suspendu jusqu'au", null=True, blank=True,
        help_text="Obligatoire pour le statut « Suspendu » : le compte se rouvre automatiquement après cette date.",
    )
    motif_statut = models.CharField(
        "motif", max_length=255, blank=True,
        help_text="Raison de la suspension, du blocage ou de la fermeture (facultatif).",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def est_en_attente_activation(self):
        """Compte créé par un admin dont l'utilisateur n'a pas encore choisi son mot de passe."""
        return not self.has_usable_password()

    def clean(self):
        super().clean()
        if self.statut == self.Statut.SUSPENDU:
            if not self.suspendu_jusqua:
                raise ValidationError({"suspendu_jusqua": "Indiquez jusqu'à quand le compte est suspendu."})
            if self.suspendu_jusqua <= timezone.now():
                raise ValidationError({"suspendu_jusqua": "La date de fin de suspension doit être dans le futur."})

    def lever_suspension_si_expiree(self):
        """Rouvre le compte si sa suspension est terminée. Renvoie True si le compte a été rouvert."""
        if (self.statut == self.Statut.SUSPENDU and self.suspendu_jusqua
                and self.suspendu_jusqua <= timezone.now()):
            self.statut = self.Statut.OUVERT
            self.motif_statut = ""
            self.save()
            return True
        return False

    def save(self, *args, **kwargs):
        # Un Administrateur DocHub a aussi accès à l'interface /admin/ de Django ;
        # un compte repassé « Utilisateur » perd tous les droits d'administration.
        self.is_staff = self.role == self.Role.ADMIN
        if self.role != self.Role.ADMIN:
            self.is_superuser = False
        # Seul un compte « Ouvert » peut se connecter.
        self.is_active = self.statut == self.Statut.OUVERT
        if self.statut != self.Statut.SUSPENDU:
            self.suspendu_jusqua = None
        if self.statut == self.Statut.OUVERT:
            self.motif_statut = ""
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)
