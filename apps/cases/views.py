from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets

from apps.cases.models import DailyEvents
from apps.cases.serializers import DailyEventsSerializer


# Create your views here.

class DailyEventsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for daily case filings and docket event metrics.
    """
    queryset = DailyEvents.objects.all()
    serializer_class = DailyEventsSerializer

    @method_decorator(cache_page(60 * 15))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
