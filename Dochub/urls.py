from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("documents/", include("DocumentApp.urls")),
    path("evenements/", include("evenements.urls")),
    path("support/", include("support.urls")),
    path("statistiques/", include("statistiques.urls")),
    path("actualites/", include("actualites.urls")),
    path("", include("users.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

