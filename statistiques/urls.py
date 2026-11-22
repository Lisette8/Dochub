from django.urls import path

from . import views

app_name = "statistiques"

urlpatterns = [
    # US-15 : Tableau de bord des compteurs globaux
    path("", views.compteurs, name="compteurs"),

    # US-33 : Liste des rapports et filtres
    path("rapports/", views.rapport_list, name="rapport_list"),

    # US-32 : Génération d'un rapport
    path("rapports/generer/", views.rapport_generer, name="rapport_generer"),

    # US-51 : Consultation et mise à jour statut/note
    path("rapports/<int:pk>/", views.rapport_detail, name="rapport_detail"),
    path("rapports/<int:pk>/modifier/", views.rapport_modifier, name="rapport_modifier"),
    path("rapports/<int:pk>/statut/", views.rapport_statut, name="rapport_statut"),

    # US-52 : Archiver / Supprimer
    path("rapports/<int:pk>/archiver/", views.rapport_archiver, name="rapport_archiver"),
    path("rapports/<int:pk>/supprimer/", views.rapport_supprimer, name="rapport_supprimer"),
]
