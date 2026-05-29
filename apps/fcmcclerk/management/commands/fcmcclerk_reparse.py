from django.core.management.base import BaseCommand
from tqdm import tqdm

from apps.cases.models import Source, CourtCase, CaseSnapshot
from apps.fcmcclerk.models import Page
from apps.fcmcclerk.parser import parse_case
from apps.fcmcclerk.tasks import (
    create_snapshot_if_changed,
)


class Command(BaseCommand):
    help = "Reparse all FCMC cases"

    def handle(self, *args, **options):
        src, _ = Source.objects.get_or_create(name="FCMC")

        already_cleaned = set()

        for pg in tqdm(
            Page.objects.filter(return_code__gte=200, return_code__lt=300).order_by(
                "scraped_at"
            )
        ):
            case = parse_case(pg.content)

            if case.case_number not in already_cleaned:
                already_cleaned.add(case.case_number)
                CaseSnapshot.objects.filter(
                    case__case_number=case.case_number, case__source=src
                ).delete()

            snap, created = create_snapshot_if_changed(
                source=src,
                scraped_at=pg.scraped_at,
                parse_case=case,
            )

            pg.snapshot = snap
            pg.save()
