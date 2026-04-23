from django.urls import path, re_path

from apps.nextgen_mock.views import LoginView, home, search, results, case_view, case_image

app_name = "nextgen_mock"
urlpatterns = [
    path("<str:request_date>/nextgen/login", LoginView.as_view()),
    path("<str:request_date>/nextgen/home", home, name="home"),
    path("<str:request_date>/nextgen/case/search", search, name="search"),
    path("<str:request_date>/nextgen/case/search/results", results),
    path("<str:request_date>/nextgen/case/view", case_view),
    path("<str:request_date>/nextgen/case/image", case_image),
]
