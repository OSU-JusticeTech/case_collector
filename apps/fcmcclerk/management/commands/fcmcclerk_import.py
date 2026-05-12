import logging
import os.path
import pathlib
from glob import glob
from tqdm import tqdm

from django.core.management.base import BaseCommand
from datetime import datetime

from apps.fcmcclerk.models import Page
from apps.fcmcclerk.parser import parse_case
from apps.fcmcclerk.tasks import parse_page


class Command(BaseCommand):
    help = "Imports FCMC case htmls"

    def add_arguments(self, parser):
        parser.add_argument("scrape_time", type=str)
        parser.add_argument("dir_glob", type=str)

    def handle(self, *args, **options):
        logging.info("start import")
        scrape_date = datetime.fromisoformat(options["scrape_time"])
        print(scrape_date)
        files = glob(options["dir_glob"])
        print("importing ", len(files))
        for fn in tqdm(files):
            if os.path.isfile(fn):
                content = open(fn).read()
                case = parse_case(content)
                # print(case.case_number)

                parts = case.case_number.split(" ")
                year = int(parts[0])
                cat = parts[1]
                number = int(parts[2])
                pg, created = Page.objects.get_or_create(
                    year=year,
                    category=cat,
                    number=number,
                    content=content,
                    return_code=203,
                )
                if created:
                    pg.scraped_at = scrape_date
                    pg.save()
                    parse_page(pg)
                else:
                    print(case.case_number, "already imported")
