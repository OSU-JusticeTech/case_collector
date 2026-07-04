import csv

from django import views
from django.http import HttpResponse
from django.shortcuts import render


# Create your views here.

class SearchView(views.View):

    def get(self, request, request_date):
        return render(request, "violations_mock/search.html")

    def post(self, request, request_date):
        return render(request, "violations_mock/results.part")


def download(request, request_date):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f"attachment;filename=RecordList20260704.csv"
    )

    resp = '"Date","Record Number","Record Type","Address","Description","Status",\n'

    for _ in range(10):
        resp += f'"07/01/2026","26123-01234","Enforcement/Housing Code Inspection/Exterior/General","ADDRESS, COLUMBUS OH 43210","Housing Inspection","Active",\n'

    response.write(resp)

    return response