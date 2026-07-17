import time
from datetime import datetime, timedelta
import logging

from django.core.management import BaseCommand

from apps.fcmcclerk.tasks import ScrapeInstruction
from apps.nextgen.tasks import scrape_pdfs, scrape_generator
from apps.violations.models import CodeViolation
from apps.violations.tasks import get_csv


class Command(BaseCommand):
    help = "Scrapes violations"

    def add_arguments(self, parser):
        parser.add_argument("day", nargs="?", type=str)

    def handle(self, *args, **options):
        logging.info("start scraping")

        #get_csv(datetime(2026, 6, 1))

        if CodeViolation.objects.count() == 0:
            start = datetime(2025, 1, 1).date()
        else:
            latest = CodeViolation.objects.all().order_by("-date")[0]
            start = latest.date
        logging.info("start on day %s", start )
        while True:
            if start + timedelta(days=1) >= datetime.now().date():
                logging.info("don't scrape today, wait")
                time.sleep(100)
                continue
            start += timedelta(days=1)

            logging.info("scrape %s", start)
            get_csv(start)
            time.sleep(12)
