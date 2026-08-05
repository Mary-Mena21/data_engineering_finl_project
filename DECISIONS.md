# Five Choices — Defended

## 1. Source: OpenLibrary HTTP API

**Choice:** OpenLibrary `/subjects/science_fiction.json` endpoint.

**Why:** No API key required, which let me focus on pipeline mechanics instead of auth management. The endpoint returns rich JSON with nested arrays (authors, subjects) that gave me real data-cleaning practice. It returns 100 works per call — enough rows to make charts interesting, small enough to run fast while learning.

**Trade-off:** Rate limits exist and the API returns a broad mix of works, so publication years are scattered rather than showing a clean modern trend.

---

## 2. Raw Landing: RustFS (S3-compatible)

**Choice:** RustFS running in Docker on `localhost:9000`.

**Why:** The project requires raw bytes land in object storage before any transform. RustFS is lightweight — one container, zero cloud costs, and I can browse the console at `localhost:9001`. Date-keyed objects (`scifi_books_YYYY-MM-DD.json`) make re-runs safe and replayable.

---

## 3. Warehouse: DuckDB

**Choice:** DuckDB file (`data/warehouse.duckdb`) instead of Postgres.

**Why:** Zero server setup. It's a single file on disk — no Docker container to manage, no connection strings, no users or passwords. DuckDB's `read_json_auto()` made loading the bronze layer trivial. Columnar storage is fast for the aggregates in my gold layer.

**Trade-off:** DuckDB allows only one writer at a time. I solved this by creating a separate `data/serving/warehouse.duckdb` copy after dbt build, so Streamlit reads a read-only file while the pipeline can still write the main warehouse. If this were production with multiple concurrent users, I would switch to Postgres.

---

## 4. Transform: Medallion Layers in dbt

**Choice:** Bronze → Silver → Gold, orchestrated by dbt, triggered by Prefect.

**Why:** Required by the project, but also the right pattern for data lineage. Bronze holds the raw `works` array exactly as the API returned it. Silver unnests the array, extracts the first author, renames columns, and creates one row per book. Gold aggregates by author to answer the business question directly.

**Key tests:** `unique` and `not_null` on `work_key`, `not_null` on `title`, and `not_null` on `author_name` in gold. These catch duplicates and missing data before it reaches the dashboard.

---

## 5. Serving: Streamlit

**Choice:** Streamlit instead of Metabase.

**Why:** Code-first, runs with a single command (`streamlit run app.py`), and I could build two interactive views in one small Python file. For a solo learning project, Streamlit is lighter than Metabase + Docker + driver setup.

**Trade-off:** No saved questions, no user management, no scheduled email reports. But for two charts and a presentation, it is the right weight.