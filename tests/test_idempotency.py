"""
TEST 5 -- loaders are idempotent.

Each loader's real network/file dependency is swapped for deterministic
fixture data (a tiny temp CSV for the two file-based loaders, a monkeypatched
fetch for the FRED/ALFRED one -- never the real CSVs, never a real API call),
then run twice against a truncated table. Row counts must be identical on
the second run: natural key + ON CONFLICT DO NOTHING, proven, not asserted.
"""
from etl import load_cot, load_fundamentals, load_futures

FUTURES_CSV = """trade_date,month,settle,change,volume,open_interest,no_trade_flag,note
2026-07-29,SEP26,634.0,1.5,1011,7123,0,
2026-07-29,NOV26,635.0,1.0,88,1045,0,
"""

COT_CSV = """date,oi,comm_net,nonc_net
2026-01-06,5000,100,50
2026-01-13,5100,110,55
"""


def test_load_futures_is_idempotent(tmp_path, monkeypatch, pg_conn_committing, clean_tables):
    csv_path = tmp_path / "lbr_term_structure_cme.csv"
    csv_path.write_text(FUTURES_CSV)
    monkeypatch.setattr(load_futures, "CSV_PATH", csv_path)

    before1, after1 = load_futures.load(pg_conn_committing)
    before2, after2 = load_futures.load(pg_conn_committing)

    assert before1 == 0
    assert after1 == 2
    assert (before2, after2) == (2, 2)


def test_load_cot_is_idempotent(tmp_path, monkeypatch, pg_conn_committing, clean_tables):
    csv_path = tmp_path / "cot_lumber_clean.csv"
    csv_path.write_text(COT_CSV)
    monkeypatch.setattr(load_cot, "CSV_PATH", csv_path)

    before1, after1 = load_cot.load(pg_conn_committing)
    before2, after2 = load_cot.load(pg_conn_committing)

    assert before1 == 0
    assert after1 == 6  # 2 rows x 3 series columns (oi, comm_net, nonc_net)
    assert (before2, after2) == (6, 6)


def test_load_fundamentals_is_idempotent(monkeypatch, pg_conn_committing, clean_tables):
    def fake_fetch_alfred(series_id, api_key):
        return [(series_id, "2026-04-01", "2026-05-18", 1310.0)]

    monkeypatch.setattr(load_fundamentals, "fetch_alfred", fake_fetch_alfred)

    before1, after1 = load_fundamentals.load(pg_conn_committing)
    before2, after2 = load_fundamentals.load(pg_conn_committing)

    assert before1 == 0
    assert after1 == len(load_fundamentals.SERIES_IDS)  # one row per series
    assert (before2, after2) == (after1, after1)
