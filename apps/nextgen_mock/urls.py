from django.urls import path, re_path

from apps.nextgen_mock.views import LoginView, home, search, results, case_view

app_name = "nextgen_mock"
urlpatterns = [
    path("<str:request_date>/nextgen/login", LoginView.as_view()),
    path("<str:request_date>/nextgen/home", home, name="home"),
    path("<str:request_date>/nextgen/case/search", search, name="search"),
    path("<str:request_date>/nextgen/case/search/results", results),
    path("<str:request_date>/nextgen/case/view", case_view),
    #re_path(
    #    r"^(?P<request_date>\d{4}-\d{2}-\d{2})/storage/shared/civil-fed/FCMC Civil F.E.D. \(Eviction\) Case List (?P<start>\d{4}-\d{2}-\d{2}) to (?P<end>\d{4}-\d{2}-\d{2}).csv",
    #    report_csv,
    #),
]
