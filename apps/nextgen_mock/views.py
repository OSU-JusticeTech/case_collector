import base64
import json
import secrets
from datetime import datetime

from django import views
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from apps.fcmcclerk.pyschema import Case
from apps.fcmcclerk_mock.fake_state import fixture_at
from apps.fcmcclerk_mock.forms import SearchForm
from apps.nextgen_mock.forms import LoginForm

# Create your views here.


@method_decorator(csrf_exempt, name="dispatch")
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
        print("could not find", form.cleaned_data)
        return redirect("nextgen_mock:search", request_date=request_date)


@csrf_exempt
def case_view(request, request_date):

    data = json.loads(base64.b64decode(request.POST.get("case_id")))
    cases = fixture_at(datetime.fromisoformat(request_date).date())

    for case in cases:
        if case.case_number == data["number"]:
            docket = []
            for i, d in enumerate(case.docket):
                payload = None
                if d.scan is not None:
                    payload = base64.b64encode(
                        json.dumps(
                            {
                                "iv": base64.b64encode(
                                    secrets.token_bytes(16)
                                ).decode(),
                                "value": base64.b64encode(
                                    json.dumps((case.case_number, i)).encode()
                                ).decode(),
                                "mac": secrets.token_hex(32),
                                "tag": "",
                            }
                        ).encode()
                    ).decode()

                docket.append((d, payload))
            return render(
                request,
                "nextgen_mock/view.html",
                context={"case": case, "docket": docket,
                         "request_date": request_date},
            )


def case_image(request, request_date):
    data = json.loads(base64.b64decode(request.GET.get("q","")))
    # print(data)
    case_number, i = json.loads(base64.b64decode(data["value"]))
    cases = fixture_at(datetime.fromisoformat(request_date).date())

    for case in cases:
        if case.case_number == case_number:

            response = HttpResponse(case.docket[i].scan.data, content_type='application/pdf')
            response['Content-Disposition'] = 'inline;filename='+case.docket[i].scan.filename
            return response
