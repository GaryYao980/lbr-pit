"""
Shared fixtures for the point-in-time test suite.

Tests run against a dedicated `lbrpit_test` database, never the `lbrpit`
database the app/ETL use -- that one may already hold real, decades-deep
ALFRED/CFTC history from a real loader run, which would silently swamp any
fixture-scoped assertion (a query has no way to know which rows are
"fixture" and which are "real"; it just returns everything that matches).
`lbrpit_test` is created automatically if it doesn't exist yet.

Every test in test_as_of.py / test_first_published.py / test_curve_order.py
runs inside a transaction that is always rolled back (`pg_conn`), so tests
never leave rows behind. test_idempotency.py runs the actual loaders, which
commit on their own -- that one uses `pg_conn_committing` plus a
truncate-before/truncate-after fixture instead.
"""
import os
import re
from pathlib import Path

import psycopg
import pytest

_DEFAULT_ADMIN_URL = "postgresql://lbrpit:lbrpit@localhost:5432/lbrpit"
ADMIN_DATABASE_URL = os.environ.get("DATABASE_URL", _DEFAULT_ADMIN_URL)
TEST_DB_NAME = "lbrpit_test"
DATABASE_URL = re.sub(r"/[^/]+$", f"/{TEST_DB_NAME}", ADMIN_DATABASE_URL)
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "db" / "schema.sql"


@pytest.fixture(scope="session")
def _schema():
    """Not autouse: the parser/scope tests need no database, and a reviewer who
    has just cloned the repo should be able to run those before starting Docker.
    Only the fixtures below pull this in."""
    with psycopg.connect(ADMIN_DATABASE_URL, autocommit=True) as admin_conn:
        exists = admin_conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,)
        ).fetchone()
        if not exists:
            admin_conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")

    # Idempotent (CREATE TABLE IF NOT EXISTS): safe to run every session.
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        for statement in SCHEMA_PATH.read_text().split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)


@pytest.fixture
def pg_conn(_schema):
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def pg_conn_committing(_schema):
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def clean_tables(pg_conn_committing):
    """For tests that run real loaders (which commit): start and end on a
    known-empty slate for the tables those loaders touch."""
    tables = "futures_settle, cot_obs, fundamental_obs"
    with pg_conn_committing.cursor() as cur:
        cur.execute(f"TRUNCATE {tables}")
    pg_conn_committing.commit()
    yield
    # A loader bug under test (e.g. a lost ON CONFLICT clause) can leave the
    # connection mid-aborted-transaction; roll back first so teardown can
    # still clean up instead of masking the real failure with a second one.
    pg_conn_committing.rollback()
    with pg_conn_committing.cursor() as cur:
        cur.execute(f"TRUNCATE {tables}")
    pg_conn_committing.commit()
