from django.urls import path

from apps.violations_mock.views import SearchView, download

app_name = "violations_mock"
urlpatterns = [
    path("<str:request_date>/permits/Cap/CapHome.aspx", SearchView.as_view()),
    path("<str:request_date>/Permits/Export2CSV.ashx", download),
]
