import csv
import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Generator
from unicodedata import category

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from django.core.cache import cache
from django.db.models import Q
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
    case_number: str
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
    for ci, case in enumerate(csv_cases):
        case_cache = cache.get(CACHE_KEY)
        if case_cache is None:
            yield ScrapeInstruction(restart=True, case_number="")
        parts = case.case_number.split(" ")
        if ci % 100 == 0:
            logging.info("processed %d of %d csv cases", ci, len(csv_cases))

        year = int(parts[0])
        cat = parts[1]
        number = int(parts[2])
        proced.add((year, cat, number))
        existing = Page.objects.filter(
            year=year, category=cat, number=number, overview_digest=case.digest
        )

        newer = (
            Page.objects.filter(category=cat)
            .filter(Q(year=year, number__gt=number) | Q(year__gt=year))
            .values_list("year", "category", "number")
        )
        missed = set(newer) - proced
        # print("newer", sorted(set(newer)))
        # print("missed", missed)
        for first in missed:
            case_cache = cache.get(CACHE_KEY)
            if case_cache is None:
                yield ScrapeInstruction(restart=True, case_number="")
            if Page.objects.filter(
                category=first[1], year=first[0], number=first[2], return_code=404
            ).exists():
                proced.add(first)
                continue
            print("missed cases before current one and not yet scraped", missed)
            yield ScrapeInstruction(
                case_number=f"{first[0]} {first[1]} {first[2]:06d}", digest="missing"
            )

        if existing.exists():
            continue

        yield ScrapeInstruction(case_number=case.case_number, digest=case.digest)

    # print(resp.content)
    yield ScrapeInstruction(earliest=datetime.now()+timedelta(hours=6), case_number="")


class CaseNotFound(Exception):
    pass


class ErrorFetchingOverview(Exception):
    pass


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
            return_code=404,
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
        print("no case tokens found, make 404 page")
        pg = Page.objects.create(
            year=year,
            category=cat,
            number=number,
            content="",
            return_code=404,
            overview_digest=digest,
        )
        return pg
    case = sess.post(
        f"{BASE_URL}/case/view", data={"_token": token, "case_id": casetokens[0]}
    )
    pg = Page.objects.create(
        year=year,
        category=cat,
        number=number,
        content=case.content.decode(),
        return_code=case.status_code,
        overview_digest=digest,
    )
    return pg


def compute_state_hash(obj: Case) -> bytes:
    payload = obj.model_dump_json().encode("utf-8")
    return hashlib.sha256(payload).digest()


def create_snapshot_if_changed(
    source: Source, page: Page, parse_case: Case
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
    for attr, cls in [
        ("docket", DocketEntry),
        ("events", Event),
        ("finances", Finance),
        ("dispositions", Disposition),
    ]:
        for sub_data in getattr(parse_case, attr):
            cls.objects.create(
                **sub_data.model_dump(),
                snapshot=snap,
            )

    return snap, True


def parse_page(pg: Page):
    case = parse_case(pg.content)
    src, _ = Source.objects.get_or_create(name="FCMC")
    create_snapshot_if_changed(
        source=src,
        page=pg,  # or int epoch
        parse_case=case,
    )
