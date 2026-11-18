from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Gestionnaire d'utilisateurs : l'email remplace le nom d'utilisateur."""

    use_in_migrations = True

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
    - « désactiver » un compte = is_active à False (le compte ne peut plus se connecter).
    """

    class Role(models.TextChoices):
        UTILISATEUR = "UTILISATEUR", "Utilisateur"
        ADMIN = "ADMIN", "Administrateur"

    username = None
    email = models.EmailField("adresse email", unique=True)
    first_name = models.CharField("prénom", max_length=150)
    last_name = models.CharField("nom", max_length=150)
    role = models.CharField(
        "rôle", max_length=20, choices=Role.choices, default=Role.UTILISATEUR
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

    def save(self, *args, **kwargs):
        # Un Administrateur DocHub a aussi accès à l'interface /admin/ de Django.
        self.is_staff = self.role == self.Role.ADMIN
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)
