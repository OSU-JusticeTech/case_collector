import csv
import hashlib
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Generator
from unicodedata import category

import numpy as np
import requests
from bs4 import BeautifulSoup
from django.conf import settings

from django.core.cache import cache
from django.db.models import Q, OuterRef, Subquery, Max
from pydantic import BaseModel

from apps.cases.models import (
    Source,
    CourtCase,
    CaseSnapshot,
    Party,
    DocketEntry,
    Event,
    Finance,
    Disposition,
)
from apps.fcmcclerk.models import Page
from apps.fcmcclerk.parser import parse_case
from apps.fcmcclerk.pyschema import Case

CACHE_KEY = "fcmc_eviction_reports"

BASE_URL = "https://www.fcmcclerk.com"


class CSVcase:
    def __init__(self, data):
        self.data = data
        self.case_number = data["CASE_NUMBER"]
        self.digest = hashlib.sha256(str(data).encode()).hexdigest()


def load_case_csvs():

    cases = cache.get(CACHE_KEY)
    if cases is None:
        logging.info("refreshing CSVs")
        sess = requests.session()
        if settings.SCRAPE_PROXIES:
            sess.proxies.update(settings.SCRAPE_PROXIES)
        sess.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0"
        }
        resp = sess.get(f"{BASE_URL}/reports/evictions")
        cases = []
        if resp.ok:
            soup = BeautifulSoup(resp.content, "html.parser")
            for link in soup.find_all("a", {"target": "_blank"}):
                if ".csv" in link.attrs["href"]:
                    logging.info("fetching csv %s", link)
                    data = sess.get(f"{BASE_URL}{link.attrs["href"]}")
                    assert data.ok
                    inf = csv.DictReader(data.content.decode().splitlines())
                    for row in inf:
                        cases.append(CSVcase(row))
                    time.sleep(2)
        # print(cases)
        cache.set(CACHE_KEY, cases, timeout=20000)
    # print(len(cases))
    newest = sorted(cases, key=lambda x: x.case_number, reverse=True)
    # print(newest[:2])
    return newest


class ScrapeInstruction(BaseModel):
    case_number: str | None = None
    digest: str | None = None
    earliest: datetime | None = None
    restart: bool = False


def scrape_generator() -> Generator[ScrapeInstruction, None, None]:
    # we first try to get case numbers from csv:

    # val = cache.get(CACHE_KEY)
    # print(val)
    # cache.set(CACHE_KEY,42, timeout=10)
    csv_cases = load_case_csvs()
    proced = set()

    parts = csv_cases[0].case_number.split(" ")
    now_year = int(parts[0])
    cat = parts[1]
    existing_set = Page.objects.filter(year__gte=now_year - 2, category=cat).values_list(
        "year", "category", "number", "overview_digest"
    )
    logging.info("compare cases to list of %d existing", len(existing_set))
    cache_check_time = 0
    for ci, case in enumerate(csv_cases):
        if time.time() > cache_check_time + 60:
            cache_check_time = time.time()
            case_cache = cache.get(CACHE_KEY)
            logging.info("check if cache is None: %s", case_cache is None)
            if case_cache is None:
                yield ScrapeInstruction(restart=True, case_number=None)
        parts = case.case_number.split(" ")
        if ci % 100 == 0:
            logging.info(
                "processed %d of %d csv cases",
                ci,
                len(csv_cases),
            )

        year = int(parts[0])
        cat = parts[1]
        number = int(parts[2])
        proced.add((year, cat, number))

        if (year, cat, number, case.digest) in existing_set:
            continue

        yield ScrapeInstruction(case_number=case.case_number, digest=case.digest)

    logging.info("all cases from CSVs are done, pick the 300 cases with number years y y-1 y-2 that need urgent rescrape")

    # the parameters were fitted to the CDF of all Docket entries relative to the filing date
    def CDF(t, tau=14.3, beta=0.74):
        return 1 - np.exp(- (t / tau) ** beta)

    # Subquery: for a given (year, category, number), get the return_code
    # of the most recently scraped Page — regardless of what that return_code is.
    latest_return_code_sq = Page.objects.filter(
        year=OuterRef("year"),
        category=OuterRef("category"),
        number=OuterRef("number"),
    ).order_by("-scraped_at").values("return_code")[:1]

    latest_status_sq = Page.objects.filter(
        year=OuterRef("year"),
        category=OuterRef("category"),
        number=OuterRef("number"),
    ).order_by("-scraped_at").values("status")[:1]

    qs = (
        Page.objects.filter(category="CVG", year__gte=now_year - 2)
        .values("year", "category", "number", "filed")
        .annotate(
            latest_scraped_at=Max("scraped_at"),
            latest_return_code=Subquery(latest_return_code_sq),
            latest_status=Subquery(latest_status_sq),
        )
        .filter(latest_return_code__lt=300)
        .exclude(latest_status="CLOSED")
    )

    for op in sorted(
            qs,
            key=lambda x: CDF((datetime.now().date() - x["filed"]).days)
                          - CDF((x["latest_scraped_at"].date() - x["filed"]).days),
            reverse=True,
    )[:300]:

        logging.info("rescrape open case %s, filed %s last scraped at %s",f"{op["year"]} {op["category"]} {op["number"]:06d}", op["filed"], op["latest_scraped_at"])
        yield ScrapeInstruction(case_number=f"{op["year"]} {op["category"]} {op["number"]:06d}", digest="rescrape")

    logging.info("scrape the most urgent closed 30 cases")

    qs = (
        Page.objects.filter(category="CVG", year__gte=now_year - 2)
        .values("year", "category", "number", "filed")
        .annotate(
            latest_scraped_at=Max("scraped_at"),
            latest_return_code=Subquery(latest_return_code_sq),
            latest_status=Subquery(latest_status_sq),
        )
        .filter(latest_return_code__lt=300, latest_status="CLOSED")
    )

    for op in sorted(qs, key=lambda x: CDF((datetime.now().date() - x['filed']).days) - CDF(
            (x['latest_scraped_at'].date() - x['filed']).days), reverse=True)[:30]:
        logging.info("rescrape closed case %s, filed %s last scraped at %s",
                     f"{op["year"]} {op["category"]} {op["number"]:06d}", op["filed"], op["latest_scraped_at"])
        yield ScrapeInstruction(case_number=f"{op["year"]} {op["category"]} {op["number"]:06d}", digest="rescrape")

    yield ScrapeInstruction(restart=True, case_number=None)


class CaseNotFound(Exception):
    pass


class ErrorFetchingOverview(Exception):
    pass

def extract_overview(html):
    soup = BeautifulSoup(html, "html.parser")

    # Find the Overview heading
    overview = soup.find(id="overview")

    # Find the first table after the Overview anchor
    table = overview.find_next("table")

    metadata_td = table.find_all("td")[1]
    text = metadata_td.get_text(separator=" ", strip=True)

    status = re.search(r"Status:\s*(.+?)(?=\s+Filed:|$)", text).group(1).strip()
    filed_str = re.search(r"Filed:\s*([0-9/]+)", text).group(1)

    filed = datetime.strptime(filed_str, "%m/%d/%Y").date()

    return status, filed


def scrape_detail(instruction: ScrapeInstruction):
    case_number = instruction.case_number
    digest = instruction.digest
    sess = requests.session()

    parts = case_number.split(" ")
    year = int(parts[0])
    cat = parts[1]
    number = int(parts[2])

    if settings.SCRAPE_PROXIES:
        sess.proxies.update(settings.SCRAPE_PROXIES)
    sess.headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0"
    }
    result = sess.get(f"{BASE_URL}/case/search")
    token = (
        result.content.decode()
        .split('<input name="_token" type="hidden" value="')[1]
        .split('"')[0]
    )

    overview = sess.post(
        f"{BASE_URL}/case/search/results",
        data={"_token": token, "case_number": case_number},
    )
    if b"<li>No Results Found</li>" in overview.content:
        print("not a case")
        pg = Page.objects.create(
            year=year,
            category=cat,
            number=number,
            content="",
            return_code=410,
            overview_digest=digest,
        )
        return pg

    casetokens = list(
        map(
            lambda x: x.split('"')[0],
            overview.content.decode().split(
                'input name="case_id" type="hidden" value="'
            )[1:],
        )
    )
    if len(casetokens) == 0:
        print("no case tokens found, make 410 page")
        pg = Page.objects.create(
            year=year,
            category=cat,
            number=number,
            content="",
            return_code=410,
            overview_digest=digest,
        )
        return pg
    case = sess.post(
        f"{BASE_URL}/case/view", data={"_token": token, "case_id": casetokens[0]}
    )
    try:
        status, filed = extract_overview(case.content.decode())
    except:
        status, filed = None, None
    pg = Page.objects.create(
        year=year,
        category=cat,
        number=number,
        content=case.content.decode(),
        return_code=case.status_code,
        overview_digest=digest,
        status=status,
        filed=filed,
    )
    return pg


def compute_state_hash(obj: Case) -> bytes:
    payload = obj.model_dump_json().encode("utf-8")
    return hashlib.sha256(payload).digest()


def create_snapshot_if_changed(
    source: Source, scraped_at: datetime, parse_case: Case
) -> tuple[CaseSnapshot, bool]:  # or int epoch
    """
    Returns (snapshot_id, created_new).
    Creates a new snapshot ONLY if its hash differs from the latest snapshot's hash.
    """
    new_hash = compute_state_hash(parse_case)

    current_case, _ = CourtCase.objects.get_or_create(
        case_number=parse_case.case_number, source=source
    )

    current_snapshot = current_case.casesnapshot_set.order_by("created_at").last()

    if current_snapshot is not None and current_snapshot.state_hash == new_hash:
        # No change since latest snapshot → skip
        logging.warning(
            "case with equal snapshot exists, skipping %s", parse_case.case_number
        )
        return current_snapshot, False

        # 3) Insert new snapshot (no unique constraint on (case_id, hash))
    snap = CaseSnapshot.objects.create(case=current_case, state_hash=new_hash)

    for party_data in parse_case.parties + parse_case.attorneys:
        Party.objects.create(
            side=party_data.type_.value,
            name=party_data.name,
            address=(
                "\n".join(party_data.address)
                if hasattr(party_data, "address") and party_data.address
                else ""
            ),
            city=party_data.city if hasattr(party_data, "city") else "",
            state=party_data.state if hasattr(party_data, "state") else "",
            zip_code=party_data.zip_ if hasattr(party_data, "zip_") else "",
            role=party_data.role if hasattr(party_data, "role") else "",
            snapshot=snap,
        )

    # Save docket entries
    for attr, cls, exclude in [
        ("docket", DocketEntry, {"scan"}),
        ("events", Event, set()),
        ("finances", Finance, set()),
        ("dispositions", Disposition, set()),
    ]:
        for sub_data in getattr(parse_case, attr):
            cls.objects.create(
                **sub_data.model_dump(exclude=exclude),
                snapshot=snap,
            )

    snap.created_at = scraped_at
    snap.save()

    return snap, True


def parse_page(pg: Page):
    case = parse_case(pg.content)
    src, _ = Source.objects.get_or_create(name="FCMC")
    snap, created = create_snapshot_if_changed(
        source=src,
        scraped_at=pg.scraped_at,  # or int epoch
        parse_case=case,
    )
    pg.snapshot = snap
    pg.save()
