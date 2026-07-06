from pathlib import Path

from django.core.management import BaseCommand
import json

from apps.attending.models import CheckinSheet


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("file", type=str)

    def handle(self, *args, **options):
        f = Path(options["file"])

        data = json.load(open(f))

        for filename, ti in data.items():
            try:
                c = CheckinSheet.objects.get(filename=filename)
                c.event_time = ti
                c.save()
            except Exception as e:
                print(filename, e.__repr__())
