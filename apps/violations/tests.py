import datetime
from unittest.mock import patch

from django.test import TestCase
from django.test import TestCase, Client, tag

from apps.fcmcclerk.tests import FakeSession
from apps.violations.tasks import get_csv
from apps.violations.models import CodeViolation

# Create your tests here.


class BasicTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("apps.violations.tasks.requests.session")
    def test_session_call(self, mock_session_cls):
        now = datetime.datetime(2026, 7, 4)
        mock_session_cls.return_value = FakeSession(
            self.client, (now - datetime.timedelta(days=100)).date()
        )
        with patch("time.sleep", return_value=None):
            get_csv(now.date())

        self.assertEqual(CodeViolation.objects.count(), 10)
