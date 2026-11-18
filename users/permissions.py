"""Permissions partagées par tous les modules DocHub (matrice des droits du CDC).

Pages Django (vues basées sur des classes) :
    class MaVue(AdminRequiredMixin, CreateView): ...      -> réservé à l'Administrateur
    class MaVue(LoginRequiredMixin, ListView): ...         -> tout utilisateur connecté

Pages Django (vues fonctions) :
    @admin_required
    def ma_vue(request): ...

API (Django REST Framework) :
    permission_classes = [IsAdmin]
    permission_classes = [IsAdminOrReadOnly]    -> lecture pour tous, écriture admin
    permission_classes = [IsOwnerOrAdmin]       -> objet à soi (ex. ses tickets) ou admin
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from rest_framework import permissions


def user_is_admin(user):
    return bool(user and user.is_authenticated and getattr(user, "is_admin", False))


# ---------- Pages Django ----------

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Non connecté -> page de connexion ; connecté sans rôle admin -> 403."""

    raise_exception = False

    def test_func(self):
        return user_is_admin(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Action réservée à l'Administrateur.")
        return super().handle_no_permission()


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not user_is_admin(request.user):
            raise PermissionDenied("Action réservée à l'Administrateur.")
        return view_func(request, *args, **kwargs)

    return wrapper


# ---------- API REST ----------

class IsAdmin(permissions.BasePermission):
    message = "Action réservée à l'Administrateur."

    def has_permission(self, request, view):
        return user_is_admin(request.user)


class IsAdminOrReadOnly(permissions.BasePermission):
    message = "Action réservée à l'Administrateur."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return user_is_admin(request.user)


class IsOwnerOrAdmin(permissions.BasePermission):
    """L'objet doit avoir un champ `owner_field` (par défaut « auteur »)
    pointant vers l'utilisateur. Une vue peut définir `owner_field = "createur"`."""

    message = "Vous n'avez accès qu'à vos propres éléments."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if user_is_admin(request.user):
            return True
        owner_field = getattr(view, "owner_field", "auteur")
        return getattr(obj, owner_field, None) == request.user
