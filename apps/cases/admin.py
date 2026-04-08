from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from apps.cases.models import CourtCase, CaseSnapshot, Source, Party, Event, Disposition, Finance, DocketEntry

# Register your models here.

admin.site.register(Source)

class CaseAdmin(admin.ModelAdmin):
    readonly_fields = ("snapshots",)

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
    readonly_fields = ("parties","docket")

    def parties(self, obj):
        return link_listing(obj.party_set.all(), "admin:cases_party_change", attr=("side", "role", "name", "address", "city"))
    def docket(self, obj):
        return link_listing(obj.docketentry_set.all(), "admin:cases_docketentry_change",
                            attr=("date", "text"))

admin.site.register(CaseSnapshot, SnapshotAdmin)
admin.site.register(Party)
admin.site.register(Event)
admin.site.register(Disposition)
admin.site.register(Finance)
admin.site.register(DocketEntry)