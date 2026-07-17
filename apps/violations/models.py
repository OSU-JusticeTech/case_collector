from django.db import models

from apps.geocode.models import Location


# Create your models here.


class CodeViolation(models.Model):
    date = models.DateField()
    record_number = models.CharField()
    record_type = models.CharField()
    address = models.CharField()
    description = models.CharField()
    status = models.CharField()

    scraped_at = models.DateTimeField(auto_now_add=True)

    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.date} {self.record_number} {self.record_type} {self.address} {self.status}"
