"""Pages "Événements" de l'interface DocHub.

Partie commune (tout utilisateur connecté) :
- liste          : calendrier du mois (vue "Mois", par défaut) ou liste complète
                   (vue "Liste"), avec le panneau "À venir" à droite (US-13).
- detail         : fiche complète d'un événement (US-13).
- inscription    : inscription d'un Utilisateur à un événement (US-28).
- desinscription : annulation de son inscription (US-28).

Partie administration (rôle Administrateur uniquement) :
- gestion        : tableau de tous les événements, avec statistiques (US-12).
- creer          : création d'un événement (US-12).
- modifier       : modification d'un événement (US-12).
- supprimer      : suppression d'un événement, avec confirmation (US-12).
- presence       : marquer un participant présent / absent.

L'administrateur organise les événements : il ne peut pas s'y inscrire,
mais il voit le nombre et le détail des participants de chaque événement.
"""

import calendar
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from users.permissions import admin_required

from .forms import EvenementForm
from .models import Evenement, Participation, avec_nb_inscrits

NB_PAR_JOUR = 2          # étiquettes affichées par case du calendrier
NB_AUTRES = 3            # "Autres événements à venir" sur la page détail

NOMS_MOIS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]
JOURS_SEMAINE = ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"]

FILTRES = {
    "tous": "Tous",
    "a_venir": "À venir",
    "passes": "Passés",
}

MSG_ADMIN_INSCRIPTION = (
    "En tant qu'administrateur, vous organisez les événements : "
    "vous ne pouvez pas vous y inscrire."
)


# ----------------------------------------------------------------------
# Outils
# ----------------------------------------------------------------------
def _evenements():
    """Événements avec leur nombre d'inscrits, calculé en une seule requête SQL."""
    return avec_nb_inscrits(Evenement.objects.all())


def _ids_inscrits(user):
    """Identifiants des événements auxquels l'utilisateur est inscrit (une requête)."""
    return set(
        Participation.objects.filter(utilisateur=user).values_list("evenement_id", flat=True)
    )


def _participants(evenement):
    """Inscrits d'un événement, avec leur compte utilisateur (une requête)."""
    return evenement.participations.select_related("utilisateur").order_by("date_inscription")


def _mois_demande(request):
    """Lit ?mois=AAAA-MM ; renvoie (année, mois). Valeur absente ou invalide : mois courant."""
    aujourd_hui = timezone.localdate()
    valeur = request.GET.get("mois", "")
    try:
        annee, mois = (int(x) for x in valeur.split("-"))
        if 1900 <= annee <= 2100 and 1 <= mois <= 12:
            return annee, mois
    except ValueError:
        pass
    return aujourd_hui.year, aujourd_hui.month


def _decaler_mois(annee, mois, delta):
    """Ajoute delta mois (positif ou négatif) à (année, mois)."""
    index = annee * 12 + (mois - 1) + delta
    return index // 12, index % 12 + 1


def _debut_mois(annee, mois):
    """Premier jour du mois à 00:00, dans le fuseau du projet (Africa/Tunis)."""
    return timezone.make_aware(datetime(annee, mois, 1))


def _construire_calendrier(annee, mois, evenements):
    """Semaines du mois (lundi -> dimanche) avec les événements de chaque jour."""
    par_jour = {}
    for evt in evenements:
        jour = timezone.localtime(evt.date_evenement).date()
        par_jour.setdefault(jour, []).append(evt)

    aujourd_hui = timezone.localdate()
    semaines = []
    for semaine in calendar.Calendar(firstweekday=0).monthdatescalendar(annee, mois):
        jours = []
        for index, jour in enumerate(semaine):
            evts_du_jour = par_jour.get(jour, []) if jour.month == mois else []
            jours.append({
                "date": jour,
                "dans_le_mois": jour.month == mois,
                "aujourd_hui": jour == aujourd_hui,
                "fin_de_semaine": index >= 5,       # SAM / DIM : aperçu ouvert vers la gauche
                "evenements": evts_du_jour[:NB_PAR_JOUR],
                "en_plus": max(len(evts_du_jour) - NB_PAR_JOUR, 0),
            })
        semaines.append(jours)
    return semaines


def _url_retour(request, defaut):
    """Page où revenir après une action : le champ "next" s'il est sûr, sinon `defaut`."""
    suivant = request.POST.get("next") or request.GET.get("next") or ""
    if suivant and url_has_allowed_host_and_scheme(
        suivant, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return suivant
    return defaut


# ----------------------------------------------------------------------
# Pages communes
# ----------------------------------------------------------------------
@login_required
def liste(request):
    maintenant = timezone.now()
    vue = "liste" if request.GET.get("vue") == "liste" else "mois"
    annee, mois = _mois_demande(request)
    aujourd_hui = timezone.localdate()

    # Paramètres de la page sans "participants" : sert à construire les liens
    # "Voir les participants" en gardant le mois / la vue / le filtre affichés.
    params = request.GET.copy()
    params.pop("participants", None)
    base_query = params.urlencode()

    context = {
        "vue": vue,
        "mois_param": "%04d-%02d" % (annee, mois),
        "mois_titre": f"{NOMS_MOIS[mois - 1]} {annee}",
        "mois_precedent": "%04d-%02d" % _decaler_mois(annee, mois, -1),
        "mois_suivant": "%04d-%02d" % _decaler_mois(annee, mois, 1),
        "est_mois_courant": (annee, mois) == (aujourd_hui.year, aujourd_hui.month),
        # Panneau de droite : TOUS les événements à venir (défilement dans le panneau)
        "a_venir": _evenements().filter(date_evenement__gte=maintenant),
        "inscrits": set() if request.user.is_admin else _ids_inscrits(request.user),
        "page_courante": request.get_full_path(),
        "base_query": base_query,
        "selection": None,
    }

    # Administrateur : participants de l'événement choisi (?participants=<id>)
    if request.user.is_admin:
        try:
            id_selection = int(request.GET.get("participants", ""))
        except ValueError:
            id_selection = None
        if id_selection:
            selection = _evenements().filter(pk=id_selection).first()
            if selection:
                context["selection"] = selection
                context["participants"] = _participants(selection)

    if vue == "mois":
        debut = _debut_mois(annee, mois)
        fin = _debut_mois(*_decaler_mois(annee, mois, 1))
        evenements_du_mois = list(
            _evenements().filter(date_evenement__gte=debut, date_evenement__lt=fin)
        )
        context.update({
            "jours_semaine": JOURS_SEMAINE,
            "semaines": _construire_calendrier(annee, mois, evenements_du_mois),
            "nb_evenements_mois": len(evenements_du_mois),
        })
    else:
        filtre = request.GET.get("filtre", "tous")
        if filtre not in FILTRES:
            filtre = "tous"

        tous = _evenements()
        if filtre == "a_venir":
            qs = tous.filter(date_evenement__gte=maintenant)
        elif filtre == "passes":
            qs = tous.filter(date_evenement__lt=maintenant).order_by("-date_evenement")
        else:
            qs = tous

        nb_a_venir = Evenement.objects.filter(date_evenement__gte=maintenant).count()
        nb_total = Evenement.objects.count()
        context.update({
            "filtre": filtre,
            "filtres": [
                {"code": "tous", "libelle": FILTRES["tous"], "nombre": nb_total},
                {"code": "a_venir", "libelle": FILTRES["a_venir"], "nombre": nb_a_venir},
                {"code": "passes", "libelle": FILTRES["passes"], "nombre": nb_total - nb_a_venir},
            ],
            # Tous les événements : la liste défile dans la carte (plus de pagination)
            "evenements": qs,
        })

    return render(request, "evenements/liste.html", context)


@login_required
def detail(request, pk):
    evenement = get_object_or_404(_evenements().select_related("cree_par"), pk=pk)
    autres_a_venir = (
        _evenements()
        .filter(date_evenement__gte=timezone.now())
        .exclude(pk=evenement.pk)[:NB_AUTRES]
    )
    est_admin = request.user.is_admin
    return render(request, "evenements/detail.html", {
        "evenement": evenement,
        "autres_a_venir": autres_a_venir,
        "inscrits": set() if est_admin else _ids_inscrits(request.user),
        "participants": _participants(evenement) if est_admin else None,
        "mois_param": timezone.localtime(evenement.date_evenement).strftime("%Y-%m"),
        "page_courante": request.get_full_path(),
    })


# ----------------------------------------------------------------------
# Inscriptions (Utilisateur uniquement, POST uniquement)
# ----------------------------------------------------------------------
@require_POST
def inscription(request, pk):
    """Inscrit l'utilisateur connecté à l'événement (US-28)."""
    if not request.user.is_authenticated:
        return redirect_to_login(reverse("evenements:detail", args=[pk]))

    retour = _url_retour(request, reverse("evenements:detail", args=[pk]))

    # L'administrateur organise : il ne s'inscrit pas (règle vérifiée côté serveur)
    if request.user.is_admin:
        messages.error(request, MSG_ADMIN_INSCRIPTION)
        return redirect(retour)

    with transaction.atomic():
        # Verrou sur la ligne de l'événement : deux inscriptions simultanées
        # ne peuvent pas dépasser la capacité.
        evenement = get_object_or_404(Evenement.objects.select_for_update(), pk=pk)

        if not evenement.est_a_venir:
            messages.error(request, "Impossible de s'inscrire : cet événement a déjà commencé.")
            return redirect(retour)

        if Participation.objects.filter(evenement=evenement, utilisateur=request.user).exists():
            messages.error(request, "Vous êtes déjà inscrit à cet événement.")
            return redirect(retour)

        if evenement.capacite is not None and evenement.participations.count() >= evenement.capacite:
            messages.error(request, "Désolé, cet événement est complet.")
            return redirect(retour)

        try:
            with transaction.atomic():
                Participation.objects.create(evenement=evenement, utilisateur=request.user)
        except IntegrityError:
            messages.error(request, "Vous êtes déjà inscrit à cet événement.")
            return redirect(retour)

    messages.success(request, f"Inscription confirmée à « {evenement.titre} ».")
    return redirect(retour)


@require_POST
def desinscription(request, pk):
    """Annule l'inscription de l'utilisateur connecté (US-28)."""
    if not request.user.is_authenticated:
        return redirect_to_login(reverse("evenements:detail", args=[pk]))

    evenement = get_object_or_404(Evenement, pk=pk)
    retour = _url_retour(request, reverse("evenements:detail", args=[evenement.pk]))

    if not evenement.est_a_venir:
        messages.error(request, "Impossible d'annuler : cet événement a déjà commencé.")
        return redirect(retour)

    supprimees, _ = Participation.objects.filter(
        evenement=evenement, utilisateur=request.user
    ).delete()
    if supprimees:
        messages.success(request, f"Votre inscription à « {evenement.titre} » a été annulée.")
    else:
        messages.error(request, "Vous n'étiez pas inscrit à cet événement.")
    return redirect(retour)


# ----------------------------------------------------------------------
# Administration (rôle Administrateur uniquement)
# ----------------------------------------------------------------------
@admin_required
def gestion(request):
    """Tableau de tous les événements avec leurs participants (CRUD : lecture)."""
    maintenant = timezone.now()
    filtre = request.GET.get("filtre", "tous")
    if filtre not in FILTRES:
        filtre = "tous"
    recherche = request.GET.get("q", "").strip()

    tous = _evenements()
    qs = tous
    if filtre == "a_venir":
        qs = qs.filter(date_evenement__gte=maintenant)
    elif filtre == "passes":
        qs = qs.filter(date_evenement__lt=maintenant).order_by("-date_evenement")
    if recherche:
        qs = qs.filter(Q(titre__icontains=recherche) | Q(lieu__icontains=recherche))

    evenements = list(qs)
    nb_total = Evenement.objects.count()
    nb_a_venir = Evenement.objects.filter(date_evenement__gte=maintenant).count()
    a_venir = list(tous.filter(date_evenement__gte=maintenant))

    return render(request, "evenements/gestion.html", {
        "evenements": evenements,
        "filtre": filtre,
        "recherche": recherche,
        "filtres": [
            {"code": "tous", "libelle": FILTRES["tous"], "nombre": nb_total},
            {"code": "a_venir", "libelle": FILTRES["a_venir"], "nombre": nb_a_venir},
            {"code": "passes", "libelle": FILTRES["passes"], "nombre": nb_total - nb_a_venir},
        ],
        "stats": {
            "total": nb_total,
            "a_venir": nb_a_venir,
            "inscriptions": Participation.objects.count(),
            "complets": sum(1 for e in a_venir if e.est_complet),
        },
        "page_courante": request.get_full_path(),
    })


@admin_required
def creer(request):
    """Création d'un événement depuis l'interface DocHub."""
    form = EvenementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        evenement = form.save(commit=False)
        evenement.cree_par = request.user
        evenement.save()
        messages.success(request, f"L'événement « {evenement.titre} » a été créé.")
        return redirect("evenements:detail", pk=evenement.pk)
    return render(request, "evenements/formulaire.html", {
        "form": form,
        "evenement": None,
        "maintenant": timezone.now(),
    })


@admin_required
def modifier(request, pk):
    """Modification d'un événement existant."""
    evenement = get_object_or_404(_evenements().select_related("cree_par"), pk=pk)
    form = EvenementForm(request.POST or None, instance=evenement)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"L'événement « {evenement.titre} » a été modifié.")
        return redirect("evenements:detail", pk=evenement.pk)
    return render(request, "evenements/formulaire.html", {
        "form": form,
        "evenement": evenement,
        "maintenant": timezone.now(),
    })


@admin_required
def supprimer(request, pk):
    """Suppression d'un événement : page de confirmation (GET), puis suppression (POST)."""
    evenement = get_object_or_404(_evenements(), pk=pk)
    if request.method == "POST":
        titre = evenement.titre
        evenement.delete()   # les participations sont supprimées avec (CASCADE)
        messages.success(request, f"L'événement « {titre} » a été supprimé.")
        return redirect("evenements:gestion")
    return render(request, "evenements/supprimer.html", {"evenement": evenement})


@admin_required
@require_POST
def presence(request, pk):
    """Marque un participant présent ou absent (bascule)."""
    participation = get_object_or_404(
        Participation.objects.select_related("utilisateur", "evenement"), pk=pk
    )
    participation.present = not participation.present
    participation.save(update_fields=["present"])
    nom = participation.utilisateur.get_full_name() or participation.utilisateur.email
    etat = "présent" if participation.present else "absent"
    messages.success(request, f"{nom} est marqué {etat}.")
    return redirect(_url_retour(
        request, reverse("evenements:detail", args=[participation.evenement_id])
    ))

