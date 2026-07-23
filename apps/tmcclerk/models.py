from django.db import models

# Create your models here.

class Page(models.Model):
    year = models.IntegerField()
    category = models.CharField()
    number = models.IntegerField()
    scraped_at = models.DateTimeField(auto_now_add=True)
    content = models.CharField(null=True)
    return_code = models.IntegerField()

    class Meta:
        unique_together = ("year", "category", "number", "scraped_at")

    def __str__(self):
        return f"{self.category}-{self.year%100}-{self.number:05d} @ {self.scraped_at} ({self.return_code})"

class SearchResult(models.Model):
    search_start = models.DateField()
    content = models.CharField(null=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    return_code = models.IntegerField()