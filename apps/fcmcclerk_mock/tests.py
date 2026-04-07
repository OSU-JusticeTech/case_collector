import datetime

from django.test import TestCase
from .fake_state import generate_year, fixture_at


# Create your tests here.


class FixtureTest(TestCase):

    def test_year(self):
        generate_year(2025)

    def test_restriction(self):
        cases = fixture_at(datetime.date(2025,10,10))
        for case in cases[-100:]:
            print(case.dispositions)