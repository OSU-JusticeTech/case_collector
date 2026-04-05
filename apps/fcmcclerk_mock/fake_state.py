from collections import Counter
from datetime import datetime, timezone, date, timedelta
import random

import numpy as np

from apps.fcmcclerk_mock.pyschema import Case

EVICTION_FIXTURE = {}  # will be populated on startup


def generate_year(year, total_cases=500):

    CASE_WEEKEND_RATIO = 0.0194938
    CASE_WORKDAY_RATIO = 0.912828
    # rest is sealed or other category
    vals = np.random.zipf(1.3, 110) - 1
    while sum(vals) > total_cases * CASE_WEEKEND_RATIO:
        max_pos = np.argmax(vals)
        vals[max_pos] = np.random.zipf(1.3) - 1
    random.shuffle(
        vals
    )  # argmax always takes the first, accumulating non-zero values towards the end
    print(sum(vals))

    day = date(year, 1, 1)
    weekenddayofyear = 0
    cases = []
    case_number = 0
    while day.year == year:
        if day.weekday() < 5:
            # 261 workdays per year
            mean = total_cases * CASE_WORKDAY_RATIO / 261
            std = mean / 2.32
            no_cases = max(round(np.random.normal(mean, std)), 0)
        else:
            no_cases = vals[weekenddayofyear]
            weekenddayofyear += 1

        cats = random.choices(
            ["CVE", "CVF", "CVG", "CVR"], weights=[629, 37087, 24018, 202], k=no_cases
        )
        for cat in cats:
            while random.random() < 1 - CASE_WORKDAY_RATIO - CASE_WEEKEND_RATIO:
                # print("skip", case_number)
                case_number += 1
            cases.append(Case.generate(f"{year} {cat} {case_number:06d}", filed=day))
            case_number += 1

        day += timedelta(days=1)
    #print(cases)
    print("generated for year", year, len(cases))
    return cases


def generate_random_fixture(months=12):
    """

      1291 weekend cases of 25k
      Create a dict of fake eviction reports for the last `months` months.
      URL -> content

      2025 distribution:
          629 2025_CVE
    37087 2025_CVF
    24018 2025_CVG
      202 2025_CVR
      total: 61936
      max assigned number: 066226

      worked 321 days of the year
    """

    fixture = []
    now = datetime.now(timezone.utc)
    for i in range(now.year-2,now.year+1):
        fixture += generate_year(i)
    return fixture
