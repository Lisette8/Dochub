"""Gestion des comptes dans l'interface DocHub (mêmes possibilités que l'admin Django).

Pages réservées aux Administrateurs :
- liste : recherche, filtres (rôle, statut), tri, pagination, actions groupées ;
- ajout (US-05), modification, mot de passe, suppression avec confirmation.
Chaque modification est écrite dans l'historique de Django (LogEntry), commun avec /admin/.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.admin.utils import NestedObjects, construct_change_message
from django.contrib.auth import update_session_auth_hash
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import router, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from .account_actions import ACTION_LABELS, available_actions, exclude_self, run_account_action
from .account_forms import AccountCreateForm, AccountPasswordForm, AccountUpdateForm
from .models import User
from .permissions import admin_required
from .services import send_activation_email

# paramètre « tri » de l'URL -> champs de la base (seules ces valeurs sont acceptées)
TRIS = {
    "nom": ["last_name", "first_name"],
    "role": ["role"],
    "statut": ["statut"],
    "connexion": ["last_login"],
    "creation": ["date_joined"],
}
TRI_DEFAUT = "-creation"
Q_MAX = User._meta.get_field("email").max_length  # longueur maximale de la recherche
COLONNES = [("nom", "Utilisateur"), ("role", "Rôle"), ("statut", "Statut"),
            ("connexion", "Dernière connexion"), ("creation", "Créé le")]


def _log(request, compte, flag, form):
    message = construct_change_message(form, None, flag == ADDITION)
    LogEntry.objects.log_actions(request.user.pk, [compte], flag, message, single_object=True)


def _selected_users(request):
    """Comptes cochés (`comptes` = identifiants envoyés par le formulaire)."""
    ids = [int(v) for v in request.POST.getlist("comptes") if v.isdecimal() and len(v) < 19]
    return User.objects.filter(pk__in=ids)


# ---------- Liste ----------

def _list_params(request):
    """Paramètres de l'URL ; toute valeur inconnue est ignorée."""
    role, statut = request.GET.get("role", ""), request.GET.get("statut", "")
    tri = request.GET.get("tri", TRI_DEFAUT)
    return {
        "q": request.GET.get("q", "").replace("\x00", "").strip()[:Q_MAX],
        "role": role if role in User.Role.values else "",
        "statut": statut if statut in User.Statut.values else "",
        "tri": tri if tri.removeprefix("-") in TRIS else TRI_DEFAUT,
    }


def _filtered_users(params):
    users = User.objects.all()
    for word in params["q"].split():
        users = users.filter(Q(email__icontains=word) | Q(first_name__icontains=word) | Q(last_name__icontains=word))
    if params["role"]:
        users = users.filter(role=params["role"])
    if params["statut"]:
        users = users.filter(statut=params["statut"])
    prefix = "-" if params["tri"].startswith("-") else ""
    return users.order_by(*[prefix + f for f in TRIS[params["tri"].removeprefix("-")]], "pk")


@admin_required
def user_list(request):
    if request.method == "POST":
        return _bulk_action(request)
    params = _list_params(request)
    page = Paginator(_filtered_users(params), settings.COMPTES_PAR_PAGE).get_page(request.GET.get("page"))
    current, desc = params["tri"].removeprefix("-"), params["tri"].startswith("-")
    columns = [{
        "label": label,
        "tri": f"-{key}" if key == current and not desc else key,
        "arrow": ("↓" if desc else "↑") if key == current else "",
        "sort": ("descending" if desc else "ascending") if key == current else "none",
    } for key, label in COLONNES]
    return render(request, "users/user_list.html", {
        "page": page, "params": params, "columns": columns, "total": User.objects.count(),
        "q_max": Q_MAX, "filtered": bool(params["q"] or params["role"] or params["statut"]),
        "roles": User.Role.choices, "statuts": User.Statut.choices, "actions": ACTION_LABELS.items(),
    })


def _bulk_action(request):
    action = request.POST.get("action", "")
    selected = _selected_users(request)
    if not selected.exists():
        messages.warning(request, "Cochez au moins un compte.")
    elif action == "supprimer":
        return _confirm_delete(request, exclude_self(request, selected, "supprimer"))
    elif action in ACTION_LABELS:
        run_account_action(request, action, selected)
    else:
        messages.warning(request, "Choisissez une action.")
    return redirect(request.get_full_path())  # garde la recherche, les filtres et la page


# ---------- Ajouter ----------

@sensitive_post_parameters()
@admin_required
def user_create(request):
    form = AccountCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        compte = form.save()
        _log(request, compte, ADDITION, form)
        messages.success(request, f"Le compte de {compte.get_full_name()} a été créé.")
        if form.sends_activation_email:
            send_activation_email(request, compte)
            messages.info(request, f"Un e-mail d'activation a été envoyé à {compte.email}.")
        return redirect("users:user_list")
    return render(request, "users/user_form.html", {"form": form})


# ---------- Modifier ----------

@admin_required
def user_update(request, pk):
    compte = get_object_or_404(User, pk=pk)
    if request.method == "POST" and "action" in request.POST:
        # Boutons rapides de la page (suspendre, bloquer, renvoyer l'e-mail...)
        if request.POST["action"] in ACTION_LABELS:
            run_account_action(request, request.POST["action"], User.objects.filter(pk=pk))
        return redirect("users:user_update", pk=pk)
    form = AccountUpdateForm(request.POST or None, instance=compte, acting_user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        if form.has_changed():
            _log(request, compte, CHANGE, form)
        messages.success(request, f"Le compte de {compte.get_full_name()} a été modifié.")
        return redirect("users:user_list")
    historique = LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(User), object_id=str(pk),
    ).select_related("user").order_by("-action_time")[:settings.HISTORIQUE_TAILLE]
    saved = User.objects.get(pk=pk)  # relu en base : le formulaire a pu copier des valeurs refusées dans `compte`
    return render(request, "users/user_form.html", {
        "form": form,
        "compte": saved,
        "actions": available_actions(saved, request.user),
        "historique": historique,
        "is_self": pk == request.user.pk,
    })


@sensitive_post_parameters()
@admin_required
def user_password(request, pk):
    compte = get_object_or_404(User, pk=pk)
    form = AccountPasswordForm(compte, request.POST or None, acting_user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        _log(request, compte, CHANGE, form)
        if form.removes_password:
            send_activation_email(request, compte)
            messages.success(request, f"Mot de passe retiré. Un e-mail d'activation a été envoyé à {compte.email}.")
        else:
            messages.success(request, f"Le mot de passe de {compte.get_full_name()} a été modifié.")
        if pk == request.user.pk:
            update_session_auth_hash(request, compte)  # l'admin reste connecté
        return redirect("users:user_update", pk=pk)
    return render(request, "users/user_password.html", {"form": form, "compte": compte})


# ---------- Supprimer ----------

def _collect(comptes):
    """Comptes et éléments liés qui seraient supprimés avec eux (tickets, documents...)."""
    collector = NestedObjects(using=router.db_for_write(User))
    collector.collect(comptes)
    return collector


def _confirm_delete(request, comptes):
    if not comptes:
        return redirect("users:user_list")
    collector = _collect(comptes)
    related = [(model._meta.verbose_name_plural, len(objs)) for model, objs in collector.model_objs.items()
               if model is not User and not model._meta.auto_created]
    return render(request, "users/user_confirm_delete.html", {
        "comptes": comptes, "related": related, "protected": collector.protected,
    })


@require_POST
@admin_required
def users_delete(request):
    """1er envoi : page de confirmation. 2e envoi (confirmer=oui) : suppression."""
    selected = _selected_users(request)
    if not selected.exists():
        messages.warning(request, "Aucun compte à supprimer.")
        return redirect("users:user_list")
    comptes = exclude_self(request, selected, "supprimer")
    if request.POST.get("confirmer") != "oui" or _collect(comptes).protected:
        return _confirm_delete(request, comptes)
    deleted = list(comptes)
    if deleted:
        with transaction.atomic():
            LogEntry.objects.log_actions(request.user.pk, deleted, DELETION)
            comptes.delete()
        messages.success(request, f"{len(deleted)} compte(s) supprimé(s).")
    return redirect("users:user_list")
