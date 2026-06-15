from django.urls import path, re_path

from apps.attending.views import base, FileList, FileLoad, data

app_name = "attending"
urlpatterns = [
    path("", base),
    path("files", FileList.as_view(), name="files"),
    path("load/<str:filename>", FileLoad.as_view(), name="load"),
    path("data/<str:filename>", data, name="data"),

]
