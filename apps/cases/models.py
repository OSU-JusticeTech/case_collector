from django.db import models

# Create your models here.

class Sources(models.Model):
    name = models.CharField(unique=True)

class Cases(models.Model):
    case_number: str
    source = models.ForeignKey(Sources, on_delete=models.CASCADE)

class CaseSnapshots(models.Model):
    state_hash = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)
    case = models.ForeignKey(Cases, on_delete=models.CASCADE)

class Parties(models.Model):
    side = models.CharField()
    name = models.CharField()
    address = models.CharField()
    city = models.CharField(null=True)
    state = models.CharField(null=True)
    zip_code = models.CharField(null=True)
    role = models.CharField()
    snapshot = models.ForeignKey(CaseSnapshots, on_delete=models.CASCADE)

class DocketEntries(models.Model):
    date = models.DateField()
    text = models.CharField()
    extra = models.CharField(null=True)
    amount = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    balance = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    snapshot = models.ForeignKey(CaseSnapshots, on_delete=models.CASCADE)

class Events(models.Model):
    room = models.CharField()
    start = models.DateTimeField()
    end = models.DateTimeField()
    event = models.CharField()
    judge = models.CharField()
    result = models.CharField()
    snapshot = models.ForeignKey(CaseSnapshots, on_delete=models.CASCADE)


class Finances(models.Model):
    application = models.CharField()
    owed = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    paid = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    dismissed = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    balance = models.DecimalField(null=True, max_digits=10, decimal_places=2)
    snapshot = models.ForeignKey(CaseSnapshots, on_delete=models.CASCADE)


class Dispositions(models.Model):
    code = models.CharField()
    date = models.DateTimeField(null=True)
    judge = models.CharField()
    status = models.CharField()
    status_date = models.DateField()
    snapshot = models.ForeignKey(CaseSnapshots, on_delete=models.CASCADE)