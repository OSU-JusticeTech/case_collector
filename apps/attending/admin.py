from django.contrib import admin

from apps.attending.models import CheckinSheet, DocketSessionState, PresenceCase

# Register your models here.

admin.site.register(CheckinSheet)
admin.site.register(DocketSessionState)

class PresenceCaseAdmin(admin.ModelAdmin):
    readonly_fields = ("case",)

admin.site.register(PresenceCase, PresenceCaseAdmin)
