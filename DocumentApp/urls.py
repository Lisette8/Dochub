from django.urls import path
from . import views

app_name = "DocumentApp"

urlpatterns = [
    # Espace utilisateur (consultation des documents)
    path("", views.DocumentListView.as_view(), name="liste"),
    path("document-liste/", views.DocumentListView.as_view(), name="document_list"),
    path("<int:pk>/telecharger/", views.document_download, name="telecharger"),

    # Espace administrateur (gestion, dépôt, modification, suppression)
    path("gestion/", views.AdminDocumentListView.as_view(), name="gestion"),
    path("gestion/ajouter/", views.AdminDocumentCreateView.as_view(), name="gestion_ajouter"),
    path("gestion/<int:pk>/", views.AdminDocumentDetailView.as_view(), name="gestion_detail"),
    path("gestion/<int:pk>/modifier/", views.AdminDocumentUpdateView.as_view(), name="gestion_modifier"),
    path("gestion/<int:pk>/supprimer/", views.AdminDocumentDeleteView.as_view(), name="gestion_supprimer"),

    # Rétrocompatibilité avec les anciens liens et tests
    path("ajouter/", views.AdminDocumentCreateView.as_view(), name="ajouter"),
    path("document-create/", views.AdminDocumentCreateView.as_view(), name="document_create"),
    path("<int:pk>/", views.AdminDocumentDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.AdminDocumentUpdateView.as_view(), name="modifier"),
    path("<int:pk>/supprimer/", views.AdminDocumentDeleteView.as_view(), name="supprimer"),
]
