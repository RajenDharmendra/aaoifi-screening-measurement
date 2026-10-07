"""
Print every field of the non-equity holdings inside iShares Russell 2500 ETF.

One OTHER position worth $719m decides whether this fund passes the current
AAOIFI asset-composition test. This says what it is.

Read-only. Writes nothing.

    python what.py nport.duckdb
"""
import sys

import duckdb

DB = sys.argv[1] if len(sys.argv) > 1 else "nport.duckdb"
FUND = "iShares Russell 2500 ETF"

con = duckdb.connect(DB, read_only=True)

cols = [r[0] for r in con.sql("DESCRIBE FUND_REPORTED_HOLDING").fetchall()]

rows = con.sql(f"""
    SELECT h.*
    FROM FUND_REPORTED_HOLDING h
    JOIN FUND_REPORTED_INFO f USING (ACCESSION_NUMBER)
    WHERE f.SERIES_NAME = '{FUND}'
      AND h.ASSET_CAT IN ('OTHER', 'STIV')
    ORDER BY ABS(TRY_CAST(h.CURRENCY_VALUE AS DOUBLE)) DESC
""").fetchall()

if not rows:
    sys.exit(f"no OTHER/STIV holdings found for {FUND!r}")

for i, row in enumerate(rows, 1):
    print(f"\n{'=' * 70}\nHOLDING {i} of {len(rows)}\n{'=' * 70}")
    for name, val in zip(cols, row):
        if val is None or str(val).strip() in ("", "N/A"):
            continue
        print(f"  {name:<28} {val}")
