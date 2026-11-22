from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .forms import TicketForm
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
