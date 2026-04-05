from django.test import TestCase, Client
from unittest.mock import patch
import json

from apps.fcmcclerk.tasks import decide_next_scrape


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
        path = url.replace("https://www.fcmcclerk.com", "")
        response = self.client.post(path, data=kwargs.get("data"))
        return self._build_response(response)


class MyTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.fcmcclerk.tasks.requests.session")
    def test_session_call(self, mock_session_cls):
        mock_session_cls.return_value = FakeSession(self.client)

        with patch("time.sleep", return_value=None):
            decide_next_scrape()
