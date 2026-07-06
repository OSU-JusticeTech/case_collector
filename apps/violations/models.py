from django.db import models

# Create your models here.


class CodeViolation(models.Model):
    date = models.DateField()
    record_number = models.CharField()
    record_type = models.CharField()
    address = models.CharField()
    description = models.CharField()
    status = models.CharField()

    scraped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} {self.record_number} {self.record_type} {self.address} {self.status}"
