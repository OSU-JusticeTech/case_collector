from django.urls import path, re_path
from rest_framework.views import APIView

from apps.attending.views import (
    base,
    FileList,
    FileLoad,
    data,
    Save,
    AllCasesUpcomingEventCountsView,
    EventsAtTimeView, checkin, DocketSessionStateView,
)

app_name = "attending"
urlpatterns = [
    path("", base),
    path("files", FileList.as_view(), name="files"),
    path("load/<str:filename>", FileLoad.as_view(), name="load"),
    path("data/<str:filename>", data, name="data"),
    path("save/<str:filename>", Save.as_view(), name="save"),
    path("checkin/", checkin),
    path("checkin/persist/", DocketSessionStateView.as_view(),name="persist"),
    path(
        "dates",
        AllCasesUpcomingEventCountsView.as_view(),
        name="upcoming-event",
    ),
    path("events/", EventsAtTimeView.as_view(), name="events-at-time"),
]
