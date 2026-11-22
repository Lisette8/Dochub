from django.contrib import admin

from users.permissions import user_is_admin

from .models import Commentaire, Ticket


class CommentaireInline(admin.StackedInline):
    model = Commentaire
    extra = 1
    fields = ("auteur", "contenu", "created_at")
    readonly_fields = ("auteur", "created_at")

    # Les messages envoyés ne sont ni modifiables ni supprimables (traçabilité)
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "titre", "categorie", "priorite", "statut", "auteur", "assigne_a", "created_at")
    list_filter = ("statut", "priorite", "categorie")
    search_fields = ("titre", "description", "auteur__email")
    readonly_fields = ("created_at", "updated_at")

    # Accès réservé au rôle Administrateur (comme UserAdmin d'Amine)
    def has_module_permission(self, request):
        return user_is_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return user_is_admin(request.user)

    def has_add_permission(self, request):
        return user_is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return user_is_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return user_is_admin(request.user)

    def get_exclude(self, request, obj=None):
        # À la création, l'auteur est automatique : on cache le champ
        if obj is None:
            return ("auteur",)
        return super().get_exclude(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly.append("auteur")
        return readonly

    def save_model(self, request, obj, form, change):
        if not change:
            obj.auteur = request.user
        super().save_model(request, obj, form, change)

    def get_inlines(self, request, obj):
        # Pas de fil de discussion tant que le ticket n'est pas créé
        return [CommentaireInline] if obj else []

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        reponse_envoyee = False
        for instance in instances:
            # Un nouveau commentaire a pour auteur l'admin connecté
            if isinstance(instance, Commentaire) and instance.pk is None:
                instance.auteur = request.user
                reponse_envoyee = True
            instance.save()
        formset.save_m2m()

        # Statut automatique, sauf si l'admin l'a changé lui-même dans ce formulaire
        if reponse_envoyee and "statut" not in form.changed_data:
            ticket = form.instance
            if ticket.maj_statut_apres_reponse(par_admin=True):
                self.message_user(
                    request,
                    f"Réponse envoyée : le ticket passe à « {ticket.get_statut_display()} ».",
                )
