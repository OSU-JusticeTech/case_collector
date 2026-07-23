import csv
import logging
import pathlib
from datetime import datetime

from django.core.management import BaseCommand
from tqdm import tqdm

from apps.cases.models import Source
from apps.fcmcclerk.pyschema import Sides, Case, DocketEntry, Disposition
from apps.fcmcclerk.tasks import create_snapshot_if_changed


def make_name(last, first, company):
    if last == "" and first == "" and company != "":
        return company
    elif company == "":
        return f'{last}, {first}'
    print(last, first, company)
    raise Exception("both name and company")


class Command(BaseCommand):
    help = "Imports reduced table extract"

    def add_arguments(self, parser):
        parser.add_argument("file", type=pathlib.Path)

    def handle(self, *args, **options):
        logging.info("start import")
        fn: pathlib.Path = options["file"]
        purefile = fn.name
        fieldnames = []
        for row in csv.reader(open(fn)):
            for hdr in row:
                if hdr in fieldnames:
                    hdr += "_"
                fieldnames.append(hdr)
            break
        print(fieldnames)

        clerk_cases = {}
        latest_dates = {}

        with open(fn) as f:
            f.readline()  # discard existing header
            for case in tqdm(csv.DictReader(f, fieldnames=fieldnames)):
                case["filed"] = datetime.strptime(case['FILED DATE'], "%d.%m.%Y").date()
                latest_date = case["filed"]
                if case['DISP DATE'] != "":
                    case["disp"] = datetime.strptime(case['DISP DATE'], "%d.%m.%Y").date()
                    latest_date = case["disp"]

                PLNTF = {k: v for k, v in {"address": [case["PLNTF ADDRESS"], case["PLNTF ADDRESS 2"]],
                                           "type": Sides.PLAINTIFF,
                                           "name": make_name(case["PLNTF L NAME"], case["PLNTF F NAME"],
                                                             case["PLNTF COMPANY"]),
                                           "city": case["CITY"],
                                           "state": case["STATE"],
                                           "zip": case["ZIP"]}.items() if v != ""}
                DFNDT = {k: v for k, v in {"address": [case["DFNDT ADDRESS"], case["DFNDT ADDRESS 2"]],
                                           "type": Sides.DEFENDANT,
                                           "name": make_name(case["DFNDT L NAME"], case["DFNDT F NAME"],
                                                             case["DFNDT COMPANY NAME"]),
                                           "city": case["CITY_"],
                                           "state": case["STATE_"],
                                           "zip": case["ZIP_"]}.items() if v != ""}
                parsed = Case(case_number=case["CASE NUMBER"],
                              parties=[PLNTF, DFNDT],
                              docket=[DocketEntry(text="PETITION IN FE&D FILED", date=case["filed"])],
                              attorneys=[],
                              finances=[],
                              events=[],
                              dispositions=[Disposition(code=case['DISP DEF'], judge="", date=case.get("disp"),
                                                        status="CLOSED" if "disp" in case else "OPEN")])
                if parsed.case_number in clerk_cases:
                    assert clerk_cases[parsed.case_number].model_dump() == parsed.model_dump()

                clerk_cases[parsed.case_number] = parsed
                latest_dates[parsed.case_number] = latest_date

                #break

        print(len(clerk_cases))

        src, _ = Source.objects.get_or_create(name="FCMC")
        for case in tqdm(clerk_cases.values()):
            create_snapshot_if_changed(src,latest_dates[case.case_number],case,purefile.encode())
