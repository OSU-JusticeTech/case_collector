import datetime

from django.test import TestCase
from .fake_state import generate_year, fixture_at

# Create your tests here.


class FixtureTest(TestCase):

    def test_year(self):
        generate_year(2025)

    def est_restriction(self):
        cases = fixture_at(datetime.date(2025, 10, 10))
        for case in cases[-10:]:
            print(case.dispositions)

    def test_sealing(self):
        cases = fixture_at(datetime.date(2025, 5, 10))
        print("got 2025-10-10")
        cases_new = fixture_at(datetime.date(2026, 2, 10))

        print(
            "sealed",
            set([c.case_number for c in cases])
            - set([c.case_number for c in cases_new]),
        )
