from django.db import models

# Create your models here.

class RenterOccupiedZip(models.Model):
    "This is the B25008_003E ACS value: Total number of people in rental units"

    year = models.IntegerField()
    zip_code = models.CharField()
    estimate = models.IntegerField()
    margin = models.IntegerField()

    def __str__(self) -> str:
        return f"{self.year} {self.zip_code} {self.estimate} ± {self.margin}"