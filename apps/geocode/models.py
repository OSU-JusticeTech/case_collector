from django.contrib.gis.db import models

# Create your models here.

class Location(models.Model):
    # Human-readable
    full_address = models.CharField()

    street_number = models.CharField(blank=True)
    street_name = models.CharField(blank=True)
    street_type = models.CharField(blank=True)
    street_direction = models.CharField(blank=True)

    unit_type = models.CharField(blank=True)
    unit_number = models.CharField(blank=True)

    city = models.CharField(blank=True)
    county = models.CharField(blank=True)
    state = models.CharField(blank=True)
    state_code = models.CharField(blank=True)

    postal_code = models.CharField(blank=True)
    postal_code_ext = models.CharField(blank=True)

    country = models.CharField(blank=True)

    rooftop = models.PointField()

    geocode_score = models.FloatField(null=True, blank=True)
    geocode_rank = models.FloatField(null=True, blank=True)
    geocode_type = models.CharField(blank=True)

    raw_geocode = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_address