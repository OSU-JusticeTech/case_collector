import logging
import time
from datetime import datetime

from django.core.management.base import BaseCommand
from apps.fcmcclerk.tasks import scrape_detail, parse_page, scrape_generator


class Command(BaseCommand):
    help = "Scrapes a FCMC case"

    def handle(self, *args, **options):
        logging.info("start scraping")
        while True:
            for cno in scrape_generator():
                logging.info("next case %s", cno)
                if cno.restart:
                    logging.info("cache expired, restart")
                    break
                if cno.earliest is not None:
                    logging.info("done, resume at %s", cno.earliest)
                    while datetime.now() < cno.earliest:
                        time.sleep(10)
                pg = scrape_detail(cno)
                if pg.return_code == 200:
                    logging.info("parse and add %s", pg)
                    parse_page(pg)
                time.sleep(15)
