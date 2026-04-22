import logging

from django.core.management import BaseCommand

from apps.nextgen.tasks import scrape_pdfs

class Command(BaseCommand):
    help = "Scrapes a nextgen case"

    def handle(self, *args, **options):
        logging.info("start scraping")

        scrape_pdfs("2024 CVG 006892")
