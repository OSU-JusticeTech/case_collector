import csv
import logging
import time
import requests
from bs4 import BeautifulSoup
from django.conf import settings

from django.core.cache import cache

from apps.fcmcclerk.models import Page

CACHE_KEY = "fcmc_eviction_reports"

BASE_URL = "https://www.fcmcclerk.com"


def load_case_csvs():

    cases = cache.get(CACHE_KEY)
    if cases is None:
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
                    logging.debug("fetching csv %s", link)
                    data = sess.get(f"{BASE_URL}{link.attrs["href"]}")
                    assert data.ok
                    inf = csv.DictReader(data.content.decode().splitlines())
                    for row in inf:
                        cases.append(row)
                    time.sleep(1)
        # print(cases)
        cache.set(CACHE_KEY, cases, timeout=80000)
    print(len(cases))
    newest = sorted(cases, key=lambda x: x.get("CASE_NUMBER"), reverse=True)
    print(newest[:2])
    return newest


def decide_next_scrape():
    # we first try to get case numbers from csv:

    # val = cache.get(CACHE_KEY)
    # print(val)
    # cache.set(CACHE_KEY,42, timeout=10)
    csv_cases = load_case_csvs()
    for case in csv_cases:
        parts = case["CASE_NUMBER"].split(" ")

        print("case:")
        year = int(parts[0])
        cat = parts[1]
        number = int(parts[2])
        existing = Page.objects.filter(year=year,category=cat, number=number)
        if existing.exists():
            continue
        return case["CASE_NUMBER"]

    # print(resp.content)


class CaseNotFound(Exception):
    pass

class ErrorFetchingOverview(Exception):
    pass


def scrape_detail(case_number):
    sess = requests.session()
    # sess.proxies.update(proxies)
    sess.headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0'}
    result = sess.get(f"{BASE_URL}/case/search")
    token = result.content.decode().split('<input name="_token" type="hidden" value="')[1].split('"')[0]

    overview = sess.post(f"{BASE_URL}/case/search/results",
                         data={'_token': token, "case_number": case_number})
    if b"<li>No Results Found</li>" in overview.content:
        print("not a case")
        time.sleep(8)
        raise CaseNotFound()

    casetokens = list(map(lambda x: x.split('"')[0],
                          overview.content.decode().split('input name="case_id" type="hidden" value="')[1:]))
    if len(casetokens) == 0:
        raise ErrorFetchingOverview()
    case = sess.post(f"{BASE_URL}/case/view", data={'_token': token, "case_id": casetokens[0]})
    parts = case_number.split(" ")
    year = int(parts[0])
    cat = parts[1]
    number = int(parts[2])
    Page.objects.create(year=year, category=cat, number=number,content=case.content, return_code=case.status_code)

