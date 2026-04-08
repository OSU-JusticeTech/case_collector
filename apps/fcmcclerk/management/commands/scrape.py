import logging
import time

from django.core.management.base import BaseCommand
from apps.fcmcclerk.tasks import decide_next_scrape, scrape_detail, parse_page


class Command(BaseCommand):
    help = "Scrapes a FCMC case"

    def handle(self, *args, **options):
        while True:
            cno = decide_next_scrape()
            logging.info("next case %s", cno)
            pg = scrape_detail(cno)
            if pg.return_code == 200:
                logging.info("parse and add %s", pg)
                parse_page(pg)
            time.sleep(15)