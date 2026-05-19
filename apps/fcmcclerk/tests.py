import datetime
import logging
import time
from collections import Counter

from django.db.models import Model
from django.test import TestCase, Client
from unittest.mock import patch
import json
from django.core.cache import cache

from apps.cases.models import CourtCase, CaseSnapshot
from apps.fcmcclerk.models import Page
from apps.fcmcclerk.tasks import scrape_detail, CACHE_KEY, parse_page, scrape_generator
from apps.fcmcclerk_mock.fake_state import fixture_at


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

            ok = True

        return FakeResponse(response)

    def get(self, url, *args, **kwargs):
        path = url.replace(
            "https://www.fcmcclerk.com",
            f"/fcmcclerk.com/{self.report_date.isoformat()}",
        )
        # print("get rewrote", path)
        response = self.client.get(path)
        return self._build_response(response)

    def post(self, url, *args, **kwargs):
        path = url.replace(
            "https://www.fcmcclerk.com",
            f"/fcmcclerk.com/{self.report_date.isoformat()}",
        )
        # print("post rewrote", path)
        response = self.client.post(path, data=kwargs.get("data"))
        return self._build_response(response)


def scrape_n_cases(n):
    scraped = 0
    while scraped < n:
        for cinstr in scrape_generator():
            logging.info("scrape case %s", cinstr)
            pg = scrape_detail(cinstr)
            if pg.return_code == 200:
                parse_page(pg)
            else:
                logging.warning("case %s not found: %s", cinstr, pg)
            scraped += 1
            if scraped >= n:
                break


class MyTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.fcmcclerk.tasks.requests.session")
    def test_session_call(self, mock_session_cls):
        now = datetime.datetime(2026, 5, 12)
        mock_session_cls.return_value = FakeSession(self.client, now.date())
        with patch("time.sleep", return_value=None):
            scrape_n_cases(15)

            cases = [c for c in fixture_at((now).date()) if "CVG" in c.case_number][
                -15:
            ]

            should = [c.case_number for c in cases]

            self.assertListEqual(
                list(
                    CourtCase.objects.order_by("case_number").values_list(
                        "case_number", flat=True
                    )
                ),
                should,
            )
            cache.delete(CACHE_KEY)

            logging.warning("cleared cache")
            mock_session_cls.return_value = FakeSession(
                self.client,
                (now + datetime.timedelta(days=5)).date(),
            )

            scrape_n_cases(15)

        cases_fut = [
            c
            for c in fixture_at((now + datetime.timedelta(days=5)).date())
            if "CVG" in c.case_number
        ]

        should_rescrape = []
        cases_part = [
            c.model_dump_json(include={"case_number", "dispositions", "parties"})
            for c in cases
        ]
        for c in reversed(cases_fut):
            if (
                c.model_dump_json(include={"case_number", "dispositions", "parties"})
                in cases_part
            ):
                continue
            should_rescrape.append(c)
            if len(should_rescrape) >= 15:
                break

        self.assertSetEqual(
            set(
                CourtCase.objects.order_by("case_number").values_list(
                    "case_number", flat=True
                )
            ),
            set([c.case_number for c in should_rescrape]).union(set(should)),
        )
        self.assertEqual(Page.objects.count(), 30)
        snaps = CaseSnapshot.objects.values_list("case__case_number", flat=True)
        self.assertDictEqual(
            Counter(snaps), Counter([c.case_number for c in should_rescrape] + should)
        )


class SealingTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.fcmcclerk.tasks.requests.session")
    def test_session_call(self, mock_session_cls):
        now = datetime.datetime(2026, 5, 12)
        mock_session_cls.return_value = FakeSession(
            self.client, (now - datetime.timedelta(days=100)).date()
        )
        with patch("time.sleep", return_value=None):
            scrape_n_cases(20)

            cache.delete(CACHE_KEY)

            logging.warning("cleared cache")
            mock_session_cls.return_value = FakeSession(
                self.client,
                (now + datetime.timedelta(days=2)).date(),
            )

            scrape_n_cases(70)

        # print(Page.objects.all())

        self.assertEqual(Page.objects.count(), 90)
        sealed_pages = Page.objects.filter(return_code=410)
        self.assertEqual(sealed_pages.count(), 1)
        self.assertEqual(sealed_pages[0].number, 36)


class LiveTest(TestCase):
    def test_session_call(self):
        scrape_n_cases(1)
        time.sleep(15)
        scrape_n_cases(1)

        print(Page.objects.all())

        pages = Page.objects.all()
        self.assertEqual(pages.count(), 2)
        for p in pages:
            self.assertEqual(p.return_code, 200)
            self.assertInHTML("Docket", p.content)
