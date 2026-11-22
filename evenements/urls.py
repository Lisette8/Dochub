from django.urls import path

from . import views

app_name = "evenements"

urlpatterns = [
    # Pages communes (tout utilisateur connecté)
    path("", views.liste, name="liste"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/inscription/", views.inscription, name="inscription"),
    path("<int:pk>/desinscription/", views.desinscription, name="desinscription"),

    # Administration (rôle Administrateur)
    path("gestion/", views.gestion, name="gestion"),
    path("gestion/creer/", views.creer, name="creer"),
    path("gestion/<int:pk>/modifier/", views.modifier, name="modifier"),
    path("gestion/<int:pk>/supprimer/", views.supprimer, name="supprimer"),
    path("gestion/participations/<int:pk>/presence/", views.presence, name="presence"),
]