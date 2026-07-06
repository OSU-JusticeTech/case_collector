import time
from datetime import datetime
import logging

from django.core.management import BaseCommand

from apps.fcmcclerk.tasks import ScrapeInstruction
from apps.nextgen.tasks import scrape_pdfs, scrape_generator
from apps.violations.tasks import get_csv


class Command(BaseCommand):
    help = "Scrapes violations"

    def add_arguments(self, parser):
        parser.add_argument("day", nargs="?", type=str)

    def handle(self, *args, **options):
        logging.info("start scraping")

        get_csv(datetime(2026, 6, 1))
        return
        while True:
            for cno in scrape_generator():
                logging.info("next case %s", cno)
                if cno.restart:
                    logging.info("restart")
                    break
                if cno.earliest is not None:
                    logging.info("done, resume at %s", cno.earliest)
                    while datetime.now() < cno.earliest:
                        time.sleep(10)
                    break

                scrape_pdfs(cno)
