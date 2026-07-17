from django.contrib import admin
from django.db import models

from apps.violations.models import CodeViolation

# Register your models here.


class RecordTypeFilter(admin.SimpleListFilter):
    title = "record type"
    parameter_name = "record_type_path"

    def lookups(self, request, model_admin):
        values = (
            model_admin.get_queryset(request)
            .values_list("record_type", flat=True)
            .distinct()
        )
        all_prefixes = set()
        for v in values:
            if not v:
                continue
            parts = v.split("/")
            for i in range(1, len(parts) + 1):
                all_prefixes.add("/".join(parts[:i]))

        choices = []
        for prefix in sorted(all_prefixes):
            depth = prefix.count("/")
            label = ("—" * depth) + " " + prefix.split("/")[-1]
            choices.append((prefix, label))
        return choices

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(
                models.Q(record_type=val) | models.Q(record_type__startswith=val + "/")
            )
        return queryset


class CodeAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "record_number",
        "record_type",
        "address",
        "location",
        "status",
        "scraped_at",
    ]
    readonly_fields = ("location",)
    list_filter = [RecordTypeFilter, "status", "scraped_at"]
    date_hierarchy = "date"
    search_fields = ["date","record_number", "record_type", "address", "description", "status"]


admin.site.register(CodeViolation, CodeAdmin)
