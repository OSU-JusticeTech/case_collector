import logging
import time
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import connection

from apps.fcmcclerk.tasks import (
    scrape_detail,
    parse_page,
    scrape_generator,
    ScrapeInstruction,
)


def scrape_and_parse(instr: ScrapeInstruction):
    pg = scrape_detail(instr)
    if pg.return_code == 200:
        logging.info("parse and add %s", pg)
        try:
            parse_page(pg)
        except Exception as e:
            logging.error("page %s could not be parsed: %s", pg, e.__repr__())
            pg.return_code = 401
            pg.save()

    time.sleep(15)

def refresh_latest_overview():
    if connection.vendor != "sqlite":
        # Postgres (or other vendors that support materialized views)
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY latest_overview")

class Command(BaseCommand):
    help = "Scrapes a FCMC case"

    def add_arguments(self, parser):
        parser.add_argument("case_number", nargs="*", type=str)

    def handle(self, *args, **options):
        logging.info("start scraping")
        scrape_cases = options.get("case_number", [])
        if len(scrape_cases) > 0:
            print("opt", scrape_cases)
            for case_number in scrape_cases:
                scrape_and_parse(ScrapeInstruction(case_number=case_number))
            return


        while True:
            logging.info("refresh materialized")
            refresh_latest_overview()
            for cno in scrape_generator():
                logging.info("next case %s", cno)
                if cno.restart:
                    logging.info("cache expired, restart")
                    break
                if cno.earliest is not None:
                    logging.info("done, resume at %s", cno.earliest)
                    while datetime.now() < cno.earliest:
                        time.sleep(10)
                    break

                scrape_and_parse(cno)
