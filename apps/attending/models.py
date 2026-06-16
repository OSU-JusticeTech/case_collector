from django.db import models

# Create your models here.

class CheckinSheet(models.Model):
    photo = models.ImageField(null=True, upload_to="checkin")
    filename = models.CharField()
    taken_at = models.DateTimeField()
    file_hash = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.filename