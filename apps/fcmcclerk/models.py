from django.db import models

# Create your models here.


class Page(models.Model):
    CVG = "CVG"
    CVF = "CVF"
    CVR = "CVR"
    CVE = "CVE"
    CATEGORIES = {
        CVG: "Forcible Entry and Detainer",
        CVF: "Contract",
        CVR: "Rent Escrow",
        CVE: "Personal Injury",
    }

    year = models.IntegerField()
    category = models.CharField(choices=CATEGORIES)
    number = models.IntegerField()
    scraped_at = models.DateTimeField(auto_now_add=True)
    content = models.CharField(null=True)
    return_code = models.IntegerField()
    overview_digest = models.CharField(null=True)

    class Meta:
        unique_together = ("year", "category", "number", "scraped_at")

    def __str__(self):
        return f"{self.year} {self.category} {self.number:06d} @ {self.scraped_at} ({self.return_code})"
