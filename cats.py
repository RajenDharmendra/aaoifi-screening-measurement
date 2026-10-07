"""
List every ASSET_CAT code in the database with its value and position count,
and flag the ones shariah_demo.py does not classify.

Read-only. Writes nothing.

    python cats.py nport.duckdb
"""
import sys

import duckdb

from shariah_demo import CLASSIFICATION

DB = sys.argv[1] if len(sys.argv) > 1 else "nport.duckdb"

con = duckdb.connect(DB, read_only=True)

rows = con.sql("""
    SELECT
        COALESCE(ASSET_CAT, '(null)')                 AS cat,
        COUNT(*)                                      AS positions,
        SUM(ABS(TRY_CAST(CURRENCY_VALUE AS DOUBLE)))  AS value
    FROM FUND_REPORTED_HOLDING
    GROUP BY 1
    ORDER BY value DESC NULLS LAST
""").fetchall()

total = sum(v or 0 for _, _, v in rows)

print(f"{'CAT':<12} {'BUCKET':<10} {'POSITIONS':>12} {'VALUE':>18}   {'SHARE':>7}")
print("-" * 65)

missing = []
for cat, n, val in rows:
    val = val or 0.0
    bucket = CLASSIFICATION.get(cat)
    if bucket is None:
        bucket = "UNMAPPED"
        missing.append((cat, n, val))
    print(f"{cat:<12} {bucket:<10} {n:>12,} {val:>18,.0f}   "
          f"{100*val/total:>6.2f}%")

print("-" * 65)
print(f"{'TOTAL':<23} {sum(n for _, n, _ in rows):>12,} {total:>18,.0f}")

if missing:
    unmapped_value = sum(v for _, _, v in missing)
    print(f"\n{len(missing)} UNMAPPED categories carrying "
          f"${unmapped_value:,.0f} ({100*unmapped_value/total:.2f}% of all value):")
    for cat, n, val in missing:
        print(f"    {cat!r:<14} {n:>10,} positions   ${val:,.0f}")
    print("\nEvery percentage in shariah_summary.csv is wrong by some part of "
          "this. Add these to CLASSIFICATION and re-run.")
else:
    print("\nAll categories mapped. The percentages stand.")

# Where does the biggest discrepancy come from? Check one fund by name.
print("\n" + "=" * 65)
print("Breakdown for iShares Russell 2500 ETF (should be ~100% equity):")
print("=" * 65)
detail = con.sql("""
    SELECT
        h.ASSET_CAT                                     AS cat,
        COUNT(*)                                        AS positions,
        SUM(ABS(TRY_CAST(h.CURRENCY_VALUE AS DOUBLE)))  AS value
    FROM FUND_REPORTED_HOLDING h
    JOIN FUND_REPORTED_INFO f USING (ACCESSION_NUMBER)
    WHERE f.SERIES_NAME = 'iShares Russell 2500 ETF'
    GROUP BY 1
    ORDER BY value DESC NULLS LAST
""").fetchall()

if not detail:
    print("  fund not found under that exact name")
else:
    sub = sum(v or 0 for _, _, v in detail)
    for cat, n, val in detail:
        val = val or 0.0
        print(f"  {str(cat):<12} {CLASSIFICATION.get(cat, 'UNMAPPED'):<10} "
              f"{n:>8,} positions  ${val:>18,.0f}   {100*val/sub:>6.2f}%")
