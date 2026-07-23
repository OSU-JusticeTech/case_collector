import logging
import pathlib
import tarfile
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from django.core.management import BaseCommand
from tqdm import tqdm

from apps.tmcclerk.models import Page, SearchResult


class Command(BaseCommand):
    help = "Scrapes a nextgen case"

    def add_arguments(self, parser):
        parser.add_argument("archive", type=pathlib.Path)
        parser.add_argument("--ignore-detail", action="store_false", dest="detail")

    def handle(self, *args, **options):
        logging.info("start imort")
        fn = options["archive"]
        print(fn)
        tar = tarfile.open(fn, "r")
        searches = []
        tz_ohio = ZoneInfo("America/New_York")

        for tarinfo in tqdm(tar):
            if tarinfo.name.endswith("printable.html"):
                if not options["detail"]:
                    continue
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
            elif "/search_" in tarinfo.name:
                #print(tarinfo)
                searches.append(tarinfo.name)
                content = tar.extractfile(tarinfo).read().decode()
                dt = datetime.fromtimestamp(tarinfo.mtime, UTC)
                #print(dt)
                #print(content)
                start = datetime.strptime(tarinfo.name[-len("07_20_2021"):],"%m_%d_%Y").replace(tzinfo=tz_ohio)
                #print(start)
                se, created = SearchResult.objects.get_or_create(
                    search_start=start,
                    content = content,
                    return_code = 203,
                )
                if created:
                    se.scraped_at = dt
                    se.save()
                else:
                    print(start, "already imported")
                #break
        tar.close()
        print(len(searches))