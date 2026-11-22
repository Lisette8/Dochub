from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("support/", include("support.urls")),
    path("", include("users.urls")),
    path("statistiques/", include("statistiques.urls")),
    path("actualites/", include("actualites.urls")),
]
