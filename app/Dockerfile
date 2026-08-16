FROM python:3.12-slim

WORKDIR /srv

COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY etl ./etl

# entrypoint.sh runs the (idempotent) ETL against the CSVs mounted at /data,
# then starts the API -- so `docker compose up` alone satisfies the
# "no manual step" without a separate ETL invocation.
COPY app/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENV LBR_PIT_DATA_DIR=/data
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
