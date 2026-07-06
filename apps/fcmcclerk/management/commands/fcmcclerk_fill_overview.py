from django.core.management.base import BaseCommand
from tqdm import tqdm

from apps.cases.models import Source
from apps.fcmcclerk.models import Page
from apps.fcmcclerk.tasks import extract_overview


class Command(BaseCommand):
    help = "fill FCMC case overviews"

    def handle(self, *args, **options):
        src, _ = Source.objects.get_or_create(name="FCMC")
        t = tqdm(
            total=Page.objects.filter(
                return_code__gte=200,
                return_code__lt=300,
                status__isnull=True,
                filed__isnull=True,
            ).count()
        )
        for pg in Page.objects.filter(
            return_code__gte=200,
            return_code__lt=300,
            status__isnull=True,
            filed__isnull=True,
        ).iterator():
            try:
                status, filed = extract_overview(pg.content)
                pg.status = status
                pg.filed = filed
                pg.save()
            except Exception as e:
                print("unable to extract page", pg)
                pass
            t.update()
        t.close()
