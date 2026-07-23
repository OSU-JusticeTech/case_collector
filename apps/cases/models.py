from django.db import models
from django.contrib.gis.db import models as gis_models

from apps.geocode.models import Location

# Create your models here.


class Source(models.Model):
    name = models.CharField(unique=True)

    def __str__(self):
        return self.name


class CourtCase(models.Model):
    case_number = models.CharField()
    source = models.ForeignKey(Source, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.source}: {self.case_number}"


class CaseSnapshot(models.Model):
    state_hash = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)
    case = models.ForeignKey(CourtCase, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.case} @ {self.created_at} {self.state_hash.hex()}"


class Party(models.Model):
    side = models.CharField()
    name = models.CharField()
    address = models.CharField()
    city = models.CharField(null=True)
    state = models.CharField(null=True)
    zip_code = models.CharField(null=True)
    role = models.CharField()
    snapshot = models.ForeignKey(CaseSnapshot, on_delete=models.CASCADE)

    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.side[:3]} {self.name} {self.address} {self.city} {self.state}/{self.zip_code} {self.role}"


class DocketEntry(models.Model):
    date = models.DateField()
    text = models.CharField()
    extra = models.CharField(null=True)
    amount = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    balance = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    snapshot = models.ForeignKey(CaseSnapshot, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.date} {self.text}"


class Event(models.Model):
    room = models.CharField()
    start = models.DateTimeField()
    end = models.DateTimeField()
    event = models.CharField()
    judge = models.CharField()
    result = models.CharField()
    snapshot = models.ForeignKey(CaseSnapshot, on_delete=models.CASCADE)

    class Meta:
        ordering = ("start",)

    def __str__(self):
        return f"{self.room} {self.start} {self.event} {self.result}"


class Finance(models.Model):
    application = models.CharField()
    owed = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    paid = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    dismissed = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    balance = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    snapshot = models.ForeignKey(CaseSnapshot, on_delete=models.CASCADE)


class Disposition(models.Model):
    code = models.CharField()
    date = models.DateField(null=True)
    judge = models.CharField()
    status = models.CharField()
    status_date = models.DateField(null=True)
    snapshot = models.ForeignKey(CaseSnapshot, on_delete=models.CASCADE)

    class Meta:
        ordering = ("date",)


class LatestOverview(models.Model):
    case_number = models.CharField(editable=False)
    source = models.ForeignKey(Source, on_delete=models.DO_NOTHING, editable=False)
    created_at = models.DateTimeField(editable=False)

    # s.id,
    snapshot = models.OneToOneField(
        CaseSnapshot,
        on_delete=models.DO_NOTHING,
        db_column="id",  # The actual column name in your materialized view
        primary_key=True,  # Since it's a 1:1 view, the case ID is the PK
        db_constraint=False,  # Prevents Django from trying to write a DB constraint
    )

    earliest_docket = models.DateField(editable=False)
    latest_docket = models.DateField(editable=False)

    code = models.CharField(editable=False)
    date = models.DateField(null=True, editable=False)
    judge = models.CharField(editable=False)
    status = models.CharField(editable=False)
    status_date = models.DateField(editable=False)

    disposition_count = models.SmallIntegerField(editable=False)
    defendant_count = models.SmallIntegerField(editable=False)
    plaintiff_count = models.SmallIntegerField(editable=False)

    stdef_name = models.CharField(editable=False)
    stdef_address = models.CharField(editable=False)
    stdef_city = models.CharField(null=True, editable=False)
    stdef_state = models.CharField(null=True, editable=False)
    stdef_zip_code = models.CharField(null=True, editable=False)

    full_address = models.CharField(editable=False)

    street_number = models.CharField(blank=True, editable=False)
    street_name = models.CharField(blank=True, editable=False)
    street_type = models.CharField(blank=True, editable=False)
    street_direction = models.CharField(blank=True, editable=False)

    unit_type = models.CharField(blank=True, editable=False)
    unit_number = models.CharField(blank=True, editable=False)

    city = models.CharField(blank=True, editable=False)
    county = models.CharField(blank=True, editable=False)
    state_code = models.CharField(blank=True, editable=False)

    postal_code = models.CharField(blank=True, editable=False)

    country = models.CharField(blank=True, editable=False)

    rooftop = gis_models.PointField(editable=False)

    geocode_score = models.FloatField(null=True, blank=True, editable=False)
    geocode_rank = models.FloatField(null=True, blank=True, editable=False)
    geocode_type = models.CharField(blank=True, editable=False)

    stptf_name = models.CharField(editable=False)
    stptf_address = models.CharField(editable=False)
    stptf_city = models.CharField(null=True, editable=False)
    stptf_state = models.CharField(null=True, editable=False)
    stptf_zip_code = models.CharField(null=True, editable=False)

    stptfatt_name = models.CharField(editable=False)
    stptfatt_address = models.CharField(editable=False)
    stptfatt_city = models.CharField(null=True, editable=False)
    stptfatt_state = models.CharField(null=True, editable=False)
    stptfatt_zip_code = models.CharField(null=True, editable=False)

    def __str__(self):
        return f"{self.case_number}"

    class Meta:
        managed = False
        db_table = "latest_overview"

    # 1. Prevent saving/updating
    def save(self, *args, **kwargs):
        # You can either silently ignore the save, or raise an error to be safe:
        raise NotImplementedError("This model is read-only.")

    # 2. Prevent deleting
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This model is read-only.")

class DailyEvents(models.Model):
    date = models.DateField(editable=False, primary_key=True)
    cases_filed = models.IntegerField(editable=False)
    writs_issued = models.IntegerField(editable=False)
    setouts_processed = models.IntegerField(editable=False)
    setouts_completed = models.IntegerField(editable=False)

    def __str__(self):
        return f"{self.date}"

    class Meta:
        managed = False
        db_table = "daily_events"

    # 1. Prevent saving/updating
    def save(self, *args, **kwargs):
        # You can either silently ignore the save, or raise an error to be safe:
        raise NotImplementedError("This model is read-only.")

    # 2. Prevent deleting
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This model is read-only.")
