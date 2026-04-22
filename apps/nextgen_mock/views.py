import secrets

from django import views
from django.shortcuts import render, redirect

from apps.fcmcclerk_mock.forms import SearchForm
from apps.nextgen_mock.forms import LoginForm


# Create your views here.

class LoginView(views.View):
    def get(self, request, request_date):
        form = LoginForm()
        return render(request, "nextgen_mock/login.html", context={"form": form})

    def post(self, request, request_date):
        form = LoginForm(request.POST)
        if form.is_valid():
            return redirect("nextgen_mock:home", request_date=request_date)

def home(request, request_date):
    return render(request, "nextgen_mock/home.html")

def search(request, request_date):

    form = SearchForm()
    token = secrets.token_urlsafe(32)
    request.session["form_token"] = token

    return render(
        request, "nextgen_mock/search.html", context={"form": form, "token": token}
    )