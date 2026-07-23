from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.db.models import Count

from apps.cases.models import (
    CourtCase,
    CaseSnapshot,
    Source,
    Party,
    Event,
    Disposition,
    Finance,
    DocketEntry,
    LatestOverview, DailyEvents,
)

# Register your models here.

admin.site.register(Source)


class CaseAdmin(admin.ModelAdmin):
    readonly_fields = ("snapshots", "scans")
    list_display = ["source", "case_number", "snapshot_count"]
    list_filter = ["source"]
    search_fields = ["case_number"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(snapshot_count=Count("casesnapshot"))

    def snapshot_count(self, obj):
        return obj.snapshot_count

    def snapshots(self, obj):
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:cases_casesnapshot_change", args=[o.id]),
                o,
            )
            for o in obj.casesnapshot_set.all()
        ]
        return (
            format_html_join("", "<li>{}</li>", ((link,) for link in links)) or "(None)"
        )

    def scans(self, obj):
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:nextgen_scandocketentry_change", args=[o.id]),
                o,
            )
            for o in obj.scandocketentry_set.all()
        ]
        return (
            format_html_join("", "<li>{}</li>", ((link,) for link in links)) or "(None)"
        )


admin.site.register(CourtCase, CaseAdmin)


def link_listing(objs, revname, attr=("title",)):
    links = [
        format_html(
            '<a href="{}">{}</a>',
            reverse(revname, args=[p.id]),
            ", ".join([str(getattr(p, a)) for a in attr]),
        )
        for p in objs
    ]
    return format_html_join("", "<li>{}</li>", ((link,) for link in links)) or "(None)"


class SnapshotAdmin(admin.ModelAdmin):
    readonly_fields = ("case", "parties", "events", "docket","disposition","finance")
    date_hierarchy = "created_at"

    def parties(self, obj):
        return link_listing(
            obj.party_set.all(),
            "admin:cases_party_change",
            attr=("side", "role", "name", "address", "city"),
        )

    def events(self, obj):
        return link_listing(
            obj.event_set.all(),
            "admin:cases_event_change",
            attr=("start", "result"),
        )

    def docket(self, obj):
        return link_listing(
            obj.docketentry_set.all(),
            "admin:cases_docketentry_change",
            attr=("date", "text"),
        )

    def disposition(self, obj):
        return link_listing(
            obj.disposition_set.all(),
            "admin:cases_disposition_change",
            attr=("date","code","status_date","status"),
        )

    def finance(self, obj):
        return link_listing(
            obj.finance_set.all(),
            "admin:cases_finance_change",
            attr=("application","owed","dismissed"),
        )



admin.site.register(CaseSnapshot, SnapshotAdmin)


class PartyAdmin(admin.ModelAdmin):
    readonly_fields = ("snapshot", "location")
    list_display = ["side", "role", "name", "address", "city", "state", "zip_code"]
    list_filter = ["side", "role", "state", "zip_code"]
    search_fields = ["name", "address", "city", "state"]


admin.site.register(Party, PartyAdmin)


class EventAdmin(admin.ModelAdmin):
    readonly_fields = ("snapshot",)
    list_display = ["event", "start", "end", "room", "judge", "result"]
    date_hierarchy = "start"
    list_filter = ["result", "event"]


admin.site.register(Event, EventAdmin)


class DispositionAdmin(admin.ModelAdmin):
    readonly_fields = ("snapshot",)
    list_display = ["date", "code", "judge", "status", "status_date"]
    date_hierarchy = "date"
    list_filter = ["code", "status"]


admin.site.register(Disposition, DispositionAdmin)


class FinanceAdmin(admin.ModelAdmin):
    readonly_fields = ("snapshot",)
    list_display = ["application", "owed", "paid", "dismissed", "balance"]
    list_filter = ["application"]


admin.site.register(Finance, FinanceAdmin)


class DocketAdmin(admin.ModelAdmin):
    readonly_fields = ("snapshot",)
    list_display = ["snapshot__case__case_number", "date", "text"]
    search_fields = ["snapshot__case__case_number", "date", "text"]
    list_filter = ["text"]
    date_hierarchy = "date"


admin.site.register(DocketEntry, DocketAdmin)


class LatestOverviewAdmin(admin.ModelAdmin):
    list_filter = ["earliest_docket", "code", "stptfatt_name"]
    search_fields = [
        "case_number",
        "stdef_name",
        "stdef_address",
        "full_address",
        "stptf_name",
        "stptf_address",
        "stptfatt_name",
        "stptfatt_address",
    ]

    def get_list_display(self, request):
        return [field.name for field in self.model._meta.fields]

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    # 2. Prevent adding or deleting
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(LatestOverview, LatestOverviewAdmin)

class DailyEventsAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return [field.name for field in self.model._meta.fields]

    # 2. Prevent adding or deleting
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(DailyEvents, DailyEventsAdmin)
