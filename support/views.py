from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import CommentaireForm, TicketForm
from .models import Ticket






class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = "support/liste.html"
    context_object_name = "tickets"

    def get_queryset(self):
        # Chaque utilisateur ne voit que ses propres tickets
        return Ticket.objects.filter(auteur=self.request.user)


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = "support/form.html"
    success_url = reverse_lazy("support:liste")

    def form_valid(self, form):
        # L'auteur est toujours l'utilisateur connecté
        form.instance.auteur = self.request.user
        messages.success(self.request, "Votre ticket a bien été créé.")
        return super().form_valid(form)

class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = "support/detail.html"
    context_object_name = "ticket"

    def get_queryset(self):
        # Un utilisateur ne peut ouvrir que ses propres tickets (sinon 404)
        return Ticket.objects.filter(auteur=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["commentaires"] = self.object.commentaires.select_related("auteur")
        context["form_reponse"] = CommentaireForm()
        return context


class TicketUpdateView(LoginRequiredMixin, UpdateView):
    model = Ticket
    form_class = TicketForm
    template_name = "support/form.html"

    def get_queryset(self):
        return Ticket.objects.filter(auteur=self.request.user)

    def get_object(self, queryset=None):
        ticket = super().get_object(queryset)
        # Modifiable seulement tant que le ticket est « Ouvert »
        if ticket.statut != Ticket.Statut.OUVERT:
            raise PermissionDenied("Ce ticket est déjà pris en charge, il n'est plus modifiable.")
        return ticket

    def get_success_url(self):
        return reverse("support:detail", args=[self.object.pk])

    def form_valid(self, form):
        messages.success(self.request, "Votre ticket a bien été modifié.")
        return super().form_valid(form)


class TicketReplyView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        # Seul l'auteur du ticket peut y répondre (sinon 404)
        ticket = get_object_or_404(Ticket, pk=pk, auteur=request.user)

        if ticket.statut == Ticket.Statut.FERME:
            messages.error(request, "Ce ticket est fermé : vous ne pouvez plus y répondre.")
            return redirect("support:detail", pk=pk)

        form = CommentaireForm(request.POST)
        if form.is_valid():
            commentaire = form.save(commit=False)
            commentaire.ticket = ticket
            commentaire.auteur = request.user
            commentaire.save()
            ticket.maj_statut_apres_reponse(par_admin=False)
            messages.success(request, "Votre réponse a bien été envoyée.")
        else:
            messages.error(request, "Votre message est vide.")
        return redirect("support:detail", pk=pk)
