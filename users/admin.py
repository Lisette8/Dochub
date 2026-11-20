"""CRUD des comptes DocHub dans l'admin Django (/admin/).

- Créer : rôle Utilisateur par défaut (option Administrateur), mot de passe facultatif
  (vide = e-mail d'activation, comme US-05).
- Lire : liste avec recherche (nom, email), filtres (rôle, statut), tri.
- Modifier : identité, rôle (promouvoir / rétrograder), statut, suspension, motif.
- Supprimer : avec la page de confirmation de Django.
- Actions groupées : promouvoir, rétrograder, suspendre 7 jours, bloquer, fermer,
  rouvrir, renvoyer l'e-mail d'activation.

Accès : les comptes de rôle Administrateur (pas seulement les superutilisateurs).
Garde-fou : un admin ne peut pas se supprimer, se rétrograder, ni suspendre /
bloquer / fermer son propre compte.
"""
from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils import timezone

from .admin_forms import UserAdminChangeForm, UserAdminCreationForm
from .models import User
from .permissions import user_is_admin
from .services import send_activation_email

# DocHub gère les droits par rôle (Utilisateur / Administrateur), pas par groupes.
admin.site.unregister(Group)

admin.site.site_header = "DocHub — Administration"
admin.site.site_title = "DocHub"
admin.site.index_title = "Gestion de la plateforme"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    list_display = ["email", "first_name", "last_name", "role", "statut_affiche", "est_active",
                    "last_login", "date_joined"]
    list_display_links = ["email"]
    list_filter = ["role", "statut"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    list_per_page = 25
    readonly_fields = ["last_login", "date_joined"]

    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Informations personnelles", {"fields": ["first_name", "last_name"]}),
        ("Rôle", {"fields": ["role"],
                  "description": "Utilisateur = compte normal. Administrateur = gère la plateforme et l'admin Django."}),
        ("Statut du compte", {"fields": ["statut", "suspendu_jusqua", "motif_statut"],
                              "description": "Seul un compte « Ouvert » peut se connecter. "
                                             "« Suspendu » demande une date de fin."}),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["first_name", "last_name", "email"]}),
        ("Rôle et statut", {"classes": ["wide"], "fields": ["role", "statut"]}),
        ("Mot de passe (facultatif)", {"classes": ["wide"], "fields": ["password1", "password2"]}),
    ]
    actions = ["promouvoir_admin", "retrograder_utilisateur", "suspendre_7_jours", "bloquer", "fermer",
               "rouvrir", "renvoyer_activation"]

    # ---------- Colonnes ----------

    @admin.display(description="Statut", ordering="statut")
    def statut_affiche(self, obj):
        if obj.statut == User.Statut.SUSPENDU and obj.suspendu_jusqua:
            return f"Suspendu jusqu'au {timezone.localtime(obj.suspendu_jusqua):%d/%m/%Y %H:%M}"
        return obj.get_statut_display()

    @admin.display(description="Activé", boolean=True)
    def est_active(self, obj):
        """Faux tant que l'utilisateur n'a pas choisi son mot de passe (lien d'activation)."""
        return not obj.est_en_attente_activation

    # ---------- Permissions : rôle Administrateur ----------

    def _is_dochub_admin(self, request):
        return user_is_admin(request.user)

    def has_module_permission(self, request):
        return self._is_dochub_admin(request)

    def has_view_permission(self, request, obj=None):
        return self._is_dochub_admin(request)

    def has_add_permission(self, request):
        return self._is_dochub_admin(request)

    def has_change_permission(self, request, obj=None):
        return self._is_dochub_admin(request)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.pk == request.user.pk:
            return False  # on ne supprime pas son propre compte
        return self._is_dochub_admin(request)

    # ---------- Formulaires ----------

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.acting_user = request.user
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and getattr(form, "sends_activation_email", False):
            send_activation_email(request, obj)
            self.message_user(request, f"Un e-mail d'activation a été envoyé à {obj.email}.", messages.INFO)

    # ---------- Actions groupées ----------

    def _others(self, request, queryset, what):
        """Retire l'admin connecté de la sélection (il ne peut pas se l'appliquer)."""
        if queryset.filter(pk=request.user.pk).exists():
            self.message_user(request, f"Votre propre compte a été ignoré : vous ne pouvez pas vous {what}.",
                              messages.WARNING)
        return queryset.exclude(pk=request.user.pk)

    def _apply(self, request, queryset, done, **changes):
        # save() sur chaque compte (et non queryset.update) pour garder is_staff / is_active cohérents.
        count = 0
        for user in queryset:
            for field, value in changes.items():
                setattr(user, field, value)
            user.save()
            count += 1
        self.message_user(request, f"{count} compte(s) {done}.", messages.SUCCESS)

    @admin.action(description="Promouvoir en Administrateur")
    def promouvoir_admin(self, request, queryset):
        self._apply(request, queryset, "promu(s) Administrateur", role=User.Role.ADMIN)

    @admin.action(description="Rétrograder en Utilisateur")
    def retrograder_utilisateur(self, request, queryset):
        self._apply(request, self._others(request, queryset, "rétrograder"), "rétrogradé(s) Utilisateur",
                    role=User.Role.UTILISATEUR)

    @admin.action(description="Suspendre 7 jours")
    def suspendre_7_jours(self, request, queryset):
        self._apply(request, self._others(request, queryset, "suspendre"), "suspendu(s) pour 7 jours",
                    statut=User.Statut.SUSPENDU, suspendu_jusqua=timezone.now() + timedelta(days=7))

    @admin.action(description="Bloquer")
    def bloquer(self, request, queryset):
        self._apply(request, self._others(request, queryset, "bloquer"), "bloqué(s)", statut=User.Statut.BLOQUE)

    @admin.action(description="Fermer (désactiver)")
    def fermer(self, request, queryset):
        self._apply(request, self._others(request, queryset, "fermer"), "fermé(s)", statut=User.Statut.FERME)

    @admin.action(description="Rouvrir")
    def rouvrir(self, request, queryset):
        self._apply(request, queryset, "rouvert(s)", statut=User.Statut.OUVERT)

    @admin.action(description="Renvoyer l'e-mail d'activation")
    def renvoyer_activation(self, request, queryset):
        pending = [u for u in queryset if u.est_en_attente_activation]
        for user in pending:
            send_activation_email(request, user)
        skipped = queryset.count() - len(pending)
        self.message_user(request, f"E-mail d'activation renvoyé à {len(pending)} compte(s).", messages.SUCCESS)
        if skipped:
            self.message_user(request, f"{skipped} compte(s) ignoré(s) : mot de passe déjà choisi.", messages.INFO)
