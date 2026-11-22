from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("", views.TicketListView.as_view(), name="liste"),
    path("nouveau/", views.TicketCreateView.as_view(), name="creer"),
    path("<int:pk>/", views.TicketDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.TicketUpdateView.as_view(), name="modifier"),
    path("<int:pk>/repondre/", views.TicketReplyView.as_view(), name="repondre"),
    path("gestion/", views.AdminTicketListView.as_view(), name="gestion"),
    path("gestion/<int:pk>/", views.AdminTicketDetailView.as_view(), name="gestion_detail"),
    path("gestion/<int:pk>/repondre/", views.AdminTicketReplyView.as_view(), name="gestion_repondre"),
]
