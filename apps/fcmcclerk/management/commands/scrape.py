from django.core.management.base import BaseCommand
from apps.fcmcclerk.tasks import decide_next_scrape, scrape_detail, parse_page


class Command(BaseCommand):
    help = "Scrapes a FCMC case"

    def handle(self, *args, **options):
        cno = decide_next_scrape()
        pg = scrape_detail(cno)
        if pg.return_code == 200:
            parse_page(pg)