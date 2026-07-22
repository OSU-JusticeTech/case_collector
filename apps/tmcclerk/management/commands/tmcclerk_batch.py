import logging
import os
import pathlib
import time
from datetime import timedelta, datetime

import requests
from bs4 import BeautifulSoup
from pprint import pprint
from copy import copy

from tqdm import tqdm

from django.core.management import BaseCommand


hdrs = {"Origin": "https://tools.tmc-clerk.com",
                "Referer": "https://tools.tmc-clerk.com/caseinformation/civilschedule/default.aspx",
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                # "X-Requested-With": "XMLHttpRequest",
                # "X-MicrosoftAjax": "Delta=true",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0",
                }

search_data = {
    "__EVENTTARGET": "",
    "__EVENTARGUMENT": "",
    "__VIEWSTATE": None,
    "__VIEWSTATEGENERATOR": None,
    "__VIEWSTATEENCRYPTED": "",
    "__EVENTVALIDATION": None,
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$TextVisits": "0",
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$ddlCR": "",
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$txtAttorneyLastName": "",
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$txtAttorneyNumber": "",
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$txtLastName": "",
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$txtFromDate": "11/03/2025",
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$txtToDate": "11/25/2025",
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$btnGetResults": "Search",
    # "__ncforminfo": None
}

details_data = {
    "__EVENTTARGET": "ctl00$ctl00$ContentPlaceHolder1$middle_content$CivilSchedule1$CivilScheduleGridView1$dvCase",
    "__EVENTARGUMENT": "LoadDetail$3",
    "__VIEWSTATE": None,
    "__VIEWSTATEGENERATOR": None,
    "__VIEWSTATEENCRYPTED": "",
    "__EVENTVALIDATION": None,
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$TextVisits": "1",
    "__ncforminfo": None
}

journal_data = {
    "__EVENTTARGET": "ctl00$ctl00$ContentPlaceHolder1$middle_content$CivilDetails1$LinkButton2",
    "__EVENTARGUMENT": "",
    "__VIEWSTATE": None,
    "__VIEWSTATEGENERATOR": None,
    "__VIEWSTATEENCRYPTED": "",
    "__EVENTVALIDATION": None,
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$TextVisits": "0",
    "__ncforminfo": None
}

image_data = {
    "__EVENTTARGET": "ctl00$ctl00$ContentPlaceHolder1$middle_content$CivilDetails1$JournalControl$gvCivilCaseJournal$ctl05$lbtnGetImage",
    "__EVENTARGUMENT": "",
    "__VIEWSTATE": None,
    "__VIEWSTATEGENERATOR": None,
    "__VIEWSTATEENCRYPTED": "",
    "__EVENTVALIDATION": None,
    "ctl00$ctl00$ContentPlaceHolder1$middle_content$TextVisits": "0",
    "__ncforminfo": None
}

def _extract_state(html):
    soup = BeautifulSoup(html, 'html.parser')
    form = soup.find('form', {"name": "aspnetForm"})
    form_data = {}
    for input_tag in form.find_all('input'):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            form_data[name] = value
    return form_data

def merge_state(state, data):
    submit_data = copy(data)
    for k, val in submit_data.items():  # - set(form_data.keys()):
        if val is None:
            submit_data[k] = state[k]
    return submit_data

def get_document(sess, state, link, path):
    # print(link)
    submit_data = merge_state(state, image_data)
    submit_data["__EVENTTARGET"] = link
    try:
        resp = sess.post("https://tools.tmc-clerk.com/caseinformation/civilschedule/default.aspx",
                         data=submit_data,
                         headers=hdrs)
        with open(path + link + ".pdf", "wb") as f:
            f.write(resp.content)
    except:
        with open(path + link + ".missing", "wb") as f:
            f.write(b"error")
    time.sleep(3)

def get_detail(dest, sess, state, argument, cno):

    submit_data = merge_state(state, details_data)

    path = dest+"/" + cno.replace(" ", "_") + "/"
    if os.path.exists(path):
        return
    os.makedirs(path, exist_ok=True)

    submit_data["__EVENTARGUMENT"] = argument
    resp = sess.post("https://tools.tmc-clerk.com/caseinformation/civilschedule/default.aspx", data=submit_data,
                     headers=hdrs)
    with open(path + "overview.html", "wb") as f:
        f.write(resp.content)

    state = _extract_state(resp.text)

    submit_data = merge_state(state, journal_data)
    resp = sess.post("https://tools.tmc-clerk.com/caseinformation/civilschedule/default.aspx", data=submit_data,
                     headers=hdrs)

    with open(path + "journal.html", "wb") as f:
        f.write(resp.content)

    state = _extract_state(resp.text)

    soup = BeautifulSoup(resp.text, 'html.parser')

    prnt = \
    soup.find("a", {"id": "ctl00_ctl00_ContentPlaceHolder1_middle_content_CivilDetails1_lnkPrintView"}).attrs[
        "href"]
    printable = sess.get("https://tools.tmc-clerk.com" + prnt, headers=hdrs)
    with open(path + "printable.html", "wb") as f:
        f.write(printable.content)

    for link in soup.find_all("a", {"class": "ScannedDocument"}):
        doclink = str(link).split("doPostBack('")[1].split("'")[0]
        if len(link.text) > 0:
            get_document(sess, state, doclink, path)
        # break
    # print(resp.content.decode())

def get_cases(dest, start, end):
    with requests.Session() as sess:
        response = sess.get("https://tools.tmc-clerk.com/caseinformation/civilschedule/default.aspx")
        state = _extract_state(response.text)
        # print(state)

        submit_data = merge_state(state, search_data)

        # pprint(submit_data)
        submit_data["ctl00$ctl00$ContentPlaceHolder1$middle_content$txtFromDate"] = start
        submit_data["ctl00$ctl00$ContentPlaceHolder1$middle_content$txtToDate"] = end

        search_result = sess.post("https://tools.tmc-clerk.com/caseinformation/civilschedule/default.aspx",
                                  data=submit_data,
                                  headers=hdrs)

        os.makedirs(dest, exist_ok=True)
        with open(dest+"/search_" + start.replace("/", "_"), "wb") as f:
            f.write(search_result.content)

        state = _extract_state(search_result.text)

        soup = BeautifulSoup(search_result.text, 'html.parser')
        for link in tqdm(soup.find_all("tr", {"class": "dataviewtable"})):
            detail = str(link).split("w1$dvCase','")[1].split("'")[0]
            cno = link.find("a").text
            if "CVG" in cno:
                get_detail(dest, sess, state, detail, cno)
            # break

class Command(BaseCommand):
    help = "Scrapes Toledo cases"

    def add_arguments(self, parser):
        parser.add_argument("destination", type=pathlib.Path)
        parser.add_argument("start_date", type=str,help="start date in YYYY-MM-DD")

    def handle(self, *args, **options):
        logging.info("start download")
        fn = str(options["destination"])
        print(fn)

        start = datetime.strptime(options["start_date"], "%Y-%m-%d")
        while start < datetime.now():
            end = start + timedelta(days=9)
            print(start, end)
            get_cases(fn, start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y"))
            start += timedelta(10)
