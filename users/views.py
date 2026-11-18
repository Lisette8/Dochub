from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import LoginForm
from .models import User
from .permissions import admin_required
from .serializers import UserSerializer


# ---------- Pages ----------

class LoginView(auth_views.LoginView):
    template_name = "users/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember_me"):
            # Sans « Se souvenir de moi », la session expire à la fermeture du navigateur.
            self.request.session.set_expiry(0)
        return response


class LogoutView(auth_views.LogoutView):
    pass


@login_required
def dashboard(request):
    context = {}
    if request.user.is_admin:
        users = User.objects.all()
        context["stats"] = {
            "users": users.count(),
            "admins": users.filter(role=User.Role.ADMIN).count(),
            "active": users.filter(is_active=True).count(),
            "inactive": users.filter(is_active=False).count(),
        }
    return render(request, "users/dashboard.html", context)


@admin_required
def admin_space(request):
    """Espace d'administration : point d'entrée des pages réservées à l'admin
    (gestion des comptes US-05 / US-22, puis les autres modules)."""
    return render(request, "users/admin_space.html")


# ---------- API ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """GET /api/auth/me/ : infos de l'utilisateur authentifié (JWT requis)."""
    return Response(UserSerializer(request.user).data)
