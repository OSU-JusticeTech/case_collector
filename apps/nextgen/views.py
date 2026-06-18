from django.contrib.auth.decorators import login_required
from django.http import Http404, FileResponse
from django.shortcuts import render, get_object_or_404
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.nextgen.models import ScanDocketEntry


# Create your views here.

class DownloadScanView(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        entry = get_object_or_404(ScanDocketEntry, pk=pk)

        if not entry.scan:
            raise Http404("No scan attached")

        return FileResponse(
            entry.scan.open("rb"),
            as_attachment=True,
            filename=entry.filename or entry.scan.name.rsplit("/", 1)[-1],
        )