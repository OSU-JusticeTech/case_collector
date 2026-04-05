from django.test import TestCase
from .fake_state import generate_year

# Create your tests here.


class FixtureTest(TestCase):

    def test_year(self):
        generate_year(2025)
