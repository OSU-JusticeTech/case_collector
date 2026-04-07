import base64
import csv
import hashlib
import json
import secrets
from datetime import datetime, timezone, date, timedelta

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from . import fake_state
from .fake_state import fixture_at
from .forms import SearchForm

from django.contrib import messages

# Create your views here.


def eviction_reports(request, request_date):

    months = []
    now = datetime.fromisoformat(request_date).date()
    startmon = now.year * 12 + (now.month)
    for i in range(14):
        month = ((startmon - i) % 12) + 1
        year = (startmon - i) // 12
        months.append(date(year, month, 1))
    start: date
    csvs = []
    for start, end in zip(months[1:], months):
        csvs.append(
            (str(start), str(end - timedelta(days=1)), f"{start.isoweekday():06d}")
        )

    return render(request, "fcmcclerk_mock/report.html", context={"csvs": csvs})


def report_csv(request, request_date, start, end):
    start = date.fromisoformat(start)
    end = date.fromisoformat(end)
    # print(start, end)
    field_names = [
        "CASE_NUMBER",
        "CASE_FILE_DATE",
        "LAST_DISPOSITION_DATE",
        "LAST_DISPOSITION_DESCRIPTION",
        "FIRST_PLAINTIFF_PARTY_SEQUENCE",
        "FIRST_PLAINTIFF_FIRST_NAME",
        "FIRST_PLAINTIFF_MIDDLE_NAME",
        "FIRST_PLAINTIFF_LAST_NAME",
        "FIRST_PLAINTIFF_SUFFIX_NAME",
        "FIRST_PLAINTIFF_COMPANY_NAME",
        "FIRST_PLAINTIFF_ADDRESS_LINE_1",
        "FIRST_PLAINTIFF_ADDRESS_LINE_2",
        "FIRST_PLAINTIFF_CITY",
        "FIRST_PLAINTIFF_STATE",
        "FIRST_PLAINTIFF_ZIP",
        "FIRST_DEFENDANT_PARTY_SEQUENCE",
        "FIRST_DEFENDANT_FIRST_NAME",
        "FIRST_DEFENDANT_MIDDLE_NAME",
        "FIRST_DEFENDANT_LAST_NAME",
        "FIRST_DEFENDANT_SUFFIX_NAME",
        "FIRST_DEFENDANT_COMPANY_NAME",
        "FIRST_DEFENDANT_ADDRESS_LINE_1",
        "FIRST_DEFENDANT_ADDRESS_LINE_2",
        "FIRST_DEFENDANT_CITY",
        "FIRST_DEFENDANT_STATE",
        "FIRST_DEFENDANT_ZIP",
    ]
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="evictions_{start}_to_{end}.csv"'
    )

    writer = csv.DictWriter(response, fieldnames=field_names)
    writer.writeheader()

    cases = fixture_at(datetime.fromisoformat(request_date).date())

    for case in cases:
        if start <= case.docket[-1].date <= end:  # min(end, datetime.now().date()):
            if "CVG" in case.case_number:
                writer.writerow(
                    {
                        "CASE_NUMBER": case.case_number,
                        "CASE_FILE_DATE": case.docket[-1].date,
                        "LAST_DISPOSITION_DATE": case.dispositions[-1].date,
                        "LAST_DISPOSITION_DESCRIPTION": case.dispositions[-1].code
                    }
                )

    return response


def search(request, request_date):

    form = SearchForm()
    token = secrets.token_urlsafe(32)
    request.session["form_token"] = token

    return render(
        request, "fcmcclerk_mock/search.html", context={"form": form, "token": token}
    )


@csrf_exempt
def results(request, request_date):

    form = SearchForm(request.POST)
    #print("token", request.POST.get("_token"))
    form_token = request.POST.get("_token")
    sess_token = request.session.get("form_token")

    if sess_token is None or form_token != sess_token:
        return HttpResponse("wrong token")

    if form.is_valid():
        #print("valid form")
        cases = fixture_at(datetime.fromisoformat(request_date).date())

        for case in cases:
            if case.case_number == form.cleaned_data["case_number"]:
                token = secrets.token_urlsafe(32)
                request.session["result_token"] = token
                return render(
                    request,
                    "fcmcclerk_mock/result.html",
                    context={
                        "token": token,
                        "case": case,
                        "case_id": base64.b64encode(
                            json.dumps({"number": case.case_number}).encode()
                        ).decode(),
                    },
                )
        for case in cases[-20:]:
            print(case.case_number)
        messages.error(request, f"Not found")
        return redirect("fcmcclerk_mock:search", request_date=request_date)


@csrf_exempt
def case_view(request, request_date):
    #print("token", request.POST.get("_token"))
    #print("id", request.POST.get("case_id"))

    data = json.loads(base64.b64decode(request.POST.get("case_id")))
    cases = fixture_at(datetime.fromisoformat(request_date).date())

    for case in cases:
        if case.case_number == data["number"]:
            return render(request, "fcmcclerk_mock/view.html", context={"case": case})
