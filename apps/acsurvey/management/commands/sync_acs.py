from datetime import datetime
import json
import logging

import requests
from django.conf import settings
from django.core.management import BaseCommand

from apps.acsurvey.models import RenterOccupiedZip


class Command(BaseCommand):
    help = "get ACS5 data"


    def handle(self, *args, **options):
        if settings.ACS_API_KEY is not None:
            for year in range(2011, datetime.now().date().year):
                print("acc year", year)
                if RenterOccupiedZip.objects.filter(year=year).count() > 0:
                    logging.info("%d already present", year)
                    continue
                res = requests.get(f"https://api.census.gov/data/{year}/acs/acs5?get=NAME,B25008_003E,B25008_003M&for=zip%20code%20tabulation%20area:*&key={settings.ACS_API_KEY}")
                if res.ok:
                    data = res.json()
                    header = data[0]
                    objs = []
                    for d in data[1:]:
                        row = dict(zip(header, d))
                        objs.append(RenterOccupiedZip(year=year, zip_code=row['zip code tabulation area'],
                                                      estimate=row['B25008_003E'],margin=row['B25008_003M']))
                    RenterOccupiedZip.objects.bulk_create(objs)
        else:
            logging.warning("no ACS_API_KEY provided")

