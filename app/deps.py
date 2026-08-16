"""Dependency injection for the DB connection.

One function, `Depends()`'d into every route.
Yields a plain psycopg connection -- routes stay `def`, not `async def`,
because psycopg's sync driver is blocking (see main.py for why that matters).
"""
import os
from collections.abc import Iterator

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://lbrpit:lbrpit@localhost:5432/lbrpit")


def get_db() -> Iterator[psycopg.Connection]:
    with psycopg.connect(DATABASE_URL) as conn:
        yield conn
