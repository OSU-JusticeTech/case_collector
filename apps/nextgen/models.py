from django.db import models

from apps.cases.models import CourtCase
from apps.fcmcclerk.pyschema import Case


# Create your models here.

class ScanDocketEntry(models.Model):
    date = models.DateField()
    text = models.CharField()
    case = models.ForeignKey(CourtCase, on_delete=models.CASCADE)
    scan = models.FileField(null=True, upload_to="nextgen")
    filename = models.CharField()

    def __str__(self):
        return f"{self.case.case_number}: {self.date} {self.text[:20]}... {self.filename}"

