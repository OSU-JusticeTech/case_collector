from django.contrib import admin

from apps.fcmcclerk.models import Page

# Register your models here.


class PageAdmin(admin.ModelAdmin):
    date_hierarchy = "scraped_at"
    list_display = ["year","category","number","scraped_at","return_code"]
    list_filter = ["return_code","year","category"]
    search_fields = ["year","category","number"]

admin.site.register(Page, PageAdmin)
