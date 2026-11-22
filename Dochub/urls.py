from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("documents/", include("DocumentApp.urls")),
    path("support/", include("support.urls")),
    path("", include("users.urls")),
    path("statistiques/", include("statistiques.urls")),
]
