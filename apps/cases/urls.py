from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.cases.views import DailyEventsViewSet

app_name = "cases"

router = DefaultRouter()
router.register(r'daily-events', DailyEventsViewSet, basename='daily-events')

urlpatterns = [
    path('api/', include(router.urls)),
]