import logging
import time

import requests
from bs4 import BeautifulSoup
from django.conf import settings

BASE_URL = "https://secure.fcmcclerk.com"


def parse_fields(form):
    fields = {}
    for inp in form.find_all("input"):
        fields[inp.attrs["name"]] = inp.attrs.get("value")
    return fields


def extract_fields(content):
    soup = BeautifulSoup(content, 'html.parser')
    form = soup.find("form")
    return parse_fields(form)

def scrape_pdfs(case_number):

    sess = requests.session()

    if settings.SCRAPE_PROXIES:
        sess.proxies.update(settings.SCRAPE_PROXIES)
    sess.headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0"
    }

    result = sess.get(f"{BASE_URL}/nextgen/login")

    time.sleep(1)

    fields = extract_fields(result.content.decode())
    fields.update({
        "email": settings.NEXTGEN_EMAIL,
        "password": settings.NEXTGEN_PASSWORD
    })
    print(fields)

    sess.post(f"{BASE_URL}/nextgen/login", data=fields)

    search = sess.get(f"{BASE_URL}/nextgen/case/search")

    fields = extract_fields(search.content.decode())

    print(fields)
    fields['case_number'] = case_number

    time.sleep(1)

    listing = sess.post(f"{BASE_URL}/nextgen/case/search/results", data=fields)

    # print(listing.content.decode())

    soup = BeautifulSoup(listing.content.decode(), 'html.parser')
    form = soup.find("form", {"action": f"{BASE_URL}/nextgen/case/view"})
    if form is None:
        logging.error("case not found %s", case_number)
        #os.makedirs(path, exist_ok=True)
        #with open(f"{path}/not-found.error", "w") as f:
        #    pass
        return
    case_data = parse_fields(form)
    print(case_data)

    time.sleep(1)

    case = sess.post(f"{BASE_URL}/nextgen/case/view", data=case_data)

    # print(case.content.decode())

    #with open(f"{path}/overview.html", "wb") as f:
    #    f.write(case.content)

    soup = BeautifulSoup(case.content.decode(), 'html.parser')
    for file_link in soup.find_all("a", {"title": "View Document"}):
        link = file_link.attrs["href"]
        file = sess.get(link)
        print(file.headers)
        if file.headers['Content-Type'] != 'application/pdf':
            #with open(f"{path}/{link.split("?q=")[1][9:20]}.html", "wb") as dest:
            #    dest.write(file.content)
                continue
        save_name = file.headers["Content-Disposition"].split("filename=")[1].replace('"', "")
        print(save_name)
        #with open(f"{path}/{save_name}", "wb") as f:
            #f.write(file.content)

        time.sleep(5)