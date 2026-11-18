from django.contrib import admin
from .models import Ticket

# Register your models here.
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "titre", "categorie", "priorite", "statut", "auteur", "assigne_a", "created_at")
    list_filter = ("statut", "priorite", "categorie")
    search_fields = ("titre", "description", "auteur__username")
    readonly_fields = ("created_at", "updated_at")

    def get_exclude(self, request, obj=None):
        # À la création, l'auteur est automatique : on cache le champ
        if obj is None:
            return ("auteur",)
        return super().get_exclude(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        # Après création, l'auteur n'est plus modifiable
        if obj is not None:
            readonly.append("auteur")
        # Un non-admin ne touche ni au statut ni à l'assignation
        if not request.user.is_superuser:
            readonly += ["statut", "assigne_a"]
        return readonly

    def save_model(self, request, obj, form, change):
        if not change:
            obj.auteur = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Le superuser voit tout, les autres seulement leurs tickets
        if request.user.is_superuser:
            return qs
        return qs.filter(auteur=request.user)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if obj is not None and not request.user.is_superuser:
            # Modifiable seulement tant que le ticket est « Ouvert »
            return allowed and obj.statut == Ticket.Statut.OUVERT
        return allowed

    def has_delete_permission(self, request, obj=None):
        # Suppression réservée à l'admin
        return request.user.is_superuser
