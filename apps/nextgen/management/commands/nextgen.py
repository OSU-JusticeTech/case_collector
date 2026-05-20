import time
from datetime import datetime
import logging

from django.core.management import BaseCommand

from apps.fcmcclerk.tasks import ScrapeInstruction
from apps.nextgen.tasks import scrape_pdfs, scrape_generator


class Command(BaseCommand):
    help = "Scrapes a nextgen case"

    def add_arguments(self, parser):
        parser.add_argument("case_number", nargs="*", type=str)

    def handle(self, *args, **options):
        logging.info("start scraping")
        scrape_cases = options.get("case_number", [])
        if len(scrape_cases) > 0:
            print("opt", scrape_cases)
            for case_number in scrape_cases:
                scrape_pdfs(ScrapeInstruction(case_number=case_number))
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
