from datetime import datetime, timezone, date, timedelta
from unittest.mock import patch, MagicMock
from .tasks import decide_next_scrape
from django.test import TestCase


def mock_get(url, *args, **kwargs):
    mock_response = MagicMock()

    if url == "https://www.fcmcclerk.com/reports/evictions":
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Evictions Report</h1>"
        months = []
        now = datetime.now(timezone.utc).date()
        startmon = now.year * 12 + (now.month)
        for i in range(14):
            month = ((startmon - i) % 12) + 1
            year = (startmon - i) // 12
            months.append(date(year, month, 1))
        start: date
        for start, end in zip(months[1:], months):
            mock_response.text += f"""<a href="/storage/shared/civil-fed/FCMC%20Civil%20F.E.D.%20(Eviction)%20Case%20List%20{start}%20to%20{end-timedelta(days=1)}.csv?{start.isoweekday():06d}" target="_blank">bla</a>"""
            # print(start, end-timedelta(days=1))
        mock_response.text += """</body></html>"""
        mock_response.content = mock_response.text.encode("utf-8")

    elif url.startswith(
        "https://www.fcmcclerk.com/storage/shared/civil-fed/FCMC%20Civil%20F.E.D.%20(Eviction)%20Case%20List%20"
    ):

        start = url[
            -len("2025-11-01%20to%202025-11-30.csv?617929") : -len(
                "%20to%202025-11-30.csv?617929"
            )
        ]
        end = url[-len("2025-11-30.csv?617929") : -len(".csv?617929")]
        print("recovered,", datetime.fromisoformat(start), datetime.fromisoformat(end))
        mock_response.status_code = 200
        mock_response.text = """"CASE_NUMBER","CASE_FILE_DATE","LAST_DISPOSITION_DATE","LAST_DISPOSITION_DESCRIPTION","FIRST_PLAINTIFF_PARTY_SEQUENCE","FIRST_PLAINTIFF_FIRST_NAME","FIRST_PLAINTIFF_MIDDLE_NAME","FIRST_PLAINTIFF_LAST_NAME","FIRST_PLAINTIFF_SUFFIX_NAME","FIRST_PLAINTIFF_COMPANY_NAME","FIRST_PLAINTIFF_ADDRESS_LINE_1","FIRST_PLAINTIFF_ADDRESS_LINE_2","FIRST_PLAINTIFF_CITY","FIRST_PLAINTIFF_STATE","FIRST_PLAINTIFF_ZIP","FIRST_DEFENDANT_PARTY_SEQUENCE","FIRST_DEFENDANT_FIRST_NAME","FIRST_DEFENDANT_MIDDLE_NAME","FIRST_DEFENDANT_LAST_NAME","FIRST_DEFENDANT_SUFFIX_NAME","FIRST_DEFENDANT_COMPANY_NAME","FIRST_DEFENDANT_ADDRESS_LINE_1","FIRST_DEFENDANT_ADDRESS_LINE_2","FIRST_DEFENDANT_CITY","FIRST_DEFENDANT_STATE","FIRST_DEFENDANT_ZIP"
"2025 CVG 044593","09/02/2025","10/02/2025","JUDGMENT HEARD BY MAGISTRATE","1","SIDNEY","","WEST","","","2933 SWITZER AVE","","COLUMBUS","OH","43219","2","D1","","L1","","","1002 OLMSTEAD AVE","","COLUMBUS","OH","43201"
"2025 CVG 044627","09/02/2025","09/24/2025","NOTICE OF DISMISSAL FILED","1","PONCE","","BROWN","JR","","1519 DENBIGH DRIVE","","COLUMBUS","OH","43220","2","D2","","L2","","","39 WEST RAMLOW ALLEY","","COLUMBUS","OH","43202"
"2025 CVG 044630","09/02/2025","11/17/2025","JUDGMENT FOR DAMAGES","1","JAMES","G","RODGERS","","","3109 MUSKET RIDGE DR","","COLUMBUS","OH","43223","2","D3","","L3","","","1608 FALL BROOK RD","","COLUMBUS","OH","43223"
"2025 CVG 044635","09/02/2025","","UNDISPOSED","1","DANIELLE","","HAYNES","","","1191 E WOODROW AVE","","COLUMBUS","OH","43207","2","D4","","L4","","","1191 E WOODROW AVE","","COLUMBUS","OH","43207"
"2025 CVG 044678","09/02/2025","09/18/2025","JUDGMENT HEARD BY MAGISTRATE","1","MICHAEL","","KUSHNER","","","PO BOX 1672","","HILLIARD","OH","43026","2","D5","M5","L5","","","264 S TERRACE CHASE","","COLUMBUS","OH","43204"
"2025 CVG 044700","09/02/2025","09/18/2025","OTHER TERMINATION - ADMIN JUDGE","1","","","","","5812 INVESTMENT GROUP LLC","C/O WILLIS LAW FIRM LLC","PO BOX 2290","COLUMBUS","OH","43216","2","D6","","L6","","","2645 ROEHAMPTON COURT","","COLUMBUS","OH","43209"
        """
        mock_response.content = mock_response.text.encode("utf-8")
    elif (
        url
        == "https://www.fcmcclerk.com/storage/shared/civil-fed/FCMC%20Civil%20F.E.D.%20(Eviction)%20Case%20List%202025-12-01%20to%202025-12-31.csv?617234"
    ):
        mock_response.status_code = 200
        mock_response.text = """"CASE_NUMBER","CASE_FILE_DATE","LAST_DISPOSITION_DATE","LAST_DISPOSITION_DESCRIPTION","FIRST_PLAINTIFF_PARTY_SEQUENCE","FIRST_PLAINTIFF_FIRST_NAME","FIRST_PLAINTIFF_MIDDLE_NAME","FIRST_PLAINTIFF_LAST_NAME","FIRST_PLAINTIFF_SUFFIX_NAME","FIRST_PLAINTIFF_COMPANY_NAME","FIRST_PLAINTIFF_ADDRESS_LINE_1","FIRST_PLAINTIFF_ADDRESS_LINE_2","FIRST_PLAINTIFF_CITY","FIRST_PLAINTIFF_STATE","FIRST_PLAINTIFF_ZIP","FIRST_DEFENDANT_PARTY_SEQUENCE","FIRST_DEFENDANT_FIRST_NAME","FIRST_DEFENDANT_MIDDLE_NAME","FIRST_DEFENDANT_LAST_NAME","FIRST_DEFENDANT_SUFFIX_NAME","FIRST_DEFENDANT_COMPANY_NAME","FIRST_DEFENDANT_ADDRESS_LINE_1","FIRST_DEFENDANT_ADDRESS_LINE_2","FIRST_DEFENDANT_CITY","FIRST_DEFENDANT_STATE","FIRST_DEFENDANT_ZIP"
"2026 CVG 005472","02/02/2026","02/26/2026","OTHER TERMINATION - ADMIN JUDGE","1","","","","","ARDENT PROPERTY MANAGEMENT INC","470 OLDE WORTHINGTON ROAD SUITE 120","","WESTERVILLE","OH","43082","2","D1","","L1","","","40 406 HUTCHINSON AVENUE","","COLUMBUS","OH","43235"
"2026 CVG 005521","02/02/2026","03/25/2026","UNDISPOSED","1","","","","","STAR 2022 SFR3 BORROWER LP","C/O MYND MANAGEMENT INC","717 N HARWOOD STREET STE 2800","DALLAS","TX","75201","2","D2","","L2","","","4966 MCALLISTER AVE","","COLUMBUS","OH","43227"
"""
        mock_response.content = mock_response.text.encode("utf-8")

    else:
        raise ValueError(f"Unexpected URL: {url}")

    return mock_response


class NextCaseTest(TestCase):

    @patch("apps.fcmcclerk.tasks.requests.session")
    def test_multiple_urls(self, mock_session):
        session_instance = mock_session.return_value
        session_instance.get.side_effect = mock_get

        with patch("time.sleep", return_value=None):
            decide_next_scrape()
