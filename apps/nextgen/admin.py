from django.contrib import admin

from apps.nextgen.models import ScanDocketEntry, Page, MagdecAnalysis, RoiCount

# Register your models here.

admin.site.register(ScanDocketEntry)
admin.site.register(Page)
admin.site.register(MagdecAnalysis)
admin.site.register(RoiCount)
