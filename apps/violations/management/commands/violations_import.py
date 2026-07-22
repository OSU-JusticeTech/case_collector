import csv
import logging
import pathlib
from datetime import datetime
from glob import glob

from django.core.management import BaseCommand

from apps.violations.models import CodeViolation


class Command(BaseCommand):
    help = "Imports Code Violation CSVs"

    def add_arguments(self, parser):
        parser.add_argument("folder", type=pathlib.Path)
        parser.add_argument("scrape_time", type=str)

    def handle(self, *args, **options):
        logging.info("start import")
        fn = str(options["folder"])
        scrape_date = datetime.fromisoformat(options["scrape_time"])
        files = glob(fn+"/*.csv")
        for f in files:
            print(f)
            with open(f) as fd:
                inf = csv.DictReader(fd)
                data = []
                for row in inf:
                    prep = {k.lower().replace(" ", "_"): v for k, v in row.items() if k != ""}
                    prep["date"] = datetime.strptime(prep["date"], "%m/%d/%Y").date()
                    data.append(prep)

                for prep in data:
                    cobj = CodeViolation.objects.create(**prep)
                    cobj.scraped_at = scrape_date
                    cobj.save()

