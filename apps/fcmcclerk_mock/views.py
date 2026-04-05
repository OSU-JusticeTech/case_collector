from django.shortcuts import render

# Create your views here.

def eviction_reports(request):

    return render(request, "fcmcclerk_mock/report.html")