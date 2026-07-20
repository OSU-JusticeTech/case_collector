from pathlib import Path
from zoneinfo import ZoneInfo

from django.core.management import BaseCommand
import json

from apps.attending.models import CheckinSheet

from django.db import connection

tz_ohio = ZoneInfo("America/New_York")

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def base_query():
    matching = []

    for row in CheckinSheet.objects.filter(validated=True,event_time__isnull=True).order_by("taken_at"):
        print(row.taken_at, "exif, detected:", row.processed["detected_date"])

        #if not datetime.datetime.fromisoformat('2026-05-13 11:38:18.351503+00:00') < data["taken_at"] < datetime.datetime.fromisoformat('2026-05-13 11:42:18.351503+00:00'):
        #    continue

        #if data["id"] != 26:
        #    continue

        #continue
        nums = []
        ocr = []
        for lbl in row.processed["master_data"].values():
            if lbl["present"] is True:
                ocr.append((lbl["number"],lbl["note"]))
                nums.append(int(lbl["number"]))

        if len(nums) == 0:
            print("empty inclid sheet", row.filename)
            continue

        values_sql = ",".join(f"({v})" for v in nums)

        extra = f"WHERE ce.start >= '{row.possible_start}' AND ce.start <= '{row.possible_end}'"

        sql = f"""
            WITH
            ocr_numbers(num) AS (
                VALUES {values_sql}
            ),
            event_cases AS (
                SELECT
                    ce.start AS start_time,
                    CAST(SUBSTR(ls.case_number, LENGTH(ls.case_number) - 5, 6) AS INTEGER) AS case_num
                FROM cases_event ce
                JOIN latest_snapshot ls
                  ON ce.snapshot_id = ls.id
                {extra}
            ),
            ocr_count AS (
                SELECT COUNT(DISTINCT num) AS total
                FROM ocr_numbers
            )
            SELECT
                ec.start_time,
                COUNT(DISTINCT ec.case_num) AS matches,
                1.0 * COUNT(DISTINCT ec.case_num) / oc.total AS coverage
            FROM event_cases ec
            JOIN ocr_numbers o
              ON o.num = ec.case_num
            CROSS JOIN ocr_count oc
            GROUP BY ec.start_time, oc.total
            ORDER BY matches DESC, coverage DESC;
            """

        # print(sql)


        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            cols = [col[0] for col in cursor.description]
            results = [dict(zip(cols, row)) for row in rows]
            print("match", results)
            best_start_time = None
            #if data["filename"] in manual_dates:
            #    best_start_time = datetime.datetime.fromisoformat(manual_dates[data["filename"]])

            if len(results) > 0:
                #print(results)
                for r in results[:1]:
                    print(r["start_time"].astimezone(tz_ohio),r["matches"],r["coverage"])
                if results[0]["coverage"] > 0.5:
                    best_start_time = results[0]["start_time"]  # from your ranking query

            if best_start_time is not None:
                #print("best start time", best_start_time.astimezone(tz_ohio).isoformat())
                sql = """
                    SELECT
                        ce.*,
                        ls.case_number
                    FROM cases_event ce
                    JOIN latest_snapshot ls
                      ON ce.snapshot_id = ls.id
                    WHERE ce.start = %s
                    """

                cursor.execute(sql, [best_start_time])
                rows = cursor.fetchall()
                cols = [col[0] for col in cursor.description]
                caseres = [dict(zip(cols, row)) for row in rows]
                #print("rows", results)
                actual_nums = set()
                for r in caseres:
                    sc = ""
                    actual_nums.add(int(r["case_number"].split(" ")[2]))
                    if int(r["case_number"].split(" ")[2]) in nums:
                        sc = bcolors.BOLD
                    #print(sc, r["case_number"],r["event"],r["result"], bcolors.ENDC)
                #numends = [r["case_num"] for r in results]
                    # print("possible", numends)
                    #return best_start_time, results
                print("total cases at time:", len(actual_nums))
                if set(nums) - actual_nums != set():
                    print("WARNING, numbers not in cases:", set(nums) - actual_nums)
                matching.append({"obj": row,"matching": results, "actual_cases": len(actual_nums),
                                 "start_time": best_start_time.astimezone(tz_ohio),
                                 "missing": list(set(nums) - actual_nums),
                                 "ocr": ocr})

    return matching


def clean_matches(align):
    thr = 0.6
    history = []
    clean_times = {}
    for a in align:
        good_matches = list(filter(lambda m: float(m["coverage"]) > thr, a["matching"]))
        if len(good_matches) == 1:
            best_start = good_matches[0]["start_time"]
            if len(history) > 0:
                if best_start.date() > history[-1].date():
                    print(a["obj"].filename)
                    print("wrong time direction", history[-1], best_start)
            history.append(best_start)
            clean_times[a["obj"].pk] = {**a,"clean_start": best_start.astimezone(tz_ohio)}
            continue
        if good_matches[1]["coverage"] < good_matches[0]["coverage"]:
            print("single winner")
            clean_times[a["obj"].pk] = {**a,"clean_start": good_matches[0]["start_time"].astimezone(tz_ohio)}
            continue

        best_matches = list(filter(lambda m: m["coverage"] == good_matches[0]["coverage"], a["matching"]))
        print("best", best_matches)
        best_dates = [m["start_time"] for m in best_matches]
        found = None
        for bd in sorted(best_dates, reverse=True):

            if bd in history:
                print("already done")
                continue
            if bd.date() > history[-1].date():
                print("wrong direction")
                continue

            # print("use",bd)
            found = bd
            break
        if found is not None:
            clean_times[a["obj"].pk] = {**a,"clean_start":  found.astimezone(tz_ohio)}
            continue

        #print(a["filename"])
        #print("hist", history[-3:])
        for gm in good_matches:
            print(gm)
        raise Exception("no clean date is found")
    return clean_times

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--write-time", action="store_true", dest="write_time")


    def handle(self, *args, **options):
        matches = base_query()
        clean = clean_matches(matches)
        if options["write_time"]:
            for c in clean.values():
                c["obj"].event_time=c["clean_start"]
                c["obj"].save()