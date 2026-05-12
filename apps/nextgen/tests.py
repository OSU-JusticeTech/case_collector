import datetime
import logging
import time

from django.test import TestCase, Client
from unittest.mock import patch


from apps.cases.models import CourtCase, Source
from apps.fcmcclerk.tasks import (
    ScrapeInstruction,
)
from apps.fcmcclerk_mock.fake_state import fixture_at
from apps.nextgen.models import ScanDocketEntry, Page
from apps.nextgen.tasks import scrape_pdfs, scrape_generator


class FakeSession:
    def __init__(self, client, report_date):
        self.client = client
        self.report_date = report_date
        self.proxies = {}

    def _build_response(self, response):
        class FakeResponse:
            def __init__(self, response):
                self.status_code = response.status_code
                self.content = response.content
                self.headers = response.headers

            ok = True

        return FakeResponse(response)

    def get(self, url, *args, **kwargs):
        path = url.replace(
            "https://secure.fcmcclerk.com",
            f"/secure.fcmcclerk.com/{self.report_date.isoformat()}",
        )
        # print("get rewrote", path)
        response = self.client.get(path)
        return self._build_response(response)

    def post(self, url, *args, **kwargs):
        path = url.replace(
            "https://secure.fcmcclerk.com",
            f"/secure.fcmcclerk.com/{self.report_date.isoformat()}",
        )
        # print("post rewrote", path)
        response = self.client.post(path, data=kwargs.get("data"))
        return self._build_response(response)


class MyTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.nextgen.tasks.requests.session")
    def test_session_call(self, mock_session_cls):
        mock_session_cls.return_value = FakeSession(
            self.client, datetime.datetime.now().date()
        )
        with self.settings(NEXTGEN_EMAIL="test@test.com", NEXTGEN_PASSWORD="test"):
            # NEXTGEN_PASSWORD="secure"):
            with patch("time.sleep", return_value=None):

                cases = fixture_at(datetime.datetime.now().date())
                for c in cases:
                    if "CVG" in c.case_number:
                        src = Source.objects.create(name="FCMC")
                        CourtCase.objects.create(case_number=c.case_number, source=src)
                        logging.info("testing to scrape %s", c.case_number)
                        scrape_pdfs(ScrapeInstruction(case_number=c.case_number))
                        scrape_pdfs(ScrapeInstruction(case_number=c.case_number))
                        break

        self.assertEqual(ScanDocketEntry.objects.count(), 10)


class IterateTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.nextgen.tasks.requests.session")
    def test_generator(self, mock_session_cls):
        mock_session_cls.return_value = FakeSession(
            self.client, datetime.datetime.now().date()
        )
        with self.settings(NEXTGEN_EMAIL="test@test.com", NEXTGEN_PASSWORD="test"):
            # NEXTGEN_PASSWORD="secure"):
            with patch("time.sleep", return_value=None):

                cases = fixture_at(datetime.datetime.now().date())
                src = Source.objects.create(name="FCMC")
                for c in cases:
                    if "CVG" in c.case_number:
                        CourtCase.objects.create(case_number=c.case_number, source=src)

                scraped = 0
                while scraped < 12:
                    for cinstr in scrape_generator():
                        self.assertIsNotNone(cinstr.case_number)
                        logging.info("scrape case %s", cinstr)
                        scrape_pdfs(cinstr)
                        scraped += 1
                        if scraped >= 12:
                            break
                self.assertEqual(Page.objects.count(), 12)
