import os
from zoneinfo import ZoneInfo

import psycopg
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

def export_query(conn, query):
    with conn.cursor() as cur:
        cur.execute(query)

        colnames = [desc.name for desc in cur.description]

        for row in cur:
            data = dict(zip(colnames,row))
            print(data["taken_at"], data["processed"]["detected_date"])

            #continue
            nums = []
            for lbl in data["processed"]["master_data"].values():
                if lbl["present"] is True:
                    print(lbl["number"],lbl["note"])
                    nums.append(int(lbl["number"]))

            if len(nums) == 0:
                print("empty inclid sheet", data["filename"])
                continue

            values_sql = ",".join(f"({v})" for v in nums)

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
            tz_ohio = ZoneInfo("America/New_York")

            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                cols = [col[0] for col in cursor.description]
                results = [dict(zip(cols, row)) for row in rows]
                # print("match", results)
                if len(results) > 0:
                    #print(results)
                    for r in results[:3]:
                        print(r["start_time"].astimezone(tz_ohio),r["matches"],r["coverage"])
                    if results[0]["coverage"] > 0.5:
                        best_start_time = results[0]["start_time"]  # from your ranking query
                        print("best start time", best_start_time.astimezone(tz_ohio).isoformat())
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
                        results = [dict(zip(cols, row)) for row in rows]
                        #print("rows", results)
                        for r in results:
                            sc = ""
                            if int(r["case_number"].split(" ")[2]) in nums:
                                sc = bcolors.BOLD
                            print(sc, r["case_number"],r["event"],r["result"], bcolors.ENDC)
                        #numends = [r["case_num"] for r in results]
                        # print("possible", numends)
                        #return best_start_time, results

            #break

def main():
    with psycopg.connect(**DB_CONFIG) as conn:
        export_query(conn, QUERY)


if __name__ == "__main__":
    main()