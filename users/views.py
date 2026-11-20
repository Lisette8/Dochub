from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import ActivationForm, LoginForm, RegisterForm
from .models import User
from .permissions import IsAdmin
from .serializers import AdminCreateUserSerializer, UserSerializer
from .services import create_account_by_admin


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


def register(request):
    """Inscription : un visiteur crée son propre compte (rôle Utilisateur uniquement)."""
    if request.user.is_authenticated:
        return redirect("users:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="users.backends.StatutBackend")
        request.session.set_expiry(0)
        messages.success(request, "Bienvenue sur DocHub, votre compte a été créé.")
        return redirect("users:dashboard")
    return render(request, "users/register.html", {"form": form})


class ActivateView(auth_views.PasswordResetConfirmView):
    """Lien reçu par e-mail après la création du compte par l'admin (US-05) :
    l'utilisateur choisit son mot de passe. Le lien n'est valable qu'une fois."""

    template_name = "users/activate.html"
    form_class = ActivationForm
    success_url = reverse_lazy("users:login")
    reset_url_token = "definir-mot-de-passe"

    def form_valid(self, form):
        messages.success(self.request, "Mot de passe enregistré. Vous pouvez maintenant vous connecter.")
        return super().form_valid(form)


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


# ---------- API ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """GET /api/auth/me/ : infos de l'utilisateur authentifié (JWT requis)."""
    return Response(UserSerializer(request.user).data)


class UserListCreateAPI(generics.ListCreateAPIView):
    """GET /api/users/ : liste des comptes ; POST : US-05 création d'un compte avec rôle.
    Réservé à l'administrateur (JWT requis)."""

    permission_classes = [IsAdmin]
    queryset = User.objects.order_by("-date_joined")

    def get_serializer_class(self):
        return AdminCreateUserSerializer if self.request.method == "POST" else UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = AdminCreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = create_account_by_admin(request, **serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
