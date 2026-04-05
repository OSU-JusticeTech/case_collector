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
    case_number = models.IntegerField()
    scraped_at = models.DateTimeField(auto_now_add=True)
    content = models.CharField(null=True)
    return_code = models.IntegerField()

    class Meta:
        unique_together = ("year", "category", "case_number", "scraped_at")
