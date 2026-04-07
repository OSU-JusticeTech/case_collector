from django.urls import path, re_path

from apps.fcmcclerk_mock.views import eviction_reports, report_csv, search, results, case_view

app_name = "fcmcclerk_mock"
urlpatterns = [
    path("<str:request_date>/reports/evictions", eviction_reports),
    path("<str:request_date>/case/search", search, name="search"),
    path("<str:request_date>/case/search/results", results),
    path("<str:request_date>/case/view", case_view),
    re_path(
        r"^(?P<request_date>\d{4}-\d{2}-\d{2})/storage/shared/civil-fed/FCMC Civil F.E.D. \(Eviction\) Case List (?P<start>\d{4}-\d{2}-\d{2}) to (?P<end>\d{4}-\d{2}-\d{2}).csv",
        report_csv,
    ),
]
