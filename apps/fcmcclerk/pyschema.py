import random
from datetime import timedelta
from turtledemo.clock import jump

import numpy as np
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Literal, Union
import datetime
from enum import Enum
from decimal import Decimal

state_abbreviations = [
    "AE",  # Armed Forces Europe
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CANADA",
    "CN",  # also Canada
    "CO",
    "CT",
    "DE",
    "DC",  # Washington
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "PR",  # Puerto Rico
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "",
]


class Sides(Enum):
    PLAINTIFF = "PLAINTIFF"
    RD_PLAINTIFF = "3RD PARTY PLAINTIFF"
    CROSS_PLAINTIFF = "CROSS CLAIM PLANTIFF"
    DEFENDANT = "DEFENDANT"
    RD_DEFENDANT = "3RD PARTY DEFENDANT"
    CROSS_DEFENDANT = "CROSS CLAIM DEFENDANT"
    INTERPRETER = "INTERPRETER"
    TENANT = "TENANT"
    LANDLORD = "LANDLORD"
    WITNESS = "WITNESS"
    GARNISHEE = "GARNISHEE"
    ALIAS = "ALIAS"
    OFFICER = "OFFICER"
    OFFICER_COMPLAINANT = "OFFICER COMPLAINANT"
    CITY_SOLICITOR = "CITY SOLICITOR"
    PARTY_COMPLAINANT = "PARTY COMPLAINANT"
    VICTIM = "VICTIM"
    PROBATION_OFFICER = "PROBATION OFFICER"
    PROSECUTING_WITNESS = "PROSECUTING WITNESS"
    BOND_DEPOSITOR = "BOND DEPOSITOR"
    ALERT_ON_ATTORNEY = "ALERT ON ATTORNEY"


class SideName(BaseModel):
    type_: Sides = Field(..., alias="type")
    name: str

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @classmethod
    def generate(cls, type_):
        return SideName(name=f"TEST {type_}", type_=type_)


class SideAddress(SideName):
    address: list[str]
    city: str | None
    state: Literal[*state_abbreviations] | None
    zip_: str | None = Field(..., alias="zip")

    @field_validator("zip_", mode="after")
    @classmethod
    def is_zip(cls, value: str) -> str:
        if value is None:
            return value
        if len(value) != 5 or not value.isdigit():
            raise ValueError(f"{value} is not zip code")
        return value

    def __hash__(self):
        return hash(str(self))


class Attorney(SideAddress):
    role: Literal["PRIMARY ATTORNEY", "Secondary Attorney", "DO NOT USE"]


class FakeAttorney(SideName):
    address: Literal[["DO NOT USE"]]


class RunningAttorney(SideName):
    address: Literal[
        ["WWR", "***runners will pick up daily***"],
        ["WWW", "***runners will pick up daily***"],
    ]


class PublicAttorney(SideName):
    address: list[str]


class DocketEntry(BaseModel):
    date: datetime.date
    text: str
    extra: str | None = None
    amount: Decimal | None = None
    balance: Decimal | None = None

    @staticmethod
    def generate(filed):
        return list(
            reversed(
                [
                    DocketEntry(
                        date=filed,
                        text="PETITION IN FE&D FILED",
                        extra="Receipt: 12345  Date: ##/##/####",
                        amount=128,
                        balance=0,
                    ),
                    DocketEntry(
                        date=filed + timedelta(days=1), text="IMAGE OF COMPLAINT"
                    ),
                    DocketEntry(
                        date=filed + timedelta(days=1),
                        text="HEARING SCHEDULED, NOTICES PROCESSED - HS",
                        extra="Event: EVICTION HEARING - FCRS <br/>\nDate: 10/23/2025    Time: 8:30 am <br/>\nJudge: 11B    Location: 11B LOCATED ON THE 11TH FLOOR<br/>\n<br/>\nResult: DDSMP - NOTICE OF DISMISSAL BY PLAINTIFF W/O PREJ.",
                    ),
                    DocketEntry(
                        date=filed + timedelta(days=1),
                        text="SUMMONS ISSUED WITH COPY OF COMPLAINT",
                    ),
                    DocketEntry(
                        date=filed + timedelta(days=1),
                        text="ORDINARY MAIL  CERTIFICATE OF MAILING DATED & FILED NEXT BUS. DAY - OM",
                        extra="Issue Date:  10/10/2025<br/>\nService:  ISSUE SVC FOR G1 C/A - ISG1<br/>\nMethod:  ORDINARY MAIL<br/>\nCost Per:  $0.00<br/>\n<br/>\n<br/>\n   DEF<br/>\n     Tracking No: O00000000",
                    ),
                    DocketEntry(
                        date=filed + timedelta(days=1),
                        text="SUMMONS ISSUED WITH COPY OF COMPLAINT",
                        extra="1 CAUSE G - 1CA<br/>\nSent on:  10/10/2025  08:08:47.72",
                    ),
                    DocketEntry(
                        date=filed + timedelta(days=1),
                        text="BAILIFF SERVICE - BS",
                        extra="Issue Date:  10/10/2025<br/>\nService:  ISSUE SVC FOR G1 C/A - ISG1<br/>\nMethod:  BAILIFF SERVICE<br/>\nCost Per:  $0.00<br/>\n<br/>\n<br/>\n  ADDRESS    Tracking No: B0000000",
                    ),
                    DocketEntry(
                        date=filed + timedelta(days=1),
                        text="SUMMONS ISSUED WITH COPY OF COMPLAINT",
                        extra="1 CAUSE G - 1CA<br/>\nSent on:  10/10/2025  08:09:05.63",
                    ),
                    DocketEntry(
                        date=filed + timedelta(days=6),
                        text="BAILIFF RETURN FILED SHOWING SERVICE ON:\nAS TO:",
                        extra="BAILIFF RETURN FILED SHOWING SERVICE ON:<br/>\nAS TO:<br/>\n   Method    : BAILIFF SERVICE<br/>\n   Issued    : 10/10/2025<br/>\n   Service   : ISSUE SVC FOR G1 C/A - ISG1<br/>\n   Served    : 10/14/2025<br/>\n   Return    : 10/15/2025<br/>\n   On        : NAME<br/>\n   Signed By : <br/>\n<br/>\n   Reason    : SUCCESSFUL BAILIFF SERVICE - SBAIL<br/>\n   Comment   : posted<br/>\n<br/>\n   Tracking # : B00000000",
                    ),
                    DocketEntry(
                        date=filed + timedelta(days=13),
                        text="DISMISSED BY PLAINTIFF",
                        extra="The following event: EVICTION HEARING - FCRS scheduled for 10/23/2025 at 8:30 am has been resulted as follows:<br/>\n<br/>\nResult: DDSMP - NOTICE OF DISMISSAL BY PLAINTIFF W/O PREJ. <br/>\nJudge: 11B    Location: 11B LOCATED ON THE 11TH FLOOR",
                    ),
                ]
            )
        )


class Event(BaseModel):
    room: str
    start: datetime.datetime
    end: datetime.datetime
    event: str
    judge: str
    result: str

    @classmethod
    def generate(cls, filed: datetime.date):
        future_days = int(np.random.exponential(5) + 14)
        return Event(
            room="11B",
            judge="11B",
            event="EVICTION HEARING - FCRS",
            result="JUDGEMENT FOR RESTITUTION OF PREMISES",
            start=datetime.datetime.combine(filed, datetime.time(10, 30))
            + timedelta(days=future_days),
            end=datetime.datetime.combine(filed, datetime.time(10, 35))
            + timedelta(days=future_days),
        )


class Finance(BaseModel):
    application: str | Literal["TOTAL"]
    owed: Decimal
    paid: Decimal
    dismissed: Decimal
    balance: Decimal

    @classmethod
    def generate(cls, amt):
        return [
            Finance(application="COST", owed=amt, paid=amt, dismissed=0, balance=0),
            Finance(application="TOTAL:", owed=amt, paid=amt, dismissed=0, balance=0),
        ]


class Disposition(BaseModel):
    code: str
    date: datetime.date | None = None
    judge: str
    status: Literal[
        "CLOSED",
        "OPEN",
        "REOPEN (RO)",
        "POST SENTENCE HEARING",
        "INACTIVE",
        "POST JUDGMENT STATUS",
    ]
    status_date: datetime.date | None = None

    # @model_validator(mode="after")
    # def check_disposition(self) -> Self:
    #    if self.code != "UNDISPOSED" and self.date is None:
    #        raise ValueError("Invalid Disposition")
    #    return self

    @staticmethod
    def generate(filed):
        future_days = np.random.exponential(5) + 14
        code = random.choices(
            [
                "NOTICE OF DISMISSAL FILED",
                "JUDGMENT HEARD BY MAGISTRATE",
                "DISMISSAL HEARD BY MAGISTRATE",
                "OTHER TERMINATION - ADMIN JUDGE",
                "UNDISPOSED",
                "DEFAULT JUDGMENTS",
                "AGREED JUDGMENT BOTH CAUSE OF ACTION",
                "BANKRUPTCY",
                "OTHER TERMINATIONS",
                "TRANSFER TO COURT OF COMMON PLEAS - ADMIN JUDGE",
                "DISMISSED BY PLAINTIFF",
                "AGREED JUDGMENT",
                "JUDGMENT FOR DAMAGES",
                "DISMISSED BY JUDGE",
            ],
            weights=[7976, 7493, 616, 6495, 27, 13, 10, 15, 4, 12, 30, 3, 7, 1],
            k=1,
        )

        return Disposition(
            code=code[0],
            date=filed + timedelta(days=future_days),
            judge="ADMINISTRATIVE",
            status="CLOSED",
            status_date=filed,
        )


class Case(BaseModel):
    case_number: str
    parties: list[Union[SideName, SideAddress]]
    docket: list[DocketEntry]
    attorneys: list[Attorney | FakeAttorney | RunningAttorney | PublicAttorney]
    finances: list[Finance]
    events: list[Event]
    dispositions: list[Disposition]

    @staticmethod
    def generate(num, filed):
        disp = Disposition.generate(filed)
        event = Event.generate(filed)
        pt = SideName.generate(Sides.PLAINTIFF)
        de = SideName.generate(Sides.DEFENDANT)

        d = DocketEntry.generate(filed)
        cost = Finance.generate(223)
        return Case(
            case_number=num,
            parties=[pt, de],
            docket=d,
            attorneys=[],
            finances=cost,
            events=[event],
            dispositions=[disp],
        )
