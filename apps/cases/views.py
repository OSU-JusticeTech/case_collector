import json
from datetime import datetime

from django.db import connection
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.reverse import reverse

from apps.cases.models import DailyEvents
from apps.cases.serializers import DailyEventsSerializer


# Create your views here.


def index(request):
    return render(request,"cases/index.html")

class DailyEventsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for daily case filings and docket event metrics.
    """
    queryset = DailyEvents.objects.all()
    serializer_class = DailyEventsSerializer

    @method_decorator(cache_page(60 * 15))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)



class HexGridView(viewsets.ViewSet):

    def list(self, request):
        current_year = datetime.now().year
        years = [
            {
                "year": year,
                "url": reverse(
                    "cases:hexgrids-detail",
                    kwargs={"pk": year},
                    request=request
                ),
                "format": "application/geo+json"
            }
            for year in range(2000, current_year + 1)
        ]

        return Response({
            "count": len(years),
            "results": years
        })

    @method_decorator(cache_page(60 * 15))
    def retrieve(self, request, pk=None):
        year = int(pk)
        print("load year", year)
        sql = """
            WITH bounds AS (
                SELECT ST_Transform(
                    ST_MakeEnvelope(
                        -83.232, 39.800,
                        -82.730, 40.160,
                        4326
                    ),
                    32617
                ) AS geom
            ),
            hexagons AS (
                SELECT
                    h.i,
                    h.j,
                    h.geom AS hex_geom,
                    ST_Transform(h.geom, 4326) AS geom_4326
                FROM bounds b
                CROSS JOIN LATERAL ST_HexagonGrid(500, b.geom) h
            )
            SELECT
                h.i,
                h.j,
                COUNT(mv.rooftop) AS total,
                ST_AsGeoJSON(h.geom_4326) AS geometry
            FROM hexagons h
            LEFT JOIN latest_overview mv
                ON mv.rooftop && h.geom_4326
                AND ST_Contains(h.geom_4326, mv.rooftop)
                AND mv.earliest_docket >= make_date(%s, 1, 1)
                AND mv.earliest_docket < make_date(%s + 1, 1, 1)
            GROUP BY h.i, h.j, h.geom_4326;
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, (year, year))

            rows = cursor.fetchall()

        features = []

        for i, j, total, geometry in rows:
            features.append({
                "type": "Feature",
                "geometry": json.loads(geometry),
                "properties": {
                    "i": i,
                    "j": j,
                    "count": total
                }
            })

        return Response({
            "type": "FeatureCollection",
            "features": features
        })