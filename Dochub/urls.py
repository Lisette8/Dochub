from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    path("evenements/", include("evenements.urls")),
    path("", include("users.urls")),
]

    path("support/", include("support.urls")),
    path("", include("users.urls")),
    path("statistiques/", include("statistiques.urls")),
]

