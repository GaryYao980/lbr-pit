# ETL

Three loaders, one per table. All idempotent: natural key + `ON CONFLICT DO NOTHING`.
Run any of them twice in a row and row counts do not change on the second run.

```bash
export DATABASE_URL=postgresql://lbrpit:lbrpit@localhost:5432/lbrpit
python etl/load_futures.py
python etl/load_cot.py
python etl/load_fundamentals.py     # needs FRED_API_KEY, see README.md
```

`load_futures.py` and `load_cot.py` read their source CSVs from `./data` by
default (they ship in the repo). Set `LBR_PIT_DATA_DIR` only if you want to
point at CSVs somewhere else.

## Sources & licenses

| Table | Source | License / access |
|---|---|---|
| `futures_settle` | `data/lbr_term_structure_cme.csv` (CME Random Length Lumber settlements) | Public settlement data |
| `cot_obs` | `data/cot_lumber_clean.csv` (CFTC Commitments of Traders) | Public domain, CFTC.gov |
| `fundamental_obs` | FRED/ALFRED API (`HOUST`, `HOUST1F`, `PERMIT`, `MORTGAGE30US`, `WPU081`, `DEXCAUS`) | Free, requires a personal API key: https://fred.stlouisfed.org/docs/api/api_key.html |

## Known data issues, fixed or flagged (not hidden)

- **`lbr_term_structure_cme.csv`'s `note` column is unquoted and contains commas** ("zero volume, zero OI, ..."), which breaks a naive parse. `load_futures.py` splits each line on the first 7 commas only.
- **`cot_lumber_clean.csv`'s `date` is not always a Tuesday.** 2 of 297 rows (`2023-07-03`, `2025-11-10`) are Monday, because CFTC shifts the as-of date back a day whenever the usual Tuesday is a federal holiday (Independence Day, Veterans Day that year). `load_cot.py` derives `release_ts` as "the Friday of that report week" rather than a flat `+3 days`, which gets those two rows right; a flat offset does not.
- **`release_ts` is still an assumption, not a sourced fact.** It further assumes the release itself always lands on that Friday at 15:30 ET. 8 of 297 weeks have that Friday landing on a US federal holiday, when CFTC would in reality push the release to the next business day. Not corrected here (would need CFTC's actual release calendar, not just a holiday calendar) — flagged so nobody mistakes the demo for a claim that every timestamp in it is exact.
- **`FRED_API_KEY` unset** means `load_fundamentals.py` refuses to run and writes nothing — no synthetic fallback. `fundamental_obs` stays empty, and `/api/fundamentals/first` returns a `note` saying the loader hasn't run instead of a fabricated series. COT and futures loaders are unaffected.
- **COT history is 297 weeks (Jan 2021 – Jul 2026), not further back.** `annual2021.xls`…`annual2026.xls` (CFTC's raw legacy archives, checked during development but not shipped with this repo) were checked against `cot_lumber_clean.csv` and agree on coverage for the years both have — extending to 2010 would need `annual2010.xls`…`annual2020.xls`, which were never obtained.
- **Term structure is 3 trade dates** (`2026-07-23`, `07-27`, `07-29`). Deep CME historical settlement history is a paid feed, not something this repo has access to. Not fabricated here.

All of the above was validated against the real CSVs during exploration before being ported into this ETL. The counts in the repo README are from a real run, not illustrative.
