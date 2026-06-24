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

QUERY = "SELECT * FROM fcmcclerk_page WHERE year = 2024 AND number=83;"


def export_content(conn, query):
    with conn.cursor() as cur:
        cur.execute(query)

        colnames = [desc.name for desc in cur.description]
        # Get column names from cursor metadata
            # Stream rows
        for row in cur:
            data = dict(zip(colnames, row))
            print(data.keys())
            with open(f"{data['year']}_{data['category']}_{data['number']:06d}-{data['scraped_at']}.html","w") as f:
                f.write(data["content"])



def main():
    with psycopg.connect(**DB_CONFIG) as conn:
        export_content(conn, QUERY)


if __name__ == "__main__":
    main()