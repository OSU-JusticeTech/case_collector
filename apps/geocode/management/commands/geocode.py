import logging
import time

from django.core.management.base import BaseCommand

from apps.cases.models import Party
from apps.geocode.tasks import geo
from apps.violations.models import CodeViolation


class Command(BaseCommand):
    help = "geocodes Party addresses"

    def handle(self, *args, **options):
        logging.info("start geocoding")

        last_unfindable = {Party: set(),
                           CodeViolation: set()}
        while True:
            total_coded = 0
            for cls in last_unfindable:
                d = geo(cls, skip=last_unfindable[cls])
                last_unfindable[cls].update(d["unfindable"])
                logging.info("geocoding new %s addresses: %d", cls, d["geocoded_count"])
                total_coded += d["geocoded_count"]
            if total_coded == 0:
                time.sleep(6 * 3600)
            time.sleep(10)
