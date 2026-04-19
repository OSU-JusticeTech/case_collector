from typing import Union, Any

from bs4 import BeautifulSoup
import datetime

from pydantic import TypeAdapter

from zoneinfo import ZoneInfo

from .pyschema import (
    Case,
    SideName,
    SideAddress,
    Attorney,
    FakeAttorney,
    RunningAttorney,
    PublicAttorney,
    Event,
    Finance,
)
from .pyschema import Disposition, DocketEntry

Party = TypeAdapter(Union[SideName, SideAddress])
AnyAtt = TypeAdapter(Attorney | FakeAttorney | RunningAttorney | PublicAttorney)


def parse_parties(soup) -> list[Union[SideName, SideAddress]]:
    table = soup.find("table", {"id": "pty_table"})
    # Initialize a list to store the party data
    parties = []
    # Iterate through each row in the table
    rows = table.find_all("tr")
    current_party = None
    for row in rows:
        cells = row.find_all("td")
        title = None
        for cell in cells:
            if cell.get("rowspan") is not None:
                party_id = cell.get_text(strip=True)
                if current_party is not None:
                    parties.append(current_party)
                current_party = {"party_number": party_id}
            if cell.get("class") == ["title"]:
                title = cell.get_text(strip=True)
            if cell.get("class") == ["data"] and title is not None and current_party is not None:
                data = cell.decode_contents().replace(
                    "<br/>", "\n"
                )  # .get_text(strip=True)
                current_party[title] = data
                title = None

    # Don't forget to append the last party's data
    if current_party:
        parties.append(current_party)

    p_objs = []
    for p in parties:
        sanp = {k.lower(): v for k, v in p.items()}
        if "State/Zip" in p:
            sanp.update(
                {
                    "state": p["State/Zip"].split("/")[0],
                    "zip": p["State/Zip"].split("/")[1],
                    "address": p.get("Address", "").split("\n"),
                }
            )
        p_objs.append(Party.validate_python(sanp))

    return p_objs


def parse_attorneys(
    soup,
) -> list[Attorney | FakeAttorney | RunningAttorney | PublicAttorney]:
    table = soup.find("table", {"id": "atty_table"})

    attorneys = []
    a_objs = []
    if table is not None:
        # Extract attorney details

        # Iterate through each row in the table
        rows = table.find_all("tr")

        current_attorney = None
        title = None
        assert len(rows) % 2 == 0
        for rid, row in enumerate(rows):
            cells = row.find_all("td")
            if rid % 2 == 0 and current_attorney is not None:
                attorneys.append(current_attorney)
                current_attorney = None
            if current_attorney is None:
                current_attorney = {}
            for cell in cells:
                if cell.get("class") == ["title"]:
                    title = cell.get_text(strip=True)
                if cell.get("class") == ["data"] and title is not None:
                    data = cell.decode_contents().replace(
                        "<br/>", "\n"
                    )  # .get_text(strip=True)
                    current_attorney[title] = data
                    title = None
        if current_attorney is not None:
            attorneys.append(current_attorney)

        for p in attorneys:
            att_vals = {
                **{k.lower()[:-1]: v for k, v in p.items()},
                **{
                    "type": p["Party Type:"].split(" - ")[0],
                    "role": p["Party Type:"].split(" - ")[1],
                    "address": p["Address:"].split("\n"),
                    "city": p["City/St/Zip:"].split(",")[0],
                    "state": p["City/St/Zip:"].split(",")[1].split(" ")[1],
                    "zip": p["City/St/Zip:"].split(",")[1].split(" ")[2],
                },
            }
            a_objs.append(AnyAtt.validate_python(att_vals))

    return a_objs


def parse_dispositions(soup):
    table = soup.find("table", {"id": "dsp_table"})

    disp = []
    if table is not None:
        # Extract the data rows
        header = table.find_all("tr")[0]
        columns = [a.get_text() for a in header.find_all("td", class_="title")]

        for row in table.find_all("tr")[1:]:
            data = [
                a.decode_contents().replace("<br/>", "\n")
                for a in row.find_all("td", class_="data")
            ]
            # print(data)
            d = dict(zip(columns, data))
            raw: dict[str,Any] = {
                **{k.lower(): v for k, v in d.items()},
                **{
                    "code": d["Disposition Code"],
                    "date": (
                        None
                        if d["Disposition Date"] == ""
                        else datetime.datetime.strptime(
                            d["Disposition Date"], "%m/%d/%Y"
                        ).date()
                    ),
                    "status_date": datetime.datetime.strptime(
                        d["Status Date"], "%m/%d/%Y"
                    ).date(),
                },
            }
            disp.append(Disposition(**raw))
    return disp


def parse_docket(soup) -> list[DocketEntry]:
    table = soup.find("table", {"id": "dkt_table"})
    # Extract the data rows
    docket = []
    current_entry = None
    d_obj = []
    if table is not None:
        for row in table.find_all("tr")[
            1:
        ]:  # Skip the first row which contains the headers
            cells = row.find_all("td")
            if row.get("class") == ["dkt_text"] and current_entry is not None:
                current_entry["extra"] = cells[1].decode_contents()
            else:
                if current_entry is not None:
                    docket.append(current_entry)
                current_entry = {
                    "Date": datetime.datetime.strptime(
                        cells[0].get_text(strip=True), "%m/%d/%Y"
                    ),
                    "Text": cells[1].get_text(strip=True),
                    "Amount": cells[2].get_text(strip=True),
                    "Balance": cells[3].get_text(strip=True),
                }
        if current_entry is not None:
            docket.append(current_entry)

        d_obj = [
            DocketEntry(
                **{
                    **{k.lower(): v for k, v in p.items()},
                    **{
                        "balance": (
                            p["Balance"][1:].replace(",", "")
                            if p["Balance"] != ""
                            else None
                        ),
                        "amount": (
                            p["Amount"][1:].replace(",", "")
                            if p["Amount"] != ""
                            else None
                        ),
                    },
                }
            )
            for p in docket
        ]
    return d_obj


def parse_events(soup) -> list[Event]:
    table = soup.find("table", {"id": "evnt_table"})

    e_obj = []
    if table is not None:
        # Extract the data rows
        header = table.find_all("tr")[0]
        columns = [a.get_text() for a in header.find_all("td", class_="title")]

        tz_ohio = ZoneInfo("America/New_York")

        events = []
        for row in table.find_all("tr")[1:]:
            data = [
                a.decode_contents().replace("<br/>", "\n")
                for a in row.find_all("td", class_="data")
            ]
            # print(data)
            events.append(dict(zip(columns, data)))
        e_obj = [
            Event(
                **{
                    **{k.lower(): v for k, v in e.items()},
                    **{
                        "room": e["Ct.Rm."],
                        "start": datetime.datetime.strptime(
                            e["Date"] + e["Start"], "%m/%d/%Y%I:%M %p"
                        ).replace(tzinfo=tz_ohio),
                        "end": datetime.datetime.strptime(
                            e["Date"] + e["End"], "%m/%d/%Y%I:%M %p"
                        ).replace(tzinfo=tz_ohio),
                    },
                }
            )
            for e in events
        ]
    return e_obj


def parse_finances(soup) -> list[Finance]:
    table = soup.find("table", {"id": "dkt_appl_table"})
    f_obs = []
    if table is not None:
        # Extract the data rows
        header = table.find_all("tr")[0]
        columns = [a.get_text() for a in header.find_all("td", class_="title")]

        costs = []
        for row in table.find_all("tr")[1:]:
            data = [
                a.decode_contents().replace("<br/>", "\n")
                for a in row.find_all("td", class_="data")
            ]
            # print(data)
            costs.append(dict(zip(columns, data)))
        f_obs = [
            Finance(
                **{
                    **{
                        k[7:].lower(): (
                            v[1:].replace(",", "")
                            if v.startswith("$")
                            else v.replace("<b>", "").replace("</b>", "")
                        )
                        for k, v in e.items()
                    },
                    **{
                        "balance": e["Balance"][1:].replace(",", ""),
                    },
                }
            )
            for e in costs
        ]

    return f_obs


def parse_case(html):
    soup = BeautifulSoup(html, "html.parser")

    case_number = soup.select_one("header.page-header h1 > span").get_text(strip=True)

    parties = parse_parties(soup)
    # print(parties)

    attorneys = parse_attorneys(soup)
    # print(attorneys)

    dispositions = parse_dispositions(soup)
    # print(dispositions)

    docket = parse_docket(soup)
    # print(docket)

    events = parse_events(soup)

    finances = parse_finances(soup)

    return Case(
        case_number=case_number,
        parties=parties,
        docket=docket,
        attorneys=attorneys,
        dispositions=dispositions,
        finances=finances,
        events=events,
    )
