import logging
import time

from django.core.management.base import BaseCommand

from apps.geocode.tasks import geo


class Command(BaseCommand):
    help = "geocodes Party addresses"

    def handle(self, *args, **options):
        logging.info("start geocoding")

        while True:
            num = geo()
            if num == 0:
                time.sleep(6 * 3600)
            time.sleep(10)
