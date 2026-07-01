import os
import base64
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
import psycopg
from psycopg.rows import dict_row
from fastmcp import FastMCP
from mcp.types import TextContent
from fastmcp.server.auth.providers.jwt import JWTVerifier


authelia_verifier = JWTVerifier(
    jwks_uri="http://authelia:9091/authelia/api/oidc/jwks",
    issuer="https://edrn.felix.nlogn.org/authelia",
    audience="https://edrn.felix.nlogn.org",
)

# 1. Initialize the FastMCP Server
mcp = FastMCP("eviction-db", auth=authelia_verifier)

# Ensure DB_DSN is provided
DB_DSN = os.environ.get("DB_DSN")
if not DB_DSN:
    raise ValueError("DB_DSN environment variable is required")

# The exact docstring from your original server to guide the model
QUERY_TOOL_DESCRIPTION = """
Run a read-only SQL SELECT against the Franklin County eviction database.

PRIMARY VIEW — start here:
  latest_overview: one row per case with tenant name/address, landlord name,
    plaintiff attorney, geocoded location, disposition code/judge/status,
    docket date range, party counts.
    Key columns: case_number, id (=snapshot_id), status, code, judge,
    status_date, date, stdef_name/address/city/zip (tenant),
    stptf_name/address (landlord), stptfatt_name (attorney),
    full_address, street_name, postal_code, earliest_docket, latest_docket.

DRILL-DOWN tables (join on snapshot_id = latest_snapshot.id):
  cases_docketentry(snapshot_id, date, text, extra, amount, balance)
  cases_event(snapshot_id, room, start, end, event, judge, result)
  cases_finance(snapshot_id, application, owed, paid, dismissed, balance)
  cases_party(snapshot_id, side, name, address, city, state, zip_code, role)
    side: PLAINTIFF, DEFENDANT, LANDLORD, TENANT, 3RD PARTY PLAINTIFF/DEFENDANT
    role: '' (primary party), PRIMARY ATTORNEY, Secondary Attorney
  cases_disposition(snapshot_id, code, date, judge, status, status_date)

OTHER:
  latest_snapshot(case_number, id, case_id, created_at, earliest_date, latest_date)
  cases_casesnapshot(id, case_id, state_hash, created_at) — all historical snapshots
  cases_courtcase(id, source_id, case_number)
  nextgen_scandocketentry(id, case_id, date, text, ...) — scanned docket entries linked
    directly to cases_courtcase via case_id FK (not snapshot-versioned).
    Use download_docket_entry_pdf(entry_pk=id) to fetch the PDF for any row.

The cases are scraped daily and versioned through case snapshots. Always operate on the latest snapshot. 
This is what the latest_snapshot view provides for joining other parts of the case.

Always LIMIT row queries (default 20).
Use ILIKE for case-insensitive text search.
"""


# 2. Register the SQL Query Tool
@mcp.tool(name="query", description=QUERY_TOOL_DESCRIPTION)
def query_tool(sql: str) -> str:
    """Execute a read-only SQL SELECT query."""
    tz_ohio = ZoneInfo("America/New_York")
    try:
        # Use psycopg v3 connection block with dict_row to match JSON-like output
        with psycopg.connect(DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()

                # Convert date/datetime fields to string for clean JSON serialization
                import json
                from datetime import date, datetime

                def json_serial(obj):
                    if isinstance(obj, (datetime, date)):
                        return obj.astimezone(tz_ohio).isoformat()
                    raise TypeError(f"Type {type(obj)} not serializable")

                return json.dumps(rows, default=json_serial)
    except Exception as e:
        # Returning the error as a message to let MCP handle standard error outputs
        return json.dumps({"error": str(e)})


# 3. Register the PDF Download Tool
DOWNLOAD_TOOL_DESCRIPTION = """
Downloads and returns a scanned docket entry PDF by its database ID (nextgen_scandocketentry.id).
Use this when a row in nextgen_scandocketentry contains a not null (scan).
JOIN the nextgen_scandocketentry.case_id on cases_courtcase.id.
The scandocketentry are similar to cases_docketentry of a snapshot, but not always line up.
"""


@mcp.tool(name="download_docket_entry_pdf", description=DOWNLOAD_TOOL_DESCRIPTION)
def download_pdf_tool(id: int) -> list:
    """Downloads a PDF using credentials extracted from the DB_DSN."""
    download_url = f"https://edrn.felix.nlogn.org/nextgen/entry/{id}/download/"

    try:
        # Extract Basic Auth credentials from the DSN URL
        parsed_dsn = urlparse(DB_DSN)
        username = parsed_dsn.username
        password = parsed_dsn.password

        if not username or not password:
            return [TextContent(type="text",
                                text="Error: Could not extract database credentials from DB_DSN for Basic Auth.")]

        # Use httpx with basic auth to pull down the file
        with httpx.Client() as client:
            response = client.get(
                download_url,
                auth=(username, password),
                timeout=30.0
            )

            if response.status_code != 200:
                return [TextContent(
                    type="text",
                    text=f"Error: Failed to fetch PDF from remote endpoint: {response.status_code} {response.reason_phrase}"
                )]

            # Base64 encode the binary data payload
            base64_pdf = base64.b64encode(response.content).decode("utf-8")

            # Return both a status string and the encoded document payload
            return [
                TextContent(type="text", text=f"Successfully authenticated and downloaded PDF for entry ID {id}."),
                TextContent(type="text", text=f"MIME-Type: application/pdf\nData (Base64):\n{base64_pdf}")
            ]

    except Exception as e:
        return [TextContent(type="text", text=f"PDF Download Error: {str(e)}")]


# 4. Entrypoint to run over standard I/O (stdio)
if __name__ == "__main__":
    # transport="http" (or "streamable-http") automatically configures FastMCP
    # to host the JSON-RPC endpoints on an HTTP port.
    mcp.run(transport="http", host="0.0.0.0", port=8000)