from django.db import models

# Create your models here.


class CheckinSheet(models.Model):
    photo = models.ImageField(null=True, upload_to="checkin")
    filename = models.CharField()
    taken_at = models.DateTimeField()
    file_hash = models.CharField(max_length=64, unique=True)

    possible_start = models.DateField(null=True, blank=True)
    possible_end = models.DateField(null=True, blank=True)

    processed = models.JSONField(null=True, blank=True)
    validated = models.BooleanField(default=False)

    event_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.filename
