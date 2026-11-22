from functools import wraps

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import RapportFiltreForm, RapportGenererForm, RapportModifierForm, RapportStatutForm
from .models import Rapport


def admin_required(view_func):
    """Vérifie que l'utilisateur est authentifié et administrateur DocHub."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not getattr(request.user, "is_admin", False):
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect("users:dashboard")
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_model_safely(app_label, model_name):
    """Charge un modèle de manière différée (lazy) sans crash si l'app n'existe pas encore."""
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


@admin_required
def compteurs(request):
    """US-15 : Tableau de bord avec compteurs globaux."""
    User = get_user_model()
    nb_users = User.objects.count()
    nb_admins = User.objects.filter(role="ADMIN").count()

    # Documents
    DocModel = _get_model_safely("documents", "Document")
    nb_documents = DocModel.objects.count() if DocModel else 0

    # Actualités
    ActuModel = _get_model_safely("actualites", "Actualite")
    nb_actualites = ActuModel.objects.count() if ActuModel else 0

    # Événements
    EventModel = _get_model_safely("evenements", "Evenement")
    nb_evenements = EventModel.objects.count() if EventModel else 0

    # Tickets ouverts (app 'tickets' ou 'support')
    TicketModel = _get_model_safely("tickets", "Ticket") or _get_model_safely("support", "Ticket")
    if TicketModel and hasattr(TicketModel, "statut"):
        nb_tickets_ouverts = TicketModel.objects.filter(statut="OUVERT").count()
    elif TicketModel:
        nb_tickets_ouverts = TicketModel.objects.count()
    else:
        nb_tickets_ouverts = 0

    stats = {
        "utilisateurs": nb_users,
        "admins": nb_admins,
        "documents": nb_documents,
        "actualites": nb_actualites,
        "evenements": nb_evenements,
        "tickets_ouverts": nb_tickets_ouverts,
    }

    # Derniers rapports générés pour aperçu rapide
    derniers_rapports = Rapport.objects.filter(archive=False)[:5]

    return render(request, "statistiques/compteurs.html", {
        "stats": stats,
        "derniers_rapports": derniers_rapports,
    })


@admin_required
def rapport_list(request):
    """US-33 : Liste des rapports générés avec filtres par statut, date et archivage."""
    filtre_form = RapportFiltreForm(request.GET or None)
    qs = Rapport.objects.all()

    if request.GET and filtre_form.is_valid():
        statut = filtre_form.cleaned_data.get("statut")
        if statut:
            qs = qs.filter(statut=statut)

        archive = filtre_form.cleaned_data.get("archive")
        if archive == "1":
            qs = qs.filter(archive=True)
        elif archive == "0":
            qs = qs.filter(archive=False)
        # Si archive == "all" : on ne filtre pas, on affiche actifs ET archivés !
    else:
        # Par défaut au chargement initial : uniquement les rapports actifs
        qs = qs.filter(archive=False)

    paginator = Paginator(qs, 10)  # 10 rapports par page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "statistiques/rapport_list.html", {
        "page_obj": page_obj,
        "filtre_form": filtre_form,
        "total_rapports": qs.count(),
    })


@admin_required
def rapport_generer(request):
    """US-32 : Générer un nouveau rapport sur une période choisie."""
    if request.method == "POST":
        form = RapportGenererForm(request.POST)
        if form.is_valid():
            rapport = form.save(commit=False)
            if not rapport.statut:
                rapport.statut = Rapport.Statut.NOUVEAU
            rapport.contenu = rapport.generer_contenu()
            rapport.save()
            messages.success(request, f"Le rapport « {rapport.titre} » a été généré avec succès.")
            return redirect("statistiques:rapport_detail", pk=rapport.pk)
    else:
        form = RapportGenererForm()

    return render(request, "statistiques/rapport_generer.html", {
        "form": form,
    })


@admin_required
def rapport_detail(request, pk):
    """US-51 : Consultation détaillée du rapport en lecture seule."""
    rapport = get_object_or_404(Rapport, pk=pk)
    return render(request, "statistiques/rapport_detail.html", {
        "rapport": rapport,
    })


@admin_required
def rapport_modifier(request, pk):
    """Modifier l'ensemble des informations d'un rapport existant (titre, dates, format, statut, note)."""
    rapport = get_object_or_404(Rapport, pk=pk)
    ancienne_date_debut = rapport.date_debut
    ancienne_date_fin = rapport.date_fin

    if request.method == "POST":
        form = RapportModifierForm(request.POST, instance=rapport)
        if form.is_valid():
            rapport = form.save(commit=False)
            # Si les dates ont été modifiées, recalculer automatiquement la synthèse
            if rapport.date_debut != ancienne_date_debut or rapport.date_fin != ancienne_date_fin:
                rapport.contenu = rapport.generer_contenu()
            rapport.save()
            messages.success(request, f"Le rapport « {rapport.titre} » a été mis à jour avec succès.")
            return redirect("statistiques:rapport_list")
    else:
        form = RapportModifierForm(instance=rapport)

    return render(request, "statistiques/rapport_modifier.html", {
        "form": form,
        "rapport": rapport,
    })


@admin_required
@require_POST
def rapport_statut(request, pk):
    """US-51 : Traitement rapide du changement de statut et note."""
    rapport = get_object_or_404(Rapport, pk=pk)
    form = RapportStatutForm(request.POST, instance=rapport)
    if form.is_valid():
        form.save()
        messages.success(request, f"Statut et note du rapport « {rapport.titre} » mis à jour.")
    else:
        messages.error(request, "Erreur lors de la mise à jour du statut.")
    return redirect("statistiques:rapport_list")


@admin_required
@require_POST
def rapport_archiver(request, pk):
    """US-52 (optionnel) : Archiver ou désarchiver un rapport."""
    rapport = get_object_or_404(Rapport, pk=pk)
    rapport.archive = not rapport.archive
    rapport.save(update_fields=["archive"])
    etat = "archivé" if rapport.archive else "restauré"
    messages.success(request, f"Le rapport « {rapport.titre} » a été {etat}.")
    return redirect("statistiques:rapport_list")


@admin_required
def rapport_supprimer(request, pk):
    """US-52 (optionnel) : Suppression définitive d'un rapport avec page de confirmation."""
    rapport = get_object_or_404(Rapport, pk=pk)
    if request.method == "POST":
        titre = rapport.titre
        rapport.delete()
        messages.success(request, f"Le rapport « {titre} » a été supprimé définitivement.")
        return redirect("statistiques:rapport_list")

    return render(request, "statistiques/rapport_supprimer.html", {
        "rapport": rapport,
    })
