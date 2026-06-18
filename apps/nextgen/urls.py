from django.urls import path, re_path

from apps.nextgen import views

app_name = "nextgen"
urlpatterns = [
    path(
        "entry/<int:pk>/download/",
        views.DownloadScanView.as_view(),
        name="download_scan",
    )
]
