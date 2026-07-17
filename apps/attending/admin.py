from django.contrib import admin

from apps.attending.models import CheckinSheet, DocketSessionState

# Register your models here.

admin.site.register(CheckinSheet)
admin.site.register(DocketSessionState)
