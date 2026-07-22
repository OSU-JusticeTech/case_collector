import logging
import pathlib
import tarfile
from datetime import UTC, datetime

from django.core.management import BaseCommand
from tqdm import tqdm

from apps.tmcclerk.models import Page


class Command(BaseCommand):
    help = "Scrapes a nextgen case"

    def add_arguments(self, parser):
        parser.add_argument("archive", type=pathlib.Path)

    def handle(self, *args, **options):
        logging.info("start imort")
        fn = options["archive"]
        print(fn)
        tar = tarfile.open(fn, "r")
        for tarinfo in tqdm(tar):
            if tarinfo.name.endswith("printable.html"):

                #print(tarinfo.name, "is", tarinfo.size, "bytes in size and is ")
                dt = datetime.fromtimestamp(tarinfo.mtime, UTC)
                #print(dt)
                dirname = tarinfo.name.split("/")[-2]
                parts = dirname.split("-")
                year_end = int(parts[1])
                if year_end > 50:
                    year = year_end+1900
                else:
                    year = year_end+2000
                number = int(parts[2])
                cat = parts[0]

                content = tar.extractfile(tarinfo).read().decode()

                pg, created = Page.objects.get_or_create(
                    year=year,
                    category=cat,
                    number=number,
                    content=content,
                    return_code=203,
                )

                if created:
                    pg.scraped_at = dt
                    pg.save()
                else:
                    print(dirname, "already imported")
        tar.close()