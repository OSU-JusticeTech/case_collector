import logging
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from django.utils import timezone

def load_case_csvs():

    if False:
        sess = requests.session()
        if settings.SCRAPE_PROXIES:
            sess.proxies.update(settings.SCRAPE_PROXIES)
        sess.headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0'}
        resp = sess.get("https://www.fcmcclerk.com/reports/evictions")
        if resp.ok:
            soup = BeautifulSoup(resp.content, "html.parser")
            for link in soup.find_all("a", {"target": "_blank"}):
                if ".csv" in link.attrs["href"]:
                    #print(link.attrs["href"])
                    logging.debug("fetching csv %s", link)
                    data = sess.get(f"https://www.fcmcclerk.com{link.attrs["href"]}")
                    assert data.ok
                    CasesLists.objects.create(content=data.content)
                    time.sleep(1)

    return


def decide_next_scrape():
    # we first try to get case numbers from csv:
    load_case_csvs()
    #print(resp.content)
