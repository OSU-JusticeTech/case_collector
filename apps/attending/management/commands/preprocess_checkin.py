from django.core.management import BaseCommand
from tqdm import tqdm

from apps.attending.models import CheckinSheet
from apps.attending.views import extract_sheet


class Command(BaseCommand):

    def handle(self, *args, **options):

        for c in tqdm(CheckinSheet.objects.all()):
            if c.processed is None:
                c.processed = extract_sheet(c)
                c.save()