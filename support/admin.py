from django.contrib import admin

from users.permissions import user_is_admin

from .models import Ticket


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
