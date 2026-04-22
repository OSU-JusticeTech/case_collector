import base64
import json
import secrets
from datetime import datetime

from django import views
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from apps.fcmcclerk_mock.fake_state import fixture_at
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

@csrf_exempt
def results(request, request_date):

    form = SearchForm(request.POST)

    if form.is_valid():
        # print("valid form")
        cases = fixture_at(datetime.fromisoformat(request_date).date())
        print("form")

        for case in cases:
            if case.case_number == form.cleaned_data["case_number"]:
                return render(
                    request,
                    "nextgen_mock/result.html",
                    context={
                        "case": case,
                        "case_id": base64.b64encode(
                            json.dumps({"number": case.case_number}).encode()
                        ).decode(),
                    },
                )
        return redirect("nextgen_mock:search", request_date=request_date)

@csrf_exempt
def case_view(request, request_date):

    data = json.loads(base64.b64decode(request.POST.get("case_id")))
    cases = fixture_at(datetime.fromisoformat(request_date).date())

    for case in cases:
        if case.case_number == data["number"]:
            return render(request, "nextgen_mock/view.html", context={"case": case})