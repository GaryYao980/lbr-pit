#!/bin/sh
set -e

echo "Waiting for postgres..."
until python -c "import psycopg, os; psycopg.connect(os.environ['DATABASE_URL']).close()" 2>/dev/null; do
  sleep 1
done

echo "Running ETL (idempotent -- safe on every container start)..."
python etl/load_futures.py
python etl/load_cot.py
python etl/load_fundamentals.py || echo "Skipping fundamentals load (see message above) -- COT and futures still start."

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
