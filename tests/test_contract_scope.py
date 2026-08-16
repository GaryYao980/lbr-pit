"""
TEST 6 -- contract scope is a decision, and the loader keeps it that way.

The source file spans two CFTC contracts that overlapped for seven weeks and
disagree on the SIGN of commercial net positioning on every one of them.
`cot_obs` is keyed (report_date, series, revision) with no contract column, so
the two cannot coexist in it and the scope has to be stated somewhere.

These tests pin both halves of where it is stated: the scope rule, which keeps
the overlap out of the insert set entirely, and the guard, which raises if a
future source ever presents a collision the rule does not cover. Neither needs a
database, so they run on a fresh clone before Docker is started.
"""
from datetime import date

import pytest

from etl import load_cot

TWO_CONTRACTS_ONE_WEEK = """\
date,contract,oi,comm_net,nonc_net
2023-04-18,LUMBER,3304,-470,300
2023-04-18,RANDOM LENGTH LUMBER,1136,377,-200
2023-04-25,LUMBER,3400,-500,320
"""

SAME_CONTRACT_TWICE = """\
date,contract,oi,comm_net,nonc_net
2023-05-02,LUMBER,100,10,5
2023-05-02,LUMBER,200,-10,-5
"""

NO_CONTRACT_COLUMN = """\
date,oi,comm_net,nonc_net
2023-05-02,100,10,5
2023-05-09,110,11,6
"""


def _write(tmp_path, text):
    p = tmp_path / "cot.csv"
    p.write_text(text)
    return p


def test_overlap_week_cannot_reach_the_database(tmp_path):
    """The handover weeks fall outside scope, so the insert set contains no
    collision at all and the surviving row is the one the rule names."""
    rows = load_cot.parse_cot(_write(tmp_path, TWO_CONTRACTS_ONE_WEEK))

    assert {r[0] for r in rows} == {date(2023, 4, 25)}
    keys = [(r[0], r[2], r[4]) for r in rows]
    assert len(keys) == len(set(keys)), "a collision reached the insert set"


def test_duplicate_natural_key_raises_rather_than_being_absorbed(tmp_path):
    """Same contract, same date, twice -- a collision scope cannot resolve.
    The loader raises rather than delegating the choice to insert order."""
    with pytest.raises(load_cot.DuplicateNaturalKey) as e:
        load_cot.parse_cot(_write(tmp_path, SAME_CONTRACT_TWICE))
    assert "2023-05-02" in str(e.value)


def test_single_contract_file_passes_through(tmp_path):
    """A file with no contract column is a single-contract file; scope must not
    silently empty it."""
    rows = load_cot.parse_cot(_write(tmp_path, NO_CONTRACT_COLUMN))
    assert len(rows) == 2 * len(load_cot.SERIES_COLUMNS)


def test_real_source_is_collision_free_and_the_expected_size():
    """The shipped file, through the real path. 170 report dates x 3 series.
    This number appears in README.md -- if it moves, the README is now wrong."""
    rows = load_cot.parse_cot(load_cot.CSV_PATH)
    assert len(rows) == 510
    keys = [(r[0], r[2], r[4]) for r in rows]
    assert len(keys) == len(set(keys))
    assert min(r[0] for r in rows) == load_cot.CONTRACT_FROM
