import json

from django.core.management import BaseCommand
from django.db.models import OuterRef, Subquery

from apps.cases.models import Source, CourtCase, CaseSnapshot
from apps.cases.serializers import SnapshotSerializer


class Command(BaseCommand):
    help = "Exports Cases"

    def add_arguments(self, parser):
        parser.add_argument("source", type=str)
        parser.add_argument("contains", type=str)

    def handle(self, *args, **options):
        src = Source.objects.get(name=options["source"])

        latest_snapshot_ids = (
            CaseSnapshot.objects.filter(case=OuterRef("pk"))
            .order_by("-created_at")
            .values("id")[:1]
        )

        cases = CourtCase.objects.filter(
            source=src, case_number__contains=options["contains"]
        ).annotate(latest_snapshot=Subquery(latest_snapshot_ids))

        snapids = [c.latest_snapshot for c in cases]

        snaps = CaseSnapshot.objects.in_bulk(snapids)

        ser = SnapshotSerializer(snaps.values(), many=True)
        print(json.dumps(ser.data))
