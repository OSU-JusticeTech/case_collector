import csv
from datetime import datetime, timezone, date, timedelta

from django.http import HttpResponse
from django.shortcuts import render

from . import fake_state
# Create your views here.


def eviction_reports(request):

    months = []
    now = datetime.now(timezone.utc).date()
    startmon = now.year * 12 + (now.month)
    for i in range(14):
        month = ((startmon - i) % 12) + 1
        year = (startmon - i) // 12
        months.append(date(year, month, 1))
    start: date
    csvs = []
    for start, end in zip(months[1:], months):
        csvs.append((str(start),str(end - timedelta(days=1)), f"{start.isoweekday():06d}"))


    return render(request, "fcmcclerk_mock/report.html", context={"csvs": csvs})


def report_csv(request, start,end):
    start = date.fromisoformat(start)
    end = date.fromisoformat(end)
    print(start, end)
    field_names = ["CASE_NUMBER","CASE_FILE_DATE","LAST_DISPOSITION_DATE","LAST_DISPOSITION_DESCRIPTION","FIRST_PLAINTIFF_PARTY_SEQUENCE","FIRST_PLAINTIFF_FIRST_NAME","FIRST_PLAINTIFF_MIDDLE_NAME","FIRST_PLAINTIFF_LAST_NAME","FIRST_PLAINTIFF_SUFFIX_NAME","FIRST_PLAINTIFF_COMPANY_NAME","FIRST_PLAINTIFF_ADDRESS_LINE_1","FIRST_PLAINTIFF_ADDRESS_LINE_2","FIRST_PLAINTIFF_CITY","FIRST_PLAINTIFF_STATE","FIRST_PLAINTIFF_ZIP","FIRST_DEFENDANT_PARTY_SEQUENCE","FIRST_DEFENDANT_FIRST_NAME","FIRST_DEFENDANT_MIDDLE_NAME","FIRST_DEFENDANT_LAST_NAME","FIRST_DEFENDANT_SUFFIX_NAME","FIRST_DEFENDANT_COMPANY_NAME","FIRST_DEFENDANT_ADDRESS_LINE_1","FIRST_DEFENDANT_ADDRESS_LINE_2","FIRST_DEFENDANT_CITY","FIRST_DEFENDANT_STATE","FIRST_DEFENDANT_ZIP"]
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="evictions_{start}_to_{end}.csv"'

    writer = csv.DictWriter(response, fieldnames=field_names)
    writer.writeheader()

    for case in fake_state.EVICTION_FIXTURE:
        if start <= case.docket[-1].date <= end:
            writer.writerow({"CASE_NUMBER": case.case_number,
                             "CASE_FILE_DATE": case.docket[-1].date})

    return response