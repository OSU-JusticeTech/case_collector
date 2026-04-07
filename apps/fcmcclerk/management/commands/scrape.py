from django.core.management.base import BaseCommand
from apps.fcmcclerk.tasks import decide_next_scrape, scrape_detail


class Command(BaseCommand):
    help = "Scrapes a FCMC case"

    def handle(self, *args, **options):
        cno = decide_next_scrape()
        scrape_detail(cno)
