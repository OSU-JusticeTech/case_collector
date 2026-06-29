import os

import psycopg
import csv
from tqdm import tqdm

DB_CONFIG = {
    "host": "eviction.felix.nlogn.org",
    "dbname": "eviction",
    "user": "read_user",
    "password": os.getenv("PASSWORD"),
    "port": 15432,
}

QUERY = """WITH base AS (
    SELECT
        s.case_number,
        d.date::date AS event_date,
        MIN(d.date::date) OVER (PARTITION BY s.case_number) AS start_date
    FROM latest_snapshot s
    JOIN cases_docketentry d ON d.snapshot_id = s.id
),
diffs AS (
    SELECT
        (event_date - start_date) AS day_offset
    FROM base
)
SELECT
    day_offset,
    COUNT(*) AS events
FROM diffs
GROUP BY day_offset
ORDER BY day_offset"""

def export_query(conn, query):
    with conn.cursor() as cur:
        cur.execute(query)

        for row in tqdm(cur):
            print(row)


def main():
    with psycopg.connect(**DB_CONFIG) as conn:
        export_query(conn, QUERY)


if __name__ == "__main__":
    main()