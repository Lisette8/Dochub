from django.contrib import admin

from .models import Rapport


@admin.register(Rapport)
class RapportAdmin(admin.ModelAdmin):
    list_display = ("titre", "date_debut", "date_fin", "statut", "archive", "created_at")
    list_filter = ("statut", "archive", "date_debut")
    search_fields = ("titre", "description", "note")
    
    def save_model(self, request, obj, form, change):
        if not obj.contenu:
            obj.contenu = obj.generer_contenu()
        super().save_model(request, obj, form, change)