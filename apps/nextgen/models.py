import os

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

    def __str__(self):
        return f"{self.page_number}: {self.diff_sum} {self.good_matches}"


class RoiCount(models.Model):
    result = models.ForeignKey(
        MagdecAnalysis, on_delete=models.CASCADE, related_name="roi_counts"
    )

    roi_id = models.IntegerField()
    color_hex = models.CharField(max_length=7)
    count_nonwhite = models.IntegerField()

    class Meta:
        ordering = ["roi_id"]

    def __str__(self):
        return f"{self.result} {self.roi_id}: {self.count_nonwhite}"

def nextgen_filenames(instance, filename):
    parts = instance.case.case_number.split(" ")
    year = int(parts[0])
    cat = "_".join(parts[1:-1])
    number = int(parts[-1])
    return os.path.join('nextgen', str(year),str(cat),f"{number:06d}"[:2], filename)

class ScanDocketEntry(models.Model):
    date = models.DateField()
    text = models.CharField()
    case = models.ForeignKey(CourtCase, on_delete=models.CASCADE)
    scan = models.FileField(null=True, upload_to=nextgen_filenames)
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


class Presence(models.Model):
    #analysis_id,
    #id,
    created_at = models.DateTimeField()

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

    check_0_dismissed = models.IntegerField()
    check_1_reassign = models.IntegerField()
    check_2_only_defendant = models.IntegerField()
    check_3_none = models.IntegerField()
    check_4_both = models.IntegerField()
    check_5_only_plaintiff = models.IntegerField()
    top_roi_id = models.IntegerField()
    top_count = models.IntegerField()
    second_count = models.IntegerField()
    top_to_second_ratio = models.FloatField()
    entry = models.ForeignKey(ScanDocketEntry, on_delete=models.DO_NOTHING)
    date = models.DateField()
    text = models.CharField()
    case = models.ForeignKey(CourtCase, on_delete=models.DO_NOTHING)
    case_number = models.TextField()
    # date, text, scan, case_id, filename, source_id, case_number)


    class Meta:
        managed = False
        db_table = "nextgen_magistrate_presence"

    # 1. Prevent saving/updating
    def save(self, *args, **kwargs):
        # You can either silently ignore the save, or raise an error to be safe:
        raise NotImplementedError("This model is read-only.")

    # 2. Prevent deleting
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This model is read-only.")
