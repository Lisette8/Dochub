from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import AdminDocumentForm, DocumentForm
from .models import Document

# Champs minimaux garantis d'exister même sur une table non encore migrée
LEGACY_FIELDS = ("idDocument", "titreDocument", "descDocument", "created_at", "updated_at")


def _is_missing_column_error(e):
    err = str(e).upper()
    return "ORA-00904" in err or "AUTEUR_ID" in err or "NO SUCH COLUMN" in err


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Vérifie que l'utilisateur est authentifié et administrateur DocHub."""
    def test_func(self):
        user = self.request.user
        return getattr(user, "is_admin", False) or user.is_staff or user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Accès réservé aux administrateurs.")
            return redirect("DocumentApp:liste")
        return super().handle_no_permission()


# ==============================================================================
# Interface Administrateur DocHub (Gestion, Dépôt, Modification, Suppression)
# ==============================================================================

class AdminDocumentListView(AdminRequiredMixin, ListView):
    """Liste d'administration avec recherche multi-mots, filtrage par type et thématique."""
    model = Document
    template_name = "DocumentApp/gestion_liste.html"
    context_object_name = "documents"
    paginate_by = 10

    def get_queryset(self):
        qs = Document.objects.all()

        # Vérification préventive pour Oracle : si les nouvelles colonnes ne sont pas encore migrées
        try:
            list(qs[:1])
            is_migrated = True
        except Exception as e:
            if _is_missing_column_error(e):
                qs = Document.objects.only(*LEGACY_FIELDS)
                is_migrated = False
            else:
                raise

        q = self.request.GET.get("q", "").strip()
        type_doc = self.request.GET.get("type", "").strip()
        thematique = self.request.GET.get("thematique", "").strip()

        if q:
            for word in q.split():
                if is_migrated:
                    qs = qs.filter(
                        Q(titreDocument__icontains=word)
                        | Q(descDocument__icontains=word)
                        | Q(fichier__icontains=word)
                    )
                else:
                    qs = qs.filter(
                        Q(titreDocument__icontains=word)
                        | Q(descDocument__icontains=word)
                    )

        if is_migrated:
            if type_doc and type_doc in Document.TypeDocument.values:
                qs = qs.filter(type_document=type_doc)
            if thematique and thematique in Document.Thematique.values:
                qs = qs.filter(thematique=thematique)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = {
            "q": self.request.GET.get("q", "").strip(),
            "type": self.request.GET.get("type", "").strip(),
            "thematique": self.request.GET.get("thematique", "").strip(),
        }
        context["params"] = params
        context["types"] = Document.TypeDocument.choices
        context["thematiques"] = Document.Thematique.choices
        context["total"] = context["paginator"].count
        context["filtered"] = bool(params["q"] or params["type"] or params["thematique"])
        return context


class AdminDocumentCreateView(AdminRequiredMixin, CreateView):
    """Dépôt d'un document (PDF, Markdown, texte) avec métadonnées complètes."""
    model = Document
    form_class = AdminDocumentForm
    template_name = "DocumentApp/gestion_form.html"

    def form_valid(self, form):
        try:
            form.instance.auteur = self.request.user
        except Exception:
            pass
        response = super().form_valid(form)
        messages.success(self.request, f"Le document « {self.object.titreDocument} » a été déposé avec succès.")
        return response

    def get_success_url(self):
        return reverse("DocumentApp:gestion")


class AdminDocumentUpdateView(AdminRequiredMixin, UpdateView):
    """Modification des métadonnées d'un document existant."""
    model = Document
    form_class = AdminDocumentForm
    template_name = "DocumentApp/gestion_form.html"
    pk_url_kwarg = "pk"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Les métadonnées du document « {self.object.titreDocument} » ont été modifiées.")
        return response

    def get_success_url(self):
        return reverse("DocumentApp:gestion")


class AdminDocumentDetailView(AdminRequiredMixin, DetailView):
    """Fiche détaillée d'un document avec prévisualisation et actions admin."""
    model = Document
    template_name = "DocumentApp/gestion_detail.html"
    context_object_name = "document"
    pk_url_kwarg = "pk"


class AdminDocumentDeleteView(AdminRequiredMixin, DeleteView):
    """Suppression sécurisée d'un document avec page de confirmation."""
    model = Document
    pk_url_kwarg = "pk"
    template_name = "DocumentApp/gestion_confirm_delete.html"
    success_url = reverse_lazy("DocumentApp:gestion")

    def post(self, request, *args, **kwargs):
        doc = self.get_object()
        titre = doc.titreDocument
        response = super().post(request, *args, **kwargs)
        messages.success(request, f"Le document « {titre} » a été supprimé.")
        return response

@login_required
def document_download(request, pk):
    """Téléchargement direct et sécurisé du fichier document."""
    doc = get_object_or_404(Document, pk=pk)
    fichier = getattr(doc, "fichier", None)
    if not fichier:
        raise Http404("Aucun fichier attaché à ce document.")
    try:
        return FileResponse(fichier.open(), as_attachment=True, filename=doc.nom_fichier)
    except Exception:
        raise Http404("Le fichier demandé est introuvable sur le serveur.")


# ==============================================================================
# Interface Utilisateur / Rétro-compatibilité
# ==============================================================================

class DocumentListView(LoginRequiredMixin, ListView):
    """Vue publique/utilisateur de la liste des documents avec filtres."""
    model = Document
    template_name = "DocumentApp/liste_documents.html"
    context_object_name = "documents"
    paginate_by = 12

    def get_queryset(self):
        qs = Document.objects.all()

        # Vérification préventive pour Oracle : si les nouvelles colonnes ne sont pas encore migrées
        try:
            list(qs[:1])
            is_migrated = True
        except Exception as e:
            if _is_missing_column_error(e):
                qs = Document.objects.only(*LEGACY_FIELDS)
                is_migrated = False
            else:
                raise

        q = self.request.GET.get("q", "").strip()
        type_doc = self.request.GET.get("type", "").strip()
        thematique = self.request.GET.get("thematique", "").strip()

        if q:
            for word in q.split():
                if is_migrated:
                    qs = qs.filter(
                        Q(titreDocument__icontains=word)
                        | Q(descDocument__icontains=word)
                        | Q(fichier__icontains=word)
                    )
                else:
                    qs = qs.filter(
                        Q(titreDocument__icontains=word)
                        | Q(descDocument__icontains=word)
                    )

        if is_migrated:
            if type_doc and type_doc in Document.TypeDocument.values:
                qs = qs.filter(type_document=type_doc)
            if thematique and thematique in Document.Thematique.values:
                qs = qs.filter(thematique=thematique)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = {
            "q": self.request.GET.get("q", "").strip(),
            "type": self.request.GET.get("type", "").strip(),
            "thematique": self.request.GET.get("thematique", "").strip(),
        }
        context["params"] = params
        context["types"] = Document.TypeDocument.choices
        context["thematiques"] = Document.Thematique.choices
        context["total"] = context["paginator"].count
        context["filtered"] = bool(params["q"] or params["type"] or params["thematique"])
        return context


# Alias et classes conservés pour rétrocompatibilité
DocumentDetailView = AdminDocumentDetailView
DocumentCreateView = AdminDocumentCreateView
DocumentUpdateView = AdminDocumentUpdateView
DocumentDeleteView = AdminDocumentDeleteView
liste_documents = DocumentListView.as_view()
