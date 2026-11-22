from datetime import timedelta

from django.contrib import admin, messages
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Evenement, Participation, avec_nb_inscrits


class StatutEvenementFilter(admin.SimpleListFilter):
    """Filtre "À venir / Passés" dans la colonne de droite de l'admin."""

    title = "statut"
    parameter_name = "statut"

    def lookups(self, request, model_admin):
        return (
            ("a_venir", "À venir"),
            ("passes", "Passés"),
        )

    def queryset(self, request, queryset):
        maintenant = timezone.now()
        if self.value() == "a_venir":
            return queryset.filter(date_evenement__gte=maintenant)
        if self.value() == "passes":
            return queryset.filter(date_evenement__lt=maintenant)
        return queryset


class ParticipationInline(admin.TabularInline):
    """Liste des participants directement dans la fiche d'un événement."""

    model = Participation
    extra = 0
    fields = ("utilisateur", "date_inscription", "present")
    readonly_fields = ("date_inscription",)
    autocomplete_fields = ("utilisateur",)


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    # Colonnes affichées dans la liste (+ boutons Modifier / Supprimer)
    list_display = (
        "titre", "date_evenement", "lieu", "a_venir", "participants",
        "cree_par", "created_at", "boutons_actions",
    )
    list_display_links = ("titre",)

    # UPDATE rapide : date et lieu modifiables directement dans la liste
    # (bouton "Enregistrer" en bas de la liste)
    list_editable = ("date_evenement", "lieu")

    # Filtres (colonne de droite) et recherche
    list_filter = (StatutEvenementFilter, "date_evenement", "lieu")
    search_fields = ("titre", "description", "lieu")
    date_hierarchy = "date_evenement"
    ordering = ("date_evenement",)
    list_per_page = 20

    # Actions groupées (cases à cocher + menu "Action")
    actions = ["reporter_d_une_semaine", "supprimer_evenements_passes"]

    # Formulaire de création / modification
    fieldsets = (
        ("Informations", {"fields": ("titre", "description")}),
        ("Date et lieu", {"fields": ("date_evenement", "date_fin", "lieu")}),
        ("Inscriptions", {"fields": ("capacite",)}),
        ("Suivi", {"fields": ("cree_par", "created_at", "updated_at")}),
    )
    readonly_fields = ("cree_par", "created_at", "updated_at")

    # Boutons "Enregistrer" et "Supprimer" aussi en haut du formulaire
    save_on_top = True

    # Participants affichés en bas de la fiche de l'événement
    inlines = [ParticipationInline]

    def get_queryset(self, request):
        # Nombre d'inscrits calculé en une seule requête SQL (compatible Oracle)
        return avec_nb_inscrits(super().get_queryset(request))

    # ------------------------------------------------------------------
    # Colonnes calculées
    # ------------------------------------------------------------------
    @admin.display(boolean=True, description="À venir")
    def a_venir(self, obj):
        return obj.est_a_venir

    @admin.display(description="Participants", ordering="nb_inscrits")
    def participants(self, obj):
        if obj.capacite is None:
            return f"{obj.nb_inscrits} (illimité)"
        return f"{obj.nb_inscrits} / {obj.capacite}"

    @admin.display(description="Actions")
    def boutons_actions(self, obj):
        url_modifier = reverse("admin:evenements_evenement_change", args=[obj.pk])
        url_supprimer = reverse("admin:evenements_evenement_delete", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="margin-right:6px;">Modifier</a>'
            '<a class="button" href="{}" style="background:#ba2121;color:#fff;">Supprimer</a>',
            url_modifier,
            url_supprimer,
        )

    # ------------------------------------------------------------------
    # CREATE / UPDATE
    # ------------------------------------------------------------------
    def save_model(self, request, obj, form, change):
        # À la création, l'admin connecté est enregistré comme créateur
        if not change and obj.cree_par is None:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Reporter les événements sélectionnés d'une semaine")
    def reporter_d_une_semaine(self, request, queryset):
        nb = 0
        for evenement in queryset:
            evenement.date_evenement += timedelta(days=7)
            evenement.save(update_fields=["date_evenement", "updated_at"])
            nb += 1
        self.message_user(
            request,
            f"{nb} événement(s) reporté(s) d'une semaine.",
            messages.SUCCESS,
        )

    # ------------------------------------------------------------------
    # DELETE
    # (La suppression simple et l'action "Supprimer les événements
    #  sélectionnés" sont fournies par Django, avec page de confirmation.)
    # ------------------------------------------------------------------
    @admin.action(description="Supprimer les événements passés parmi la sélection")
    def supprimer_evenements_passes(self, request, queryset):
        passes = queryset.filter(date_evenement__lt=timezone.now())
        nb = passes.count()
        if nb == 0:
            self.message_user(
                request,
                "Aucun événement passé dans la sélection.",
                messages.WARNING,
            )
            return
        passes.delete()
        self.message_user(
            request,
            f"{nb} événement(s) passé(s) supprimé(s).",
            messages.SUCCESS,
        )


@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    """Gestion de toutes les inscriptions aux événements (US-28)."""

    list_display = ("utilisateur", "evenement", "date_inscription", "present")
    list_editable = ("present",)
    list_filter = ("present", "evenement", "date_inscription")
    search_fields = (
        "utilisateur__email", "utilisateur__first_name", "utilisateur__last_name",
        "evenement__titre",
    )
    autocomplete_fields = ("utilisateur", "evenement")
    readonly_fields = ("date_inscription",)
    date_hierarchy = "date_inscription"
    list_select_related = ("utilisateur", "evenement")
    list_per_page = 20

    