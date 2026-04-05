from django.core.management.base import BaseCommand
from apps.fcmcclerk.tasks import decide_next_scrape


class Command(BaseCommand):
    help = "Scrapes a FCMC case"

    def handle(self, *args, **options):
        decide_next_scrape()
