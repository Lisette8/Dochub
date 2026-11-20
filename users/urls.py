from django.urls import path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

app_name = "users"

urlpatterns = [
    # Pages
    path("", views.dashboard, name="dashboard"),
    path("connexion/", views.LoginView.as_view(), name="login"),
    path("deconnexion/", views.LogoutView.as_view(), name="logout"),
    path("inscription/", views.register, name="register"),
    path("activer/<uidb64>/<token>/", views.ActivateView.as_view(), name="activate"),
    # Ancienne page « Utilisateurs » : la gestion des comptes est dans l'admin Django.
    path("administration/", RedirectView.as_view(pattern_name="admin:users_user_changelist", permanent=False),
         name="admin_space"),
    # API JWT (US-06)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/me/", views.me, name="me"),
    # API comptes (US-05)
    path("api/users/", views.UserListCreateAPI.as_view(), name="api_users"),
]
