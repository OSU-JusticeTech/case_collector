from django.contrib import admin

from apps.cases.models import CourtCase, CaseSnapshot, Source, Party, Event, Disposition, Finance, DocketEntry

# Register your models here.

admin.site.register(Source)
admin.site.register(CourtCase)
admin.site.register(CaseSnapshot)
admin.site.register(Party)
admin.site.register(Event)
admin.site.register(Disposition)
admin.site.register(Finance)
admin.site.register(DocketEntry)