from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.shortcuts import redirect

from .forms import DocumentForm
from .models import Document


@login_required
def liste_documents(request):
    documents = Document.objects.all().order_by("-created_at")
    return render(
        request,
        "DocumentApp/liste_documents.html",
        {"documents": documents},
    )


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = "DocumentApp/liste_documents.html"
    context_object_name = "documents"

    def get_queryset(self):
        return Document.objects.all().order_by("-created_at")


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Vous n'avez pas accès à la gestion des documents.")
            return redirect("DocumentApp:liste")
        return super().handle_no_permission()


class DocumentDetailView(AdminRequiredMixin, DetailView):
    model = Document
    template_name = "DocumentApp/detail_document.html"
    context_object_name = "document"
    pk_url_kwarg = "idDocument"


class DocumentCreateView(AdminRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "DocumentApp/form_document.html"

    def get_success_url(self):
        return reverse("DocumentApp:detail", kwargs={"idDocument": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Le document a bien été ajouté.")
        return response


class DocumentUpdateView(AdminRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = "DocumentApp/form_document.html"
    pk_url_kwarg = "idDocument"

    def get_success_url(self):
        return reverse("DocumentApp:detail", kwargs={"idDocument": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Le document a bien été modifié.")
        return response


class DocumentDeleteView(AdminRequiredMixin, DeleteView):
    model = Document
    pk_url_kwarg = "idDocument"
    success_url = reverse_lazy("DocumentApp:liste")
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, "Le document a bien été supprimé.")
        return response
