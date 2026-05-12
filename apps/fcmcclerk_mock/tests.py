import datetime

from django.test import TestCase
from .fake_state import generate_year, fixture_at
from ..fcmcclerk.pyschema import Case

# Create your tests here.


class FixtureTest(TestCase):

    def test_year(self):
        generate_year(2025)

    def test_restriction(self):
        cases = fixture_at(datetime.date(2025, 10, 10))
        print(len(cases))
        for case in cases[-10:]:
            self.assertEqual(case.dispositions[0].status, "OPEN")
            print(case.dispositions)

    def test_sealing(self):
        cases = fixture_at(datetime.date(2025, 5, 10))
        cases_new = fixture_at(datetime.date(2026, 2, 10))

        print(
            "sealed",
            set([c.case_number for c in cases])
            - set([c.case_number for c in cases_new]),
        )
        self.assertSetEqual(
            set([c.case_number for c in cases])
            - set([c.case_number for c in cases_new]),
            {
                "2025 CVG 000135",
                "2025 CVG 000153",
                "2025 CVF 000152",
                "2025 CVF 000138",
                "2025 CVF 000136",
            },
        )
