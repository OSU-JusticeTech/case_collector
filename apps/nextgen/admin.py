from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from apps.nextgen.models import ScanDocketEntry, Page, MagdecAnalysis, RoiCount

# Register your models here.


class ScanDocketEntryAdmin(admin.ModelAdmin):
    readonly_fields = ("case", "analyses", "filename", "download_link")
    list_display = ["case", "date", "text", "filename"]
    search_fields = ["case__case_number", "date", "text", "filename"]
    exclude = ("magdec_analyses",)

    def download_link(self, obj):
        if obj and obj.scan:
            url = reverse("nextgen:download_scan", args=[obj.pk])
            return format_html('<a class="button" href="{}">📥 Download Scan</a>', url)
        return "No File"

    def analyses(self, obj):
        links = [
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:nextgen_magdecanalysis_change", args=[o.id]),
                o,
            )
            for o in obj.magdec_analyses.all()
        ]
        return (
            format_html_join("", "<li>{}</li>", ((link,) for link in links)) or "(None)"
        )

admin.site.register(ScanDocketEntry, ScanDocketEntryAdmin)


class PageAdmin(admin.ModelAdmin):
    readonly_fields = ("case", "content_preview")
    list_display = ["case", "scraped_at", "return_code"]
    date_hierarchy = "scraped_at"
    search_fields = ["case__case_number"]

    def content_preview(self, obj):
        if obj.content:
            # Using srcdoc inside an iframe keeps the HTML sandbox-isolated
            return format_html(
                '<iframe srcdoc="{}" style="width: 800px; height: 500px; border: 1px solid #ccc; border-radius: 4px;"></iframe>',
                obj.content.replace("secure.fcmcclerk.com", ""),
            )
        return "No content"


admin.site.register(Page, PageAdmin)


class MagdecAnalysisAdmin(admin.ModelAdmin):
    list_display = ["page_number", "diff_sum", "good_matches", "created_at"]
    readonly_fields = ("docket_entry",)

    def docket_entry(self, obj):
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

admin.site.register(MagdecAnalysis, MagdecAnalysisAdmin)


class RoiCountAdmin(admin.ModelAdmin):
    readonly_fields = ("result",)
    list_display = ["result", "roi_id", "count_nonwhite"]


admin.site.register(RoiCount, RoiCountAdmin)
