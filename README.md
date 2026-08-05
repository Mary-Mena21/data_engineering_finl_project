# OpenLibrary Sci-Fi Pipeline

A small end-to-end data engineering pipeline: fetch science-fiction book data from the
[OpenLibrary API](https://openlibrary.org/developers/api), land it in S3-compatible object
storage, load and model it with dbt on DuckDB, and serve it through a Streamlit dashboard
(with an optional Metabase connection).

```
OpenLibrary API → RustFS (raw/) → bronze (DuckDB) → dbt silver/gold → serving copy → Streamlit / Metabase
```

## Architecture

| Stage | Tool | What happens |
|---|---|---|
| Extract & land | `pipeline/fetch.py` | Pulls one page of `science_fiction` works from OpenLibrary, saves raw JSON locally, uploads it to RustFS (`s3://raw/openlibrary/...`) |
| Bronze load | `pipeline/load.py` | Downloads the day's JSON from RustFS and loads it as-is into `bronze_openlibrary_books` in `data/warehouse.duckdb` |
| Silver/gold | `dbt_project/` | `silver_books` unnests the raw `works` array into one row per book; `gold_author_stats` aggregates work counts/editions per author |
| Serving copy | `pipeline/flow.py` | Copies `data/warehouse.duckdb` to `data/serving/warehouse.duckdb` (read-only snapshot for the dashboard) |
| Orchestration | Prefect | `pipeline/flow.py` wires the steps above into one flow with retries |
| Dashboard | `app/app.py` (Streamlit) | Reads the serving copy: top authors by work count, books published per year |
| Optional BI | Metabase | Connects directly to `data/warehouse.duckdb` via the community DuckDB driver |

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package/dependency manager)
- [Docker](https://www.docker.com/) (for RustFS and, optionally, Metabase)

## Setup

```bash
uv sync
```

## Running it

**1. Start RustFS** (local S3-compatible object storage):

```bash
docker compose up -d rustfs
```

Console: http://localhost:9001 (`rustfsadmin` / `rustfsadmin`)

**2. Start a Prefect server** (the flow is orchestrated, not run ad hoc):

```bash
uv run prefect server start
```

Dashboard: http://127.0.0.1:4200

**3. Run the pipeline** (in a separate terminal):

```bash
uv run python pipeline/flow.py
```

This fetches fresh data, loads bronze, runs `dbt build` (silver views + gold tables + tests),
and publishes the serving copy.

**4. View the dashboard:**

```bash
uv run streamlit run app/app.py
```

Opens at http://localhost:8501.

**5. (Optional) Metabase:**

```bash
docker compose up -d metabase-driver-init metabase
```

Opens at http://localhost:3000. Connect a new DuckDB database pointing at `data/warehouse.duckdb`.
The `metabase` service builds from [metabase.Dockerfile](metabase.Dockerfile), which adds
`libstdc++`/`gcompat` on top of the base Alpine image — required for the community DuckDB
driver's native library to load.

## Project layout

```
pipeline/           Fetch, land, and bronze-load logic + the Prefect flow
dbt_project/         silver_books, gold_author_stats models and tests
app/app.py           Streamlit dashboard
data/warehouse.duckdb        Working DuckDB warehouse (bronze/silver/gold)
data/serving/warehouse.duckdb  Read-only snapshot the dashboard reads from
docker-compose.yml   RustFS + Metabase services
metabase.Dockerfile  Metabase image with DuckDB native-lib dependencies
```

## Scheduling

`pipeline/flow.py` has a commented-out `run_pipeline.serve(...)` call for a daily cron
deployment — uncomment it to run the pipeline on a schedule via the Prefect server instead
of triggering it manually.


## Stopping it
```
# 1. Stop ALL containers and delete their volumes
docker compose down -v

# 2. Delete the data folder (warehouse + serving copy + temp files)
rm -rf data/

# 3. Confirm it's gone
ls data/
```
## Final Checklist
```
# 1. Start RustFS
docker compose up -d

# 2. Verify RustFS is up
docker ps

# 3. Run the pipeline
uv run python pipeline/flow.py

# 4. View the dashboard
uv run streamlit run app/app.py

# 5. (Optional) Metabase
docker compose up -d metabase-driver-init metabase

# 6. Run the Prefect server
uv run prefect server start
```