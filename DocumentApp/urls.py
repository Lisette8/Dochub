from django.urls import path

from . import views

app_name = "DocumentApp"

urlpatterns = [
    path("", views.DocumentListView.as_view(), name="liste"),
    path("", views.DocumentListView.as_view(), name="document_list"),
    path("ajouter/", views.DocumentCreateView.as_view(), name="ajouter"),
    path("ajouter/", views.DocumentCreateView.as_view(), name="document_create"),
    path("<int:idDocument>/", views.DocumentDetailView.as_view(), name="detail"),
    path("<int:idDocument>/", views.DocumentDetailView.as_view(), name="document_detail"),
    path("<int:idDocument>/modifier/", views.DocumentUpdateView.as_view(), name="modifier"),
    path("<int:idDocument>/modifier/", views.DocumentUpdateView.as_view(), name="document_update"),
    path("<int:idDocument>/supprimer/", views.DocumentDeleteView.as_view(), name="supprimer"),
    path("<int:idDocument>/supprimer/", views.DocumentDeleteView.as_view(), name="document_delete"),
]