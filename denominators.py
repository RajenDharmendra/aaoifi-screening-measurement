"""
Three denominators, two look-through settings, three AAOIFI thresholds.
Eighteen defensible answers per fund.

WHY THREE DENOMINATORS

  SS 21 3/19 says the ratio is against "total assets value ... including all
  assets, benefits, rights and cash liquidity". SS 59 8/2/2 says "the value of
  the assets of the entity". Neither says NET assets. So:

    gross   sum of ABS(CURRENCY_VALUE) over the holdings table. What the raw
            data gives you if you never open the fund-level table.
    total   the filer's own TOTAL_ASSETS. The literal match to the clause text.
    net     the filer's own NET_ASSETS. What industry practice uses, and what
            removes securities-lending collateral the fund holds but does not
            own. Not what either standard says.

LOOK-THROUGH

  A fund held inside a fund files as ASSET_CAT 'OTHER', ISSUER_TYPE 'RF'.
  iShares Russell 2500 ETF holds 41% of itself in iShares Russell 2000 ETF,
  filed exactly that way. Counting that as equity, or not, is a judgement call
  no standard addresses.

    python denominators.py nport.duckdb

Outputs:
    denominators_summary.csv   one row per fund, all 18 verdicts
    denominators_detail.csv    one row per fund per treatment per rule
"""
import sys

import duckdb
import pandas as pd

DB = sys.argv[1] if len(sys.argv) > 1 else "nport.duckdb"

CLASSIFICATION = {
    "EC": "tangible", "EP": "tangible", "RE": "tangible", "COMM": "tangible",

    "DBT": "debt", "LON": "debt", "ABS-MBS": "debt", "ABS-CBDO": "debt",
    "ABS-O": "debt", "ABS-APCP": "debt", "SN": "debt", "RA": "debt",

    "STIV": "cash", "CASH": "cash",

    "DE": "other", "DIR": "other", "DCR": "other", "DCO": "other",
    "DFE": "other", "DO": "other", "OTHER": "other",
}

RULES = [
    ("A >=30", lambda p: p >= 30),   # SS 21 3/19, 2015 compilation
    ("B >50",  lambda p: p > 50),    # SS 59 8/2/2, 2018
    ("C >=33", lambda p: p >= 33),   # SS 59 8/2/3 floor
]

DENOMS = [("gross", "gross"), ("total", "total_assets"), ("net", "net_assets")]
TREATMENTS = [(f"{d}/{'LT' if lt else 'as-filed'}", col, lt)
              for d, col in DENOMS for lt in (False, True)]


def main():
    con = duckdb.connect(DB, read_only=True)
    con.register("cls", pd.DataFrame(list(CLASSIFICATION.items()),
                                     columns=["cat", "bucket"]))

    df = con.sql("""
        WITH h AS (
            SELECT ACCESSION_NUMBER, ASSET_CAT, ISSUER_TYPE,
                   ABS(TRY_CAST(CURRENCY_VALUE AS DOUBLE)) AS v
            FROM FUND_REPORTED_HOLDING
        )
        SELECT
            f.SERIES_NAME                            AS fund,
            h.ACCESSION_NUMBER                       AS accession,
            MAX(TRY_CAST(f.TOTAL_ASSETS AS DOUBLE))  AS total_assets,
            MAX(TRY_CAST(f.NET_ASSETS AS DOUBLE))    AS net_assets,
            SUM(h.v)                                 AS gross,
            SUM(CASE WHEN c.bucket = 'tangible' THEN h.v ELSE 0 END) AS tangible,
            SUM(CASE WHEN h.ISSUER_TYPE = 'RF' AND h.ASSET_CAT = 'OTHER'
                     THEN h.v ELSE 0 END)            AS rf_wrapper
        FROM h
        JOIN FUND_REPORTED_INFO f USING (ACCESSION_NUMBER)
        LEFT JOIN cls c ON c.cat = h.ASSET_CAT
        GROUP BY 1, 2
    """).df()

    df = df[df.gross > 0].copy()
    n = len(df)
    print(f"{n:,} filings with positive gross holdings.\n")

    print("=" * 74)
    print("THE THREE DENOMINATORS COMPARED")
    print("=" * 74)
    for col in ("gross", "total_assets", "net_assets"):
        ok = df[col].notna() & (df[col] > 0)
        print(f"  {col:<14} usable for {ok.sum():>7,} of {n:,} filings "
              f"({100*ok.sum()/n:>5.1f}%)   median ${df.loc[ok, col].median():>15,.0f}")
    both = df.total_assets.notna() & (df.total_assets > 0) & \
           df.net_assets.notna() & (df.net_assets > 0)
    lev = df.loc[both, "total_assets"] / df.loc[both, "net_assets"]
    print(f"\n  total_assets / net_assets   median {lev.median():.3f}"
          f"   p90 {lev.quantile(.90):.3f}   p99 {lev.quantile(.99):.3f}"
          f"   max {lev.max():.1f}")
    print(f"  filings with liabilities above 10% of net assets: "
          f"{(lev > 1.10).sum():,} ({100*(lev > 1.10).mean():.1f}%)")

    # ---- the six treatments --------------------------------------------
    pct_cols = []
    for label, denom_col, lookthru in TREATMENTS:
        num = df.tangible + (df.rf_wrapper if lookthru else 0.0)
        den = df[denom_col] if denom_col != "gross" else df.gross
        usable = den.notna() & (den > 0)
        pct = (100 * num / den).where(usable)
        col = f"pct {label}"
        df[col] = pct
        pct_cols.append(col)
        for rule, test in RULES:
            df[f"{label} | {rule}"] = pct.map(
                lambda p: None if pd.isna(p) else ("PASS" if test(p) else "FAIL"))

    verdict_cols = [f"{t} | {r}" for t, _, _ in TREATMENTS for r, _ in RULES]

    print("\n" + "=" * 74)
    print("PASS RATE — 6 TREATMENTS x 3 THRESHOLDS")
    print("=" * 74)
    print(f"{'treatment':<18}" + "".join(f"{r:>16}" for r, _ in RULES)
          + f"{'median':>9}{'>100%':>8}")
    for label, _, _ in TREATMENTS:
        cells = ""
        for rule, _ in RULES:
            c = df[f"{label} | {rule}"]
            p, k = (c == "PASS").sum(), c.notna().sum()
            cells += f"{p:>9,} {100*p/k:>4.1f}%" if k else f"{'—':>16}"
        pc = df[f"pct {label}"]
        print(f"{label:<18}{cells}{pc.median():>8.1f}%{(pc > 100).sum():>8,}")

    # ---- leverage breaks the ratio -------------------------------------
    over = (df[pct_cols] > 100).any(axis=1)
    print(f"\n{over.sum():,} funds ({100*over.mean():.1f}%) return a tangible "
          f"ratio above 100% under at least one denominator.")
    print("A ratio above 100% means the fund holds more tangible assets than it")
    print("has equity — it is levered. AAOIFI's asset-composition tests assume")
    print("assets roughly equal equity and say nothing about this case.")

    # ---- disagreement ---------------------------------------------------
    scored = df[verdict_cols].notna().sum(axis=1)
    distinct = df[verdict_cols].apply(lambda r: len(set(r.dropna())), axis=1)
    df["contested"] = (distinct > 1) & (scored >= 2)
    df["spread"] = df[pct_cols].max(axis=1) - df[pct_cols].min(axis=1)

    size = df.net_assets.where(df.net_assets > 0, df.gross)
    c = df.contested.sum()
    print("\n" + "=" * 74)
    print("DISAGREEMENT")
    print("=" * 74)
    print(f"{c:,} of {(scored >= 2).sum():,} funds "
          f"({100*c/(scored >= 2).sum():.1f}%) get both a PASS and a FAIL "
          f"somewhere in the 18 cells.")
    print(f"They hold ${size[df.contested].sum()/1e12:,.2f}T of "
          f"${size.sum()/1e12:,.2f}T.")

    capped = df.spread.clip(upper=100)
    print(f"\nspread, capped at 100 pts to exclude levered funds:")
    print(f"  median {capped.median():.1f}   p90 {capped.quantile(.9):.1f}"
          f"   p99 {capped.quantile(.99):.1f}")
    for t in (10, 20, 40):
        k = (df.spread > t).sum()
        print(f"  spread > {t:>2} pts: {k:>6,} funds   "
              f"${size[df.spread > t].sum()/1e9:>8,.0f}B")

    # ---- funds that flip every threshold --------------------------------
    allfail = df[pct_cols].max(axis=1)
    allpass = df[pct_cols].min(axis=1)
    total_flip = df[(allpass < 30) & (allfail > 50) & (allfail <= 100)]
    print("\n" + "=" * 74)
    print("FUNDS THAT GO FROM FAILING EVERY TEST TO PASSING EVERY TEST")
    print("=" * 74)
    print(f"{len(total_flip):,} funds, "
          f"${size[total_flip.index].sum()/1e9:,.0f}B.\n")
    print(f"  {'fund':<42}{'low':>7}{'high':>7}{'spread':>8}{'size':>10}")
    for i in size[total_flip.index].nlargest(15).index:
        r = df.loc[i]
        print(f"  {str(r.fund)[:40]:<42}{allpass[i]:>6.1f}%{allfail[i]:>6.1f}%"
              f"{r.spread:>7.1f}p{size[i]/1e9:>9.1f}B")

    df.to_csv("denominators_summary.csv", index=False)
    long = []
    for label, _, _ in TREATMENTS:
        for rule, _ in RULES:
            s = df[["fund", "accession"]].copy()
            s["treatment"], s["rule"] = label, rule
            s["tangible_pct"] = df[f"pct {label}"].round(2)
            s["verdict"] = df[f"{label} | {rule}"]
            long.append(s)
    pd.concat(long).to_csv("denominators_detail.csv", index=False)
    print("\nwrote denominators_summary.csv and denominators_detail.csv")


if __name__ == "__main__":
    main()
