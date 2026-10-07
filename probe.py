"""
Two questions before building the four-treatment run:

  1. Does FUND_REPORTED_INFO carry a net-assets figure? (the right denominator)
  2. How much value sits in ISSUER_TYPE = 'RF' — fund-of-funds holdings that
     would move under look-through?

Read-only. Writes nothing.

    python probe.py nport.duckdb
"""
import sys

import duckdb

DB = sys.argv[1] if len(sys.argv) > 1 else "nport.duckdb"
con = duckdb.connect(DB, read_only=True)

print("=" * 70)
print("FUND_REPORTED_INFO columns")
print("=" * 70)
info = con.sql("DESCRIBE FUND_REPORTED_INFO").fetchall()
for name, dtype, *_ in info:
    mark = "  <<<" if any(k in name.upper()
                          for k in ("ASSET", "LIAB", "NET", "VALUE")) else ""
    print(f"  {name:<34} {dtype}{mark}")

print()
print("=" * 70)
print("ISSUER_TYPE across all holdings")
print("=" * 70)
rows = con.sql("""
    SELECT
        COALESCE(ISSUER_TYPE, '(null)')               AS t,
        COUNT(*)                                      AS positions,
        SUM(ABS(TRY_CAST(CURRENCY_VALUE AS DOUBLE)))  AS value
    FROM FUND_REPORTED_HOLDING
    GROUP BY 1
    ORDER BY value DESC NULLS LAST
""").fetchall()
total = sum(v or 0 for _, _, v in rows)
for t, n, v in rows:
    v = v or 0.0
    print(f"  {t:<10} {n:>12,} positions  ${v:>20,.0f}   {100*v/total:>6.2f}%")

print()
print("=" * 70)
print("ASSET_CAT of registered-fund (RF) holdings — where look-through bites")
print("=" * 70)
rows = con.sql("""
    SELECT
        COALESCE(ASSET_CAT, '(null)')                 AS cat,
        COUNT(*)                                      AS positions,
        SUM(ABS(TRY_CAST(CURRENCY_VALUE AS DOUBLE)))  AS value
    FROM FUND_REPORTED_HOLDING
    WHERE ISSUER_TYPE = 'RF'
    GROUP BY 1
    ORDER BY value DESC NULLS LAST
""").fetchall()
rf_total = sum(v or 0 for _, _, v in rows)
for cat, n, v in rows:
    v = v or 0.0
    print(f"  {cat:<10} {n:>12,} positions  ${v:>20,.0f}   {100*v/rf_total:>6.2f}%")
print(f"\n  RF holdings are ${rf_total:,.0f} = {100*rf_total/total:.2f}% of all "
      f"reported value.")

print()
print("=" * 70)
print("Securities-lending collateral, by issuer title")
print("=" * 70)
rows = con.sql("""
    SELECT
        ISSUER_TITLE                                  AS title,
        COUNT(*)                                      AS positions,
        SUM(ABS(TRY_CAST(CURRENCY_VALUE AS DOUBLE)))  AS value
    FROM FUND_REPORTED_HOLDING
    WHERE UPPER(COALESCE(ISSUER_TITLE, '')) LIKE '%SL AGENCY%'
       OR UPPER(COALESCE(ISSUER_TITLE, '')) LIKE '%SECURITIES LENDING%'
       OR UPPER(COALESCE(ISSUER_TITLE, '')) LIKE '%COLLATERAL%'
    GROUP BY 1
    ORDER BY value DESC NULLS LAST
    LIMIT 15
""").fetchall()
if not rows:
    print("  no title matches — collateral is not identifiable by name")
else:
    sl = sum(v or 0 for _, _, v in rows)
    for title, n, v in rows:
        v = v or 0.0
        print(f"  {str(title)[:46]:<48} {n:>7,}  ${v:>18,.0f}")
    print(f"\n  top-15 title matches: ${sl:,.0f} = {100*sl/total:.2f}% of all value")
    print("  (name matching is a floor, not a count — most collateral will not"
          " say so in its title)")
