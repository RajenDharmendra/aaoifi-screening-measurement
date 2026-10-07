# AAOIFI screening — measuring what an AI agent gets right

Four read-only tools that apply AAOIFI Shari'ah asset-composition standards to
SEC Form N-PORT fund filings, and a measured record of what an AI agent does
with the same question.

**Headline.** Six defensible readings of one AAOIFI test give 455 of 13,324 US
fund filings both a pass and a fail on the same threshold — $495 billion in net
assets. An AI agent asked for AAOIFI's tangible-asset threshold returned the
superseded figure as current and the current figure as "some scholars", in four
independent runs. Supplying the clause text corrected it completely. In one of
two runs where the text was available in the working directory, the agent never
opened it.

---

## What the standards actually say

Read from AAOIFI's published Shari'ah Standards, corroborated for SS 59 against
a third-party published copy.

| Clause | What it says | Threshold |
|---|---|---|
| SS 21 3/19 | Tangible assets as a share of total assets value (2015 compilation) | ≥ 30% |
| SS 21 3/4/2 | Debt as a share of market capitalisation | ≤ 30% |
| SS 21 3/4/3 | Interest-bearing deposits as a share of market cap of total equity | ≤ 30% |
| SS 21 3/4/4 | Prohibited income as a share of total income | ≤ 5% |
| SS 59 8/1 | Operating entity whose debts arise from business turnover | no ratio test |
| SS 59 8/2/2 | Ring-fenced vehicle not turned over on an ongoing basis | > 50% tangible |
| SS 59 8/2/3 | Floor for the same vehicle | ≥ 33% at all times |

SS 59 was issued 29 December 2018. Its Section 8 carries a footnote on the
section heading:

> this clause modifies the clauses 3/18 and 3/19 of shariah standard on
> commercial papers

That is the standard stating that Section 8 displaces SS 21 3/19 — not an
inference drawn from comparing two texts.

**AAOIFI's freely accessible gateway serves the 2015 compilation.** It carries
the superseded 30% figure and does not contain Standard 59, so a reader working
from the free text sees neither the current threshold nor the footnote saying
the old one was modified.

### A regulator renders 8/2/2 differently

The State Bank of Pakistan's adoption annex renders clause 8/2/2 as **"at least
33% of the value of the assets"** — not "exceed 50%". The likely explanation is
that the adoption text collapses 8/2/2 and the 8/2/3 floor into one line, but
that is an inference.

This is not a counterexample to the finding. It is the finding. The governing
text is transmitted inconsistently, and a model trained on whatever was
reachable reproduces the inconsistency while presenting it as settled.

---

## The three judgement calls

AAOIFI sets thresholds. It does not settle the inputs to them.

**What counts as tangible.** AAOIFI enumerates no N-PORT asset category. The
mapping in `denominators.py` is an interpretation; a different Shari'ah board
could legitimately differ on several lines.

**What the denominator is.** SS 21 3/19 says "total assets value… including all
assets, benefits, rights and cash liquidity". SS 59 8/2/2 says "the value of the
assets of the entity". Neither says *net* assets. An N-PORT filing offers three
figures that fit: gross reported holdings, the filer's `TOTAL_ASSETS`, and the
filer's `NET_ASSETS`. At the 99th percentile they differ by 2.6x.

**Whether to look through a held fund.** A fund held inside a fund files as
`ASSET_CAT: OTHER` with `ISSUER_TYPE: RF`. iShares Russell 2500 ETF holds 41% of
itself in iShares Russell 2000 ETF, filed exactly that way. Counting that as
equity, or not, moves the verdict.

Three denominators × two look-through settings × three thresholds = eighteen
defensible answers per fund.

---

## The scripts

All four open the database read-only and write nothing to it.

| Script | What it does |
|---|---|
| `cats.py` | Enumerates every `ASSET_CAT` against the classification map and names anything unmapped |
| `probe.py` | Schema and `ISSUER_TYPE` distribution; sizes the look-through exposure |
| `what.py` | Prints every field of a named fund's non-equity holdings |
| `denominators.py` | The six treatments across three thresholds; writes the summary and detail files |

```bash
python denominators.py nport.duckdb
```

The classification map and the three rules are literals at the top of
`denominators.py`. Change either and re-run; the verdicts move, which is the
point.

### Getting the data

SEC Form N-PORT structured data sets are published quarterly and are free.
Load the tab-delimited files into DuckDB. The run reported here used 13,324
filings and 5,105,506 holdings.

---

## Known defects in this analysis

Stated here because an analysis that hides its weak points does not survive
contact with someone looking for them.

**The look-through rule is binary, and that is the worst decision in it.**
Counting every `ISSUER_TYPE: RF` holding filed as `ASSET_CAT: OTHER` as equity
is right for a fund holding a pure equity ETF and wrong for a fund holding a
mix. Worse, it made 157 funds look undecidable that are not — resolving each
held fund against its own N-PORT filing in the same data set decides them at a
median unresolved value of 0.0%.

**Short positions are counted as positive assets.** Gross holdings are summed as
absolute reported value, so a short adds to the total rather than subtracting.
The fix is a one-line filter on `PAYOFF_PROFILE`. This error is not bounded.

**The 100% boundary is float-sensitive.** 898 filings are fully tangible under
at least one treatment, and land either side of 100 depending on floating-point
arithmetic.

**Scope.** One quarter, US registered funds only, asset composition only — not
debt ratios, prohibited income or purification, none of which N-PORT supports.

---

## What was measured, and how

Four agent runs. Sterile working directory containing the database and nothing
else. Network denied and the denial verified before each run. One question per
session, no steering, no corrections.

| Run | Clause text present | Agent read it? | Result |
|---|---|---|---|
| 1 — screening task | no | — | Wrong. 30% → SS 59; >50% called an older view |
| 2 — threshold | no | — | Wrong. Plus "SS 21 sets no firm percentage" |
| 3 — threshold | yes | no, until asked | Wrong → fully correct once read |
| 4 — threshold | yes | yes, unprompted | Correct |

**Zero of three correct without the text. Two of two correct with it. One of two
read it unprompted.**

The gap is not reasoning capability. On two counts the agent's data work was
better than the reference implementation here — it excluded short positions and
resolved fund-of-funds properly, both of which this analysis got wrong. The gap
is that the authoritative text was not in the room, and the model substituted
recollection.

### The part that matters commercially

In Run 3 the agent declared it could not look anything up while a document
answering the question sat one file search away in its own working directory.

Context has to be delivered and verified, not merely made available.

---

## What is not in this repository

- The N-PORT database. It is public SEC data, several hundred megabytes, and
  rebuildable from the source.
- Per-fund result files.
- The agent question set and its scoring key, withheld so that the questions
  remain usable as a measurement. Available on request.

---

## Licence

MIT. See `LICENSE`.

Nothing here is Shari'ah advice. The thresholds are quoted from published
standards; their application to any particular instrument is a matter for a
qualified Shari'ah board.
