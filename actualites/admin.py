from django.contrib import admin

from .models import Actualite


@admin.register(Actualite)
class ActualiteAdmin(admin.ModelAdmin):
    list_display = ("titre", "categorie", "statut", "epinglee", "created_at")
    list_filter = ("statut", "categorie", "epinglee")
    search_fields = ("titre", "description")
    list_editable = ("statut", "epinglee")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"