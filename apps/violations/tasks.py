import csv
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db.models import Max, OuterRef, Subquery

from apps.violations.models import CodeViolation

hdrs = {"Origin":"https://portal.columbus.gov",
        "Referer":"https://portal.columbus.gov/permits/Cap/CapHome.aspx?module=Enforcement",
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "X-Requested-With": "XMLHttpRequest",
        "X-MicrosoftAjax": "Delta=true",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0",
       }

post_data = {l[0]: "=".join(l[1:]) if len(l)>1 else "" for l in map(lambda x: x.split("="), """ctl00$ScriptManager1=ctl00$PlaceHolderMain$updatePanel|ctl00$PlaceHolderMain$btnNewSearch
ACA_CS_FIELD=c790cb6fe1d84377ae5faa29683e4ec2
__EVENTTARGET=ctl00$PlaceHolderMain$btnNewSearch
__EVENTARGUMENT
__LASTFOCUS
__VIEWSTATEGENERATOR=589EB791
__VIEWSTATEENCRYPTED
ctl00$HeaderNavigation$hdnShoppingCartItemNumber
ctl00$HeaderNavigation$hdnShowReportLink=N
ctl00$PlaceHolderMain$addForMyPermits$collection=rdoExistCollection
ctl00$PlaceHolderMain$addForMyPermits$ddlMyCollection
ctl00$PlaceHolderMain$addForMyPermits$txtName
ctl00$PlaceHolderMain$addForMyPermits$txtDesc
ctl00$PlaceHolderMain$ddlSearchType=0
ctl00$PlaceHolderMain$generalSearchForm$txtGSNumber$ChildControl0
ctl00$PlaceHolderMain$generalSearchForm$txtGSNumber$ctl00_PlaceHolderMain_generalSearchForm_txtGSNumber_ChildControl0_watermark_exd_ClientState
ctl00$PlaceHolderMain$generalSearchForm$txtGSNumber$ChildControl1
ctl00$PlaceHolderMain$generalSearchForm$txtGSNumber$ctl00_PlaceHolderMain_generalSearchForm_txtGSNumber_ChildControl1_watermark_exd_ClientState
ctl00$PlaceHolderMain$generalSearchForm$ddlGSDirection
ctl00$PlaceHolderMain$generalSearchForm$txtGSStreetName
ctl00$PlaceHolderMain$generalSearchForm$ddlGSStreetSuffix
ctl00$PlaceHolderMain$generalSearchForm$txtGSCity
ctl00$PlaceHolderMain$generalSearchForm$ddlGSState$State1
ctl00$PlaceHolderMain$generalSearchForm$txtGSAppZipSearchPermit
ctl00$PlaceHolderMain$generalSearchForm$txtGSAppZipSearchPermit_ZipFromAA=0
ctl00$PlaceHolderMain$generalSearchForm$txtGSAppZipSearchPermit_zipMask
ctl00$PlaceHolderMain$generalSearchForm$txtGSAppZipSearchPermit_ext_ClientState
ctl00$PlaceHolderMain$generalSearchForm$txtGSParcelNo
ctl00$PlaceHolderMain$generalSearchForm$txtGSPermitNumber
ctl00$PlaceHolderMain$generalSearchForm$txtGSStartDate=05/15/2025
ctl00$PlaceHolderMain$generalSearchForm$txtGSStartDate_ext_ClientState
ctl00$PlaceHolderMain$generalSearchForm$txtGSEndDate=05/16/2025
ctl00$PlaceHolderMain$generalSearchForm$txtGSEndDate_ext_ClientState
ctl00$PlaceHolderMain$hfASIExpanded
ctl00$PlaceHolderMain$txtHiddenDate
ctl00$PlaceHolderMain$txtHiddenDate_ext_ClientState
ctl00$PlaceHolderMain$dgvPermitList$lblNeedReBind
ctl00$PlaceHolderMain$dgvPermitList$gdvPermitList$hfSaveSelectedItems
ctl00$PlaceHolderMain$dgvPermitList$inpHideResumeConf
ctl00$PlaceHolderMain$hfGridId
ctl00$HDExpressionParam
Submit=Submit
__ASYNCPOST=true""".split("\n"))}

def parse_aspnet_partial_response(response: str) -> list[dict[str, str]]:
    results = []
    i = 0
    length = len(response)

    def read_until(delim='|'):
        nonlocal i
        start = i
        while i < length and response[i] != delim:
            i += 1
        part = response[start:i]
        i += 1  # skip delimiter
        return part

    # Skip header: "1|#||"
    if response.startswith("1|#||4"):
        i = len("1|#||4")

    while i < length:
        token = read_until()
        if token == '':
            continue
        elif token.isdigit():
            # length-prefixed block, like: 4|27|updatePanel|id|<div>...</div>|
            data_length = int(token)
            command = read_until()
            target = read_until()
            data = response[i:i + data_length]
            i += data_length + 1  # +1 for the trailing '|'
            #print("meta", data_length, command, target, data[:100])
            results.append({
                'command': command,
                'target': target,
                'data': data
            })
            #print("i end", i, response[i-100: i+100])
            #break
        else:
            # Unknown format — skip or handle gracefully
            pass

    return results

BASE_URL = "https://portal.columbus.gov"

def get_csv(day):
    sess = requests.session()

    if settings.SCRAPE_PROXIES:
        sess.proxies.update(settings.SCRAPE_PROXIES)
    sess.headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0"
    }
    response = sess.get(f"{BASE_URL}/permits/Cap/CapHome.aspx?module=Enforcement")
    soup = BeautifulSoup(response.content, 'html.parser')
    form = soup.find('form')
    form_data = {}
    for input_tag in form.find_all('input'):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            form_data[name] = value

    for k in set(post_data.keys()) - set(form_data.keys()):
        form_data[k] = post_data[k]

    form_data["ctl00$PlaceHolderMain$generalSearchForm$txtGSStartDate"] = day.strftime("%m/%d/%Y")  # "05/15/2025"
    form_data["ctl00$PlaceHolderMain$generalSearchForm$txtGSEndDate"] = day.strftime("%m/%d/%Y")  # "05/15/2025"

    resp = sess.post("https://portal.columbus.gov/permits/Cap/CapHome.aspx?module=Enforcement", data=form_data,
                     headers=hdrs)

    parsed = parse_aspnet_partial_response(resp.content.decode())
    new_viewstate = None
    for p in parsed:
        if p["command"] == "hiddenField" and p["target"] == "__VIEWSTATE":
            new_viewstate = p["data"]

    form_data["__VIEWSTATE"] = new_viewstate

    form_data[
        "ctl00$ScriptManager1"] = "ctl00$PlaceHolderMain$dgvPermitList$updatePanel|ctl00$PlaceHolderMain$dgvPermitList$gdvPermitList$gdvPermitListtop4btnExport"
    form_data["__EVENTTARGET"] = "ctl00$PlaceHolderMain$dgvPermitList$gdvPermitList$gdvPermitListtop4btnExport"


    resp = sess.post("https://portal.columbus.gov/permits/Cap/CapHome.aspx?module=Enforcement", data=form_data,
                     headers=hdrs)
    table = sess.get("https://portal.columbus.gov/Permits/Export2CSV.ashx?flag=1248",
                     headers=hdrs)

    inf = csv.DictReader(table.content.decode().splitlines())
    data = []
    for row in inf:
        prep = {k.lower().replace(" ", "_"): v for k, v in row.items() if k != ""}
        prep["date"] = datetime.strptime(prep["date"], "%m/%d/%Y").date()
        data.append(prep)


    latest_scraped_at = (
        CodeViolation.objects
        .filter(record_number=OuterRef("record_number"))
        .order_by("-scraped_at")
        .values("scraped_at")[:1]
    )

    record_numbers = [r["record_number"] for r in data]

    latest_qs = CodeViolation.objects.filter(record_number__in=record_numbers,
                                             scraped_at=Subquery(latest_scraped_at))

    latest_by_record = {obj.record_number: obj for obj in latest_qs}

    for prep in data:
        latest = latest_by_record.get(prep["record_number"])
        if latest and all(getattr(latest, f) == v for f, v in prep.items()):
            continue
        CodeViolation.objects.create(**prep)

    time.sleep(10)



