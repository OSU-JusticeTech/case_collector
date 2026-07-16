from django.contrib import admin
from django.utils.html import format_html

from apps.fcmcclerk.models import Page

# Register your models here.


class PageAdmin(admin.ModelAdmin):
    date_hierarchy = "scraped_at"
    readonly_fields = ("snapshot", "content_preview")
    list_display = [
        "year",
        "category",
        "number",
        "scraped_at",
        "return_code",
        "status",
        "filed",
    ]
    list_filter = ["return_code", "year", "category", "status", "filed"]
    search_fields = ["year", "category", "number"]

    def content_preview(self, obj):
        if obj.content:
            # Using srcdoc inside an iframe keeps the HTML sandbox-isolated
            return format_html(
                '<iframe srcdoc="{}" style="width: 800px; height: 500px; border: 1px solid #ccc; border-radius: 4px;"></iframe>',
                obj.content,
            )
        return "No content"


admin.site.register(Page, PageAdmin)
