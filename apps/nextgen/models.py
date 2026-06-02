from django.db import models

from apps.cases.models import CourtCase
from apps.fcmcclerk.pyschema import Case

# Create your models here.

class MagdecAnalysis(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    page_number = models.IntegerField()

    good_matches = models.IntegerField()
    diff_sum = models.BigIntegerField()

    # transformation matrix
    m11 = models.FloatField()
    m12 = models.FloatField()
    m13 = models.FloatField()
    m21 = models.FloatField()
    m22 = models.FloatField()
    m23 = models.FloatField()

class RoiCount(models.Model):
    result = models.ForeignKey(
        MagdecAnalysis,
        on_delete=models.CASCADE,
        related_name="roi_counts"
    )

    roi_id = models.IntegerField()
    color_hex = models.CharField(max_length=7)
    count_nonwhite = models.IntegerField()

    class Meta:
        ordering = ["roi_id"]


class ScanDocketEntry(models.Model):
    date = models.DateField()
    text = models.CharField()
    case = models.ForeignKey(CourtCase, on_delete=models.CASCADE)
    scan = models.FileField(null=True, upload_to="nextgen")
    filename = models.CharField()
    magdec_analyses = models.ManyToManyField(MagdecAnalysis)

    def __str__(self):
        return (
            f"{self.case.case_number}: {self.date} {self.text[:20]}... {self.filename}"
        )




class Page(models.Model):

    case = models.ForeignKey(CourtCase, on_delete=models.SET_NULL, null=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    content = models.CharField(null=True)
    return_code = models.IntegerField()

    def __str__(self):
        return f"{self.case} {self.scraped_at} {self.return_code}"
