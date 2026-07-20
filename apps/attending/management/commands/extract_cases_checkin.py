from django.core.management import BaseCommand
from django.db.models import OuterRef, Subquery

from apps.attending.models import CheckinSheet, PresenceCase
from apps.cases.models import CaseSnapshot, Event, CourtCase


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", dest="write")


    def handle(self, *args, **options):

        for c in CheckinSheet.objects.filter(event_time__isnull=False):
            latest_snapshot_id = (
                CaseSnapshot.objects.filter(case=OuterRef("pk"))
                .order_by("-created_at")
                .values("id")[:1]
            )

            # Use 'casesnapshot' (the default reverse relation name)
            cases = CourtCase.objects.filter(
                casesnapshot__id=Subquery(latest_snapshot_id),
                casesnapshot__event__start=c.event_time,
            )

            print(c)
            #print(cases)

            actual_nums = []
            doubleevents = set()
            caseexpand = {}
            for r in cases:
                if r.case_number in doubleevents:
                    continue
                number = int(r.case_number.split(" ")[-1])
                caseexpand[number] = r
                actual_nums.append(number)
                doubleevents.add(r.case_number)

            assert len(actual_nums) == len(set(actual_nums)), "Same number from multiple years present"

            ocr = []
            for lbl in c.processed["master_data"].values():
                if lbl["present"] is True:
                    ocr.append((lbl["number"], lbl["note"]))

            for k, note in ocr:
                case = caseexpand.get(int(k))
                if case is None:
                    print("number not found", k)
                    if options["write"]:
                        PresenceCase.objects.create(sheet=c,
                                                    raw_number=k,
                                                    note=note)
                else:
                    print(case, "-",note)
                    if options["write"]:
                        PresenceCase.objects.create(sheet=c,
                                                    case=case,
                                                    raw_number=k,
                                                    note=note)
