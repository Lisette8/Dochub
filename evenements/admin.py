from django.contrib import admin

from .models import Evenement


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    # Colonnes affichées dans la liste
    list_display = ("titre", "date_evenement", "lieu", "a_venir", "cree_par", "created_at")
    list_display_links = ("titre",)

    # Filtres (colonne de droite) et recherche
    list_filter = ("date_evenement", "lieu")
    search_fields = ("titre", "description", "lieu")
    date_hierarchy = "date_evenement"
    ordering = ("date_evenement",)
    list_per_page = 20

    # Formulaire de création / modification
    fieldsets = (
        ("Informations", {"fields": ("titre", "description")}),
        ("Date et lieu", {"fields": ("date_evenement", "lieu")}),
        ("Suivi", {"fields": ("cree_par", "created_at", "updated_at")}),
    )
    readonly_fields = ("cree_par", "created_at", "updated_at")

    @admin.display(boolean=True, description="À venir")
    def a_venir(self, obj):
        return obj.est_a_venir

    def save_model(self, request, obj, form, change):
        # À la création, l'admin connecté est enregistré comme créateur
        if not change and obj.cree_par is None:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)