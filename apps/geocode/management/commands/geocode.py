import logging
from django.core.management.base import BaseCommand

from apps.geocode.tasks import geo


class Command(BaseCommand):
    help = "Scrapes a FCMC case"

    def add_arguments(self, parser):
        parser.add_argument("case_number", nargs="*", type=str)

    def handle(self, *args, **options):
        logging.info("start scraping")
        scrape_cases = options.get("case_number", [])
        if len(scrape_cases) > 0:
            print("opt", scrape_cases)
            return

        geo()
        print("bla")
