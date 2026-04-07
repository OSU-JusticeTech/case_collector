from django.test import TestCase, Client
from unittest.mock import patch
import json

from apps.fcmcclerk.models import Page
from apps.fcmcclerk.tasks import decide_next_scrape, scrape_detail


class FakeSession:
    def __init__(self, client):
        self.client = client
        self.proxies = {}

    def _build_response(self, response):
        class FakeResponse:
            def __init__(self, response):
                self.status_code = response.status_code
                self.content = response.content

            ok = True

        return FakeResponse(response)

    def get(self, url, *args, **kwargs):
        path = url.replace("https://www.fcmcclerk.com", "/fcmcclerk.com")
        print("get rewrote", path)
        response = self.client.get(path)
        return self._build_response(response)

    def post(self, url, *args, **kwargs):
        path = url.replace("https://www.fcmcclerk.com", "/fcmcclerk.com")
        print("post rewrote", path)
        response = self.client.post(path, data=kwargs.get("data"))
        return self._build_response(response)


class MyTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.fcmcclerk.tasks.requests.session")
    def test_session_call(self, mock_session_cls):
        mock_session_cls.return_value = FakeSession(self.client)

        with patch("time.sleep", return_value=None):
            cno = decide_next_scrape()
            scrape_detail(cno)

        self.assertEqual(Page.objects.count(), 1)
        print(Page.objects.all())
