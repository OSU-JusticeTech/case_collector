from django.db import models

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
    status_date = models.DateField()
    snapshot = models.ForeignKey(CaseSnapshot, on_delete=models.CASCADE)
