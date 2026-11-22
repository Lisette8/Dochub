from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from users.permissions import AdminRequiredMixin

from .forms import ActualiteForm
from .models import Actualite


# ---------- Interface utilisateur ----------



class ActualiteListView(LoginRequiredMixin, ListView):
    template_name = "actualites/liste.html"
    context_object_name = "actualites"
    paginate_by = 9

    def get_queryset(self):
        # Seules les actualités publiées sont visibles, les épinglées en premier
        return Actualite.objects.filter(
            statut=Actualite.Statut.PUBLIE
        ).order_by("-epinglee", "-created_at")


class ActualiteDetailView(LoginRequiredMixin, DetailView):
    template_name = "actualites/detail.html"
    context_object_name = "actualite"

    def get_queryset(self):
        # Un brouillon renvoie une 404 : il n'existe pas pour l'utilisateur
        return Actualite.objects.filter(statut=Actualite.Statut.PUBLIE)


# ---------- Interface administrateur ----------

class GestionListView(AdminRequiredMixin, ListView):
    template_name = "actualites/gestion_liste.html"
    context_object_name = "actualites"
    paginate_by = 10

    def get_queryset(self):
        qs = Actualite.objects.all()
        q = self.request.GET.get("q", "").strip()
        statut = self.request.GET.get("statut", "")
        categorie = self.request.GET.get("categorie", "")
        if q:
            qs = qs.filter(Q(titre__icontains=q) | Q(description__icontains=q))
        if statut:
            qs = qs.filter(statut=statut)
        if categorie:
            qs = qs.filter(categorie=categorie)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["params"] = self.request.GET
        context["statuts"] = Actualite.Statut.choices
        context["categories"] = Actualite.Categorie.choices
        context["total"] = context["paginator"].count
        return context


class GestionCreateView(AdminRequiredMixin, CreateView):
    model = Actualite
    form_class = ActualiteForm
    template_name = "actualites/gestion_form.html"
    success_url = reverse_lazy("actualites:gestion_liste")

    def form_valid(self, form):
        messages.success(self.request, "L'actualité a bien été créée.")
        return super().form_valid(form)


class GestionUpdateView(AdminRequiredMixin, UpdateView):
    model = Actualite
    form_class = ActualiteForm
    template_name = "actualites/gestion_form.html"
    success_url = reverse_lazy("actualites:gestion_liste")

    def form_valid(self, form):
        messages.success(self.request, "L'actualité a bien été modifiée.")
        return super().form_valid(form)


class GestionDeleteView(AdminRequiredMixin, DeleteView):
    model = Actualite
    template_name = "actualites/gestion_confirm_delete.html"
    success_url = reverse_lazy("actualites:gestion_liste")

    def form_valid(self, form):
        messages.success(self.request, "L'actualité a bien été supprimée.")
        return super().form_valid(form)