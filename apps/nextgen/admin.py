from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.nextgen.models import ScanDocketEntry, Page, MagdecAnalysis, RoiCount

# Register your models here.

class ScanDocketEntryAdmin(admin.ModelAdmin):
    readonly_fields = ("case","magdec_analyses","filename", "download_link")
    list_display = ["case", "date", "text", "filename"]
    search_fields = ["case", "date", "text", "filename"]

    def download_link(self, obj):
        if obj and obj.scan:
            url = reverse('nextgen:download_scan', args=[obj.pk])
            return format_html('<a class="button" href="{}">📥 Download Scan</a>', url)
        return "No File"


admin.site.register(ScanDocketEntry, ScanDocketEntryAdmin)

class PageAdmin(admin.ModelAdmin):
    readonly_fields = ("case","content_preview")
    list_display = ["case", "scraped_at", "return_code"]
    date_hierarchy = "scraped_at"
    search_fields = ["case"]

    def content_preview(self, obj):
        if obj.content:
            # Using srcdoc inside an iframe keeps the HTML sandbox-isolated
            return format_html(
                '<iframe srcdoc="{}" style="width: 800px; height: 500px; border: 1px solid #ccc; border-radius: 4px;"></iframe>',
                obj.content.replace("secure.fcmcclerk.com","")
            )
        return "No content"

admin.site.register(Page, PageAdmin)

class MagdecAnalysisAdmin(admin.ModelAdmin):
     list_display = ["page_number", "diff_sum", "good_matches", "created_at"]

admin.site.register(MagdecAnalysis, MagdecAnalysisAdmin)


class RoiCountAdmin(admin.ModelAdmin):
    readonly_fields = ("result",)
    list_display = ["result", "roi_id", "count_nonwhite"]

admin.site.register(RoiCount, RoiCountAdmin)
