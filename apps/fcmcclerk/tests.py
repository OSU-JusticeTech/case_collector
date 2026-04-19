import datetime
import logging
import time

from django.test import TestCase, Client
from unittest.mock import patch
import json
from django.core.cache import cache

from apps.fcmcclerk.models import Page
from apps.fcmcclerk.tasks import scrape_detail, CACHE_KEY, parse_page, scrape_generator


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
        mock_session_cls.return_value = FakeSession(
            self.client, datetime.datetime.now().date()
        )
        with patch("time.sleep", return_value=None):
            scrape_n_cases(15)

            cache.delete(CACHE_KEY)

            logging.warning("cleared cache")
            mock_session_cls.return_value = FakeSession(
                self.client,
                (datetime.datetime.now() + datetime.timedelta(days=2)).date(),
            )

            scrape_n_cases(15)

        print(Page.objects.all())

        self.assertEqual(Page.objects.count(), 30)


class SealingTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.fcmcclerk.tasks.requests.session")
    def test_session_call(self, mock_session_cls):
        mock_session_cls.return_value = FakeSession(
            self.client, (datetime.datetime.now() - datetime.timedelta(days=100)).date()
        )
        with patch("time.sleep", return_value=None):
            scrape_n_cases(20)

            cache.delete(CACHE_KEY)

            logging.warning("cleared cache")
            mock_session_cls.return_value = FakeSession(
                self.client,
                (datetime.datetime.now() + datetime.timedelta(days=2)).date(),
            )

            scrape_n_cases(70)

        print(Page.objects.all())

        self.assertEqual(Page.objects.count(), 90)


class LiveTest(TestCase):
    def test_session_call(self):
        scrape_n_cases(1)
        time.sleep(15)
        scrape_n_cases(1)

        print(Page.objects.all())

        self.assertEqual(Page.objects.count(), 2)

