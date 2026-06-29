import logging
import time

from django.core.management.base import BaseCommand

from apps.geocode.tasks import geo


class Command(BaseCommand):
    help = "geocodes Party addresses"

    def handle(self, *args, **options):
        logging.info("start geocoding")

        last_unfindable = set()
        while True:
            d = geo(skip=last_unfindable)
            print("geocoding new addresses", d["geocoded_count"])
            if d["geocoded_count"] == 0:
                time.sleep(6 * 3600)
            last_unfindable.update(d["unfindable"])
            time.sleep(10)
