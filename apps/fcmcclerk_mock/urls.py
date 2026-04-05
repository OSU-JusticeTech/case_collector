from django.urls import path, re_path

from apps.fcmcclerk_mock.views import eviction_reports, report_csv

urlpatterns = [
    path("reports/evictions", eviction_reports),
    re_path(r"^storage/shared/civil-fed/FCMC Civil F.E.D. \(Eviction\) Case List (?P<start>\d{4}-\d{2}-\d{2}) to (?P<end>\d{4}-\d{2}-\d{2}).csv", report_csv),
]
