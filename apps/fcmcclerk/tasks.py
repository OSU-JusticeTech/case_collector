import csv
import logging
import time
import requests
from bs4 import BeautifulSoup
from django.conf import settings

from django.core.cache import cache

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
    return


def decide_next_scrape():
    # we first try to get case numbers from csv:

    # val = cache.get(CACHE_KEY)
    # print(val)
    # cache.set(CACHE_KEY,42, timeout=10)
    load_case_csvs()
    # print(resp.content)
