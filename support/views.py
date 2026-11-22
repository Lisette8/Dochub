from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def liste(request):
    return render(request, "support/liste.html")
