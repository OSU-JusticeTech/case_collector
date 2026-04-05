from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Literal, Union
import datetime
from enum import Enum
from decimal import Decimal


state_abbreviations = [
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
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
    CITY_SOLICITOR = 'CITY SOLICITOR'
    PARTY_COMPLAINANT = 'PARTY COMPLAINANT'
    VICTIM = 'VICTIM'
    PROBATION_OFFICER = 'PROBATION OFFICER'
    PROSECUTING_WITNESS = 'PROSECUTING WITNESS'
    BOND_DEPOSITOR = 'BOND DEPOSITOR'
    ALERT_ON_ATTORNEY = 'ALERT ON ATTORNEY'


class SideName(BaseModel):
    type_: Sides = Field(..., alias="type")
    name: str

    model_config = ConfigDict(
        populate_by_name=True,
    )


class SideAddress(SideName):
    address: list[str]
    city: str
    state: Literal[*state_abbreviations]
    zip_: str = Field(..., alias="zip")

    @field_validator("zip_", mode="after")
    @classmethod
    def is_zip(cls, value: str) -> str:
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
    address: Literal[["WWR", "***runners will pick up daily***"], ["WWW", "***runners will pick up daily***"]]

class PublicAttorney(SideName):
    address: list[str]

class DocketEntry(BaseModel):
    date: datetime.date
    text: str
    extra: str | None = None
    amount: Decimal | None = None
    balance: Decimal | None = None


class Event(BaseModel):
    room: str
    start: datetime.datetime
    end: datetime.datetime
    event: str
    judge: str
    result: str


class Finance(BaseModel):
    application: str | Literal["TOTAL"]
    owed: Decimal
    paid: Decimal
    dismissed: Decimal
    balance: Decimal

class Disposition(BaseModel):
    code: str
    date: datetime.date | None = None
    judge: str
    status: Literal["CLOSED", "OPEN", "REOPEN (RO)", "POST SENTENCE HEARING", "INACTIVE", "POST JUDGMENT STATUS"]
    status_date: datetime.date | None = None

    #@model_validator(mode="after")
    #def check_disposition(self) -> Self:
    #    if self.code != "UNDISPOSED" and self.date is None:
    #        raise ValueError("Invalid Disposition")
    #    return self


class Case(BaseModel):
    case_number: str
    parties: list[Union[SideName, SideAddress]]
    docket: list[DocketEntry]
    attorneys: list[Attorney | FakeAttorney | RunningAttorney | PublicAttorney]
    finances: list[Finance]
    events: list[Event]
    dispositions: list[Disposition]
