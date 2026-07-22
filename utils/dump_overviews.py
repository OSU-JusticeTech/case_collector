import os

import psycopg
import csv
from tqdm import tqdm

DB_CONFIG = {
    "host": "as-cura-server.asc.ohio-state.edu",
    "dbname": "eviction",
    "user": "read_user",
    "password": os.getenv("PASSWORD"),
    "port": 5432,
}

QUERY = "SELECT * FROM latest_overview;"
OUTPUT_FILE = "output.csv"
# QUERY = "select * from nextgen_magistrate_presence WHERE date > '2025-11-20';"
# OUTPUT_FILE = "magdecs.csv"
#QUERY = """select pc.*,cs.filename,cs.event_time,c.* from attending_presencecase pc JOIN attending_checkinsheet cs ON pc.sheet_id = cs.id
# JOIN cases_courtcase c ON c.id = pc.case_id"""
#OUTPUT_FILE = "presence.csv"
QUERY = "select * from attending_presencecase p WHERE p.case_id is NULL"
OUTPUT_FILE = "rubbish.csv"

def export_query_to_csv(conn, query, output_file):
    with conn.cursor() as cur:
        cur.execute(query)

        # Get column names from cursor metadata
        colnames = [desc.name for desc in cur.description]

        with open(output_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(colnames)

            # Stream rows
            for row in tqdm(cur):
                writer.writerow(row)


def main():
    with psycopg.connect(**DB_CONFIG) as conn:
        export_query_to_csv(conn, QUERY, OUTPUT_FILE)


if __name__ == "__main__":
    main()