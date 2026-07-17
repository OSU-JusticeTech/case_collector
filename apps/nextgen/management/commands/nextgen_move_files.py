import logging
import os.path

from django.conf import settings
from django.core.management import BaseCommand
from tqdm import tqdm

from apps.nextgen.models import ScanDocketEntry, nextgen_filenames


class Command(BaseCommand):
    help = "moves files to new structure"

    def handle(self, *args, **options):
        logging.info("start scraping")

        for se in tqdm(ScanDocketEntry.objects.all().exclude(scan="")):
            cur_dir = os.path.dirname(se.scan.name)
            supposed = nextgen_filenames(se, se.filename)
            supp_dir = os.path.dirname(supposed)
            cur_name = os.path.basename(se.scan.name)
            if cur_dir == supp_dir:
                continue

            #print(se.case)
            #print(se.scan)
            #print(cur_dir)
            #print(supposed)
            #print(cur_name)

            #print(os.path.join(settings.MEDIA_ROOT, se.scan.name))
            #print("new", os.path.join(settings.MEDIA_ROOT, supp_dir, cur_name))
            #print()
            try:
                os.makedirs(os.path.join(settings.MEDIA_ROOT, supp_dir),exist_ok=True)
                os.rename(os.path.join(settings.MEDIA_ROOT, se.scan.name),
                          os.path.join(settings.MEDIA_ROOT, supp_dir, cur_name) ) # we can't take the supposed name because we may need a unique suffix

                se.scan.name = os.path.join(supp_dir, cur_name)
                se.save()
            except Exception as e:
                print("unable to move", se, e.__repr__())
            #break

