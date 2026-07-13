import logging
import os.path
import pathlib
from glob import glob

from bs4 import BeautifulSoup
from tqdm import tqdm

from django.core.management.base import BaseCommand
from datetime import datetime, UTC

from apps.fcmcclerk.models import Page
from apps.fcmcclerk.parser import parse_case, get_case_number
from apps.fcmcclerk.tasks import parse_page


class Command(BaseCommand):
    help = "Imports FCMC case htmls"

    def add_arguments(self, parser):
        parser.add_argument("scrape_time", nargs="?", type=str)
        parser.add_argument("dir_glob", type=str)
        parser.add_argument("--no-parse", action="store_false", dest="parse")

    def handle(self, *args, **options):
        logging.info("start import")
        if options["scrape_time"] is None:
            logging.info("use filestat time")
            scrape_date = None
        else:
            scrape_date = datetime.fromisoformat(options["scrape_time"])
        print(scrape_date)
        files = glob(options["dir_glob"])
        logging.info("importing %d files", len(files))
        for fn in tqdm(files):
            if os.path.isfile(fn):
                content = open(fn).read()
                soup = BeautifulSoup(content, "html.parser")
                case_number = get_case_number(soup)
                # print(case_number)

                parts = case_number.split(" ")
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
                    if scrape_date is None:
                        mtime = pathlib.Path(fn).stat().st_mtime
                        dt = datetime.fromtimestamp(mtime, UTC)
                        pg.scraped_at = dt
                    else:
                        pg.scraped_at = scrape_date
                    pg.save()
                    if options["parse"]:
                        parse_page(pg)
                else:
                    print(case_number, "already imported")
