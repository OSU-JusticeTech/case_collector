import datetime
import logging
import time

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.base import ContentFile

from apps.cases.models import CourtCase
from apps.fcmcclerk.pyschema import DocketEntry
from apps.nextgen.models import ScanDocketEntry, Page

BASE_URL = "https://secure.fcmcclerk.com"


def parse_scan_docket(soup):
    table = soup.find("table", {"id": "dkt_table"})
    # Extract the data rows
    docket = []
    if table is not None:
        tbody = table.find("tbody")

        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            text = cells[1].decode_contents()
            pdf = cells[4].find("a", {"title": "View Document"})
            pdf_link = None
            if pdf is not None:
                pdf_link = pdf.attrs["href"]
            docket.append(
                (
                    DocketEntry(
                        date=datetime.datetime.strptime(
                            cells[0].get_text(strip=True), "%m/%d/%Y"
                        ),
                        text=text,
                    ),
                    pdf_link,
                )
            )
    return docket


def parse_fields(form):
    fields = {}
    for inp in form.find_all("input"):
        fields[inp.attrs["name"]] = inp.attrs.get("value")
    return fields


def extract_fields(content):
    soup = BeautifulSoup(content, "html.parser")
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
    fields.update(
        {"email": settings.NEXTGEN_EMAIL, "password": settings.NEXTGEN_PASSWORD}
    )
    # print(fields)

    sess.post(f"{BASE_URL}/nextgen/login", data=fields)

    search = sess.get(f"{BASE_URL}/nextgen/case/search")

    fields = extract_fields(search.content.decode())

    # print(fields)
    fields["case_number"] = case_number

    time.sleep(1)

    listing = sess.post(f"{BASE_URL}/nextgen/case/search/results", data=fields)

    # print(listing.content.decode())

    soup = BeautifulSoup(listing.content.decode(), "html.parser")
    allforms = soup.find_all("form")
    form = None
    for f in allforms:
        if f["action"].endswith("/nextgen/case/view"):
            form = f
            break
    if form is None:
        logging.error("case not found %s", case_number)
        # os.makedirs(path, exist_ok=True)
        # with open(f"{path}/not-found.error", "w") as f:
        #    pass
        return
    case_data = parse_fields(form)

    time.sleep(1)

    case = sess.post(f"{BASE_URL}/nextgen/case/view", data=case_data)

    soup = BeautifulSoup(case.content.decode(), "html.parser")

    dkt = parse_scan_docket(soup)
    # print(dkt)
    case_obj = CourtCase.objects.get(case_number=case_number, source__name="FCMC")
    for entry, link in dkt:
        entry_obj, created = ScanDocketEntry.objects.get_or_create(
            case=case_obj, date=entry.date, text=entry.text
        )
        if created and link is not None:
            file = sess.get(link)
            # print(file.headers)
            if file.headers["Content-Type"] != "application/pdf":
                cf = ContentFile(file.content, name="non-pdf.html")
                entry_obj.scan = cf
                entry_obj.save()
                continue
            save_name = (
                file.headers["Content-Disposition"]
                .split("filename=")[1]
                .replace('"', "")
            )
            cf = ContentFile(file.content, name=save_name)
            entry_obj.scan = cf
            entry_obj.filename = save_name
            entry_obj.save()
            time.sleep(5)

    Page.objects.create(
        case = case_obj,
        content=case.content.decode(),
        return_code=case.status_code,
    )