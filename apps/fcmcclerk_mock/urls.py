from django.urls import path

from apps.fcmcclerk_mock.views import eviction_reports

urlpatterns = [
    path('reports/evictions', eviction_reports),
]
