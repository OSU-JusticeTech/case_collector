import json
import os
from zoneinfo import ZoneInfo

import psycopg
from networkx.generators.trees import random_unlabeled_tree
from psycopg.types import datetime
from tqdm import tqdm

DB_CONFIG = {
    "host": "eviction.felix.nlogn.org",
    "dbname": "eviction",
    "user": "read_user",
    "password": os.getenv("PASSWORD"),
    "port": 15432,
}

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


QUERY = """SELECT * FROM attending_checkinsheet WHERE validated = True ORDER BY taken_at"""

#manual_dates = json.load(open("utils/manual_dates.json"))
#print(manual_dates)

tz_ohio = ZoneInfo("America/New_York")

def export_query(conn, query):
    with conn.cursor() as cur:
        cur.execute(query)

        colnames = [desc.name for desc in cur.description]

        matching = []

        for row in cur:
            data = dict(zip(colnames,row))
            print(data["taken_at"], "exif, detected:", data["processed"]["detected_date"])

            #if not datetime.datetime.fromisoformat('2026-05-13 11:38:18.351503+00:00') < data["taken_at"] < datetime.datetime.fromisoformat('2026-05-13 11:42:18.351503+00:00'):
            #    continue

            #if data["id"] != 26:
            #    continue

            #continue
            nums = []
            ocr = []
            for lbl in data["processed"]["master_data"].values():
                if lbl["present"] is True:
                    ocr.append((lbl["number"],lbl["note"]))
                    nums.append(int(lbl["number"]))

            if len(nums) == 0:
                print("empty inclid sheet", data["filename"])
                continue

            values_sql = ",".join(f"({v})" for v in nums)

            extra = f"WHERE ce.start >= '{data["possible_start"]}' AND ce.start <= '{data["possible_end"]}'"

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


            with conn.cursor() as cursor:
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
                    matching.append({"pk": data["id"],"filename": data["filename"],"matching": results, "actual_cases": len(actual_nums),
                                     "exif": data["taken_at"],"start_time": best_start_time.astimezone(tz_ohio),
                                     "missing": list(set(nums) - actual_nums),
                                     "ocr": ocr})

            #if len(matching) > 1:
            #    break
        #with open("alignment.json","w") as f:
        #    json.dump(matching, f, default=str)
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
                    print(a["filename"])
                    print("wrong time direction", history[-1], best_start)
            history.append(best_start)
            clean_times[a["pk"]] = {**a,"clean_start": best_start.astimezone(tz_ohio)}
            continue
        if good_matches[1]["coverage"] < good_matches[0]["coverage"]:
            print("single winner")
            clean_times[a["pk"]] = {**a,"clean_start": good_matches[0]["start_time"].astimezone(tz_ohio)}
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
            clean_times[a["pk"]] = {**a,"clean_start":  found.astimezone(tz_ohio)}
            continue

        #print(a["filename"])
        #print("hist", history[-3:])
        for gm in good_matches:
            print(gm)
        raise Exception("no clean date is found")
    return clean_times


def get_cases_present(conn,clean):
    with conn.cursor() as cursor:

        sure_there = []
        sql = """
            SELECT
                ce.*,
                ls.case_number,
                ls.case_id,
                ls.id
            FROM cases_event ce
            JOIN latest_snapshot ls
              ON ce.snapshot_id = ls.id
            WHERE ce.start = %s
            """

        cursor.execute(sql, [clean["clean_start"]])
        rows = cursor.fetchall()
        cols = [col[0] for col in cursor.description]
        caseres = [dict(zip(cols, row)) for row in rows]
        # print("rows", results)
        actual_nums = []
        doubleevents = set()
        caseexpand = {}
        for r in caseres:
            if r["case_number"] in doubleevents:
                continue
            number = int(r["case_number"].split(" ")[2])
            caseexpand[number] = r
            actual_nums.append(number)
            doubleevents.add(r["case_number"])

        #print(actual_nums)
        print([c["case_number"] for c in caseres])

        assert list(sorted(actual_nums)) == list(sorted(list(set(actual_nums)))), "Same number from multiple years present"
        for k,note in clean["ocr"]:
            case = caseexpand.get(int(k))
            if case is None:
                print("number not found", k)
                continue
            #print(case["case_number"],case["event"], "-",note)

            sql = """
                        SELECT
                            p.*
                        FROM cases_party p
                        WHERE p.snapshot_id = %s
                        """
            cursor.execute(sql, [case["id"]])
            rows = cursor.fetchall()
            cols = [col[0] for col in cursor.description]
            parties = [dict(zip(cols, row)) for row in rows]
            patt = None
            for p in parties:
                if p["role"] != 'PRIMARY ATTORNEY':
                    continue
                if p["side"] == "PLAINTIFF":
                    patt = p["name"]

            addrs = set(map(lambda p:p["address"], filter(lambda x: x["role"] =="" and x["side"] == "DEFENDANT" , parties)))
            #print("defaddr", addrs)

            if len(addrs) == 1 and patt is not None:
                sure_there.append((case["case_number"],list(addrs)[0]))
            elif len(addrs) != 1:
                print("multiple def addr",case["case_number"], addrs)
            else:
                print("no patt",case["case_number"], case["event"], "-", note)

        return sure_there
        #print("actual", caseexpand)

def main():
    with psycopg.connect(**DB_CONFIG) as conn:
        m = export_query(conn, QUERY)
        c = clean_matches(m)

        sure_theres = {}
        for pk,cl in c.items():
            print(cl)
            sure = get_cases_present(conn, cl)
            sure_theres[cl["clean_start"].isoformat()] = sure
        #print(c)
        with open("sure_there.json","w") as f:
            json.dump(sure_theres, f,default=str)
        #json.dump(c, open("clean_time.json", "w"), default=str, indent=2)


if __name__ == "__main__":
    main()