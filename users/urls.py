from django.urls import path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import account_views, views

app_name = "users"

urlpatterns = [
    # Pages
    path("", views.dashboard, name="dashboard"),
    path("connexion/", views.LoginView.as_view(), name="login"),
    path("deconnexion/", views.LogoutView.as_view(), name="logout"),
    path("inscription/", views.register, name="register"),
    path("activer/<uidb64>/<token>/", views.ActivateView.as_view(), name="activate"),
    # Gestion des comptes dans l'interface DocHub (administrateurs)
    path("utilisateurs/", account_views.user_list, name="user_list"),
    path("utilisateurs/ajouter/", account_views.user_create, name="user_create"),
    path("utilisateurs/supprimer/", account_views.users_delete, name="users_delete"),
    path("utilisateurs/<int:pk>/", account_views.user_update, name="user_update"),
    path("utilisateurs/<int:pk>/mot-de-passe/", account_views.user_password, name="user_password"),
    # La même gestion dans l'admin Django
    path("administration/", RedirectView.as_view(pattern_name="admin:users_user_changelist", permanent=False),
         name="admin_space"),
    # API JWT (US-06)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/me/", views.me, name="me"),
    # API comptes (US-05)
    path("api/users/", views.UserListCreateAPI.as_view(), name="api_users"),
]
