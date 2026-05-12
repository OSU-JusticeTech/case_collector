import copy
import hashlib
from datetime import datetime, timezone, date, timedelta

import numpy as np

from apps.fcmcclerk.pyschema import Case, Disposition

EVICTION_FIXTURE = []  # will be populated on startup


def fixture_at(req_date):
    new_cases = []
    CASE_SEAL_RATIO = 0.3  # guessed
    for case in EVICTION_FIXTURE:
        if case.docket[-1].date <= req_date:
            h = hashlib.sha256(
                b"".join(
                    [p.model_dump_json().encode() for p in case.parties]
                    + [case.case_number.encode()]
                )
            ).digest()
            int_from_bytes = int.from_bytes(h[:8], "big")
            float_val = int_from_bytes / 2**64

            # Use next bytes for int
            int_val = int.from_bytes(h[8:12], "big") % 20

            if float_val < CASE_SEAL_RATIO:
                # print("sealing case", case.case_number, "after days", int_val)
                if case.docket[-1].date + timedelta(days=int_val) < req_date:
                    # print("sealed")
                    continue

            cp: Case = copy.deepcopy(case)
            cp.docket = []
            for de in case.docket:
                if de.date <= req_date:
                    cp.docket.append(de)
            cp.dispositions = []
            for ev in case.dispositions:
                if ev.date <= req_date:
                    cp.dispositions.append(ev)
            if len(cp.dispositions) == 0:
                filed = cp.docket[-1].date
                cp.dispositions.append(
                    Disposition(
                        status="OPEN",
                        status_date=filed,
                        code="UNDISPOSED",
                        judge="ADMINISTRATIVE",
                    )
                )
            new_cases.append(cp)

    return new_cases


def generate_year(year, total_cases=500):

    CASE_WEEKEND_RATIO = 0.0194938
    CASE_WORKDAY_RATIO = 0.912828

    rng = np.random.default_rng(year + 1234567)

    # rest is sealed or other category
    weekend_caseloads = rng.zipf(1.3, 110) - 1
    while sum(weekend_caseloads) > total_cases * CASE_WEEKEND_RATIO:
        max_pos = np.argmax(weekend_caseloads)
        weekend_caseloads[max_pos] = rng.zipf(1.3) - 1
    # argmax always takes the first, accumulating non-zero values towards the end, so we need to reshuffle
    rng.shuffle(weekend_caseloads)
    # print("total weekend cases", sum(weekend_caseloads))

    day = date(year, 1, 1)
    weekenddayofyear = 0
    cases = []
    case_number = 1
    while day.year == year:
        if day.weekday() < 5:
            # 261 workdays per year
            mean = total_cases * CASE_WORKDAY_RATIO / 261
            std = mean / 2.32
            no_cases = max(round(rng.normal(mean, std)), 0)
        else:
            no_cases = weekend_caseloads[weekenddayofyear]
            weekenddayofyear += 1

        case_type_distribution = np.array([629, 37087, 24018, 202])
        cats = rng.choice(
            ["CVE", "CVF", "CVG", "CVR"],
            no_cases,
            p=case_type_distribution / case_type_distribution.sum(),
        )
        for cat in cats:
            while rng.random() < 1 - CASE_WORKDAY_RATIO - CASE_WEEKEND_RATIO:
                # print("skip", case_number)
                # this is most likely a sealed case
                case_number += 1
            cases.append(Case.generate(f"{year} {cat} {case_number:06d}", filed=day))
            case_number += 1

        day += timedelta(days=1)
    # print(cases)
    print("generated for year", year, len(cases))
    return cases


def generate_random_fixture(months=12):
    """

    1291 weekend cases of 25k

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
    now = datetime(2026, 5, 12)
    for i in range(now.year - 2, now.year + 1):
        fixture += generate_year(i)
    return fixture
