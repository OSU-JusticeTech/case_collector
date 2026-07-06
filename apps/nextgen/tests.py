import datetime
import logging
import time

from django.core.cache import cache
from django.test import TestCase, Client
from unittest.mock import patch


from apps.cases.models import CourtCase, Source
from apps.fcmcclerk.tasks import (
    ScrapeInstruction,
    CACHE_KEY,
)
from apps.fcmcclerk.tests import scrape_n_cases, FakeSession
from apps.fcmcclerk_mock.fake_state import fixture_at
from apps.nextgen.models import ScanDocketEntry, Page
from apps.nextgen.tasks import scrape_pdfs, scrape_generator


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


class UpdateTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.nextgen.tasks.requests.session")
    def test_generator(self, mock_session_cls):
        now = datetime.datetime(2026, 5, 12)
        mock_session_cls.return_value = FakeSession(self.client, now.date())
        with self.settings(NEXTGEN_EMAIL="test@test.com", NEXTGEN_PASSWORD="test"):
            with patch("time.sleep", return_value=None):

                scrape_n_cases(20)

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

                cache.delete(CACHE_KEY)

                logging.warning("cleared cache")
                mock_session_cls.return_value = FakeSession(
                    self.client,
                    (now + datetime.timedelta(days=10)).date(),
                )

                scrape_n_cases(20)

                scraped = 0
                while scraped < 15:
                    for cinstr in scrape_generator():
                        self.assertIsNotNone(cinstr.case_number)
                        logging.info("scrape case %s", cinstr)
                        scrape_pdfs(cinstr)
                        scraped += 1
                        if scraped >= 15:
                            break


class ExpireTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.nextgen.tasks.requests.session")
    def test_generator(self, mock_session_cls):
        now = datetime.datetime(2026, 5, 12)
        mock_session_cls.return_value = FakeSession(self.client, now.date())
        cno = "2026 CVG 000166"
        src = Source.objects.create(name="FCMC")
        CourtCase.objects.create(case_number=cno, source=src)

        with patch("time.sleep", return_value=None):
            with self.settings(
                NEXTGEN_EMAIL="test@test.com", NEXTGEN_PASSWORD="non-expired"
            ):
                scrape_pdfs(ScrapeInstruction(case_number=cno))
                self.assertEqual(
                    ScanDocketEntry.objects.exclude(filename="").count(), 1
                )

            with self.assertRaises(Exception) as context:
                with self.settings(
                    NEXTGEN_EMAIL="test@test.com", NEXTGEN_PASSWORD="expired"
                ):
                    scrape_pdfs(ScrapeInstruction(case_number=cno))
                    # self.assertEqual(ScanDocketEntry.objects.exclude(filename="").count(), 1)

            self.assertEqual(str(context.exception), "validate email")
