from django.urls import path

from . import views

app_name = "actualites"

urlpatterns = [
    # Interface utilisateur
    path("", views.ActualiteListView.as_view(), name="liste"),
    path("<int:pk>/", views.ActualiteDetailView.as_view(), name="detail"),
    # Interface administrateur
    path("gestion/", views.GestionListView.as_view(), name="gestion_liste"),
    path("gestion/ajouter/", views.GestionCreateView.as_view(), name="gestion_ajouter"),
    path("gestion/<int:pk>/modifier/", views.GestionUpdateView.as_view(), name="gestion_modifier"),
    path("gestion/<int:pk>/supprimer/", views.GestionDeleteView.as_view(), name="gestion_supprimer"),
]