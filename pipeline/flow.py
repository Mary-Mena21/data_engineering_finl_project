# pipeline/flow.py
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import shutil
from prefect import flow, task, get_run_logger

# Make imports work when running this file directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.fetch import fetch_books, save_local, upload_to_rustfs
from pipeline.load import download_from_rustfs, load_bronze


@task(retries=3, retry_delay_seconds=5)
def extract_and_land() -> str:
    """Fetch from OpenLibrary and land raw bytes in RustFS."""
    logger = get_run_logger()
    logger.info("Fetching data from OpenLibrary API")

    data = fetch_books()
    filepath = save_local(data)
    s3_key = upload_to_rustfs(filepath)

    today = datetime.now().strftime("%Y-%m-%d")
    logger.info("Landed raw data at s3://raw/%s", s3_key)
    return today


@task
def load_bronze_task(date_str: str) -> None:
    """Download from RustFS and load into DuckDB bronze table."""
    logger = get_run_logger()
    logger.info("Loading bronze for date: %s", date_str)

    local_path = download_from_rustfs(date_str)
    load_bronze(local_path)

    logger.info("Bronze loaded from %s", local_path)


@task
def dbt_build_task() -> None:
    """Run dbt build (models + tests)."""
    logger = get_run_logger()
    logger.info("Running dbt build...")

    dbt_exe = str(Path(sys.executable).parent / "dbt.exe")
    result = subprocess.run(
        [dbt_exe, "build", "--profiles-dir", "."],
        cwd="dbt_project",
        capture_output=True,
        text=True,
        check=False,
    )

    logger.info("dbt output:\n%s", result.stdout)
    if result.stderr:
        logger.warning("dbt stderr:\n%s", result.stderr)
    result.check_returncode()
    logger.info("dbt build completed successfully")


@task
def publish_serving_copy() -> None:
    """Copy warehouse to a read-only serving database for Streamlit."""
    logger = get_run_logger()
    logger.info("Creating serving copy...")

    serving_dir = Path("data/serving")
    serving_dir.mkdir(parents=True, exist_ok=True)
    serving_path = serving_dir / "warehouse.duckdb"

    # Remove old file first (Windows is picky about overwriting)
    if serving_path.exists():
        serving_path.unlink()

    shutil.copy("data/warehouse.duckdb", serving_path)
    logger.info("Serving copy ready at %s", serving_path)


@flow(log_prints=True)
def run_pipeline():
    """End-to-end pipeline: extract → land → bronze → dbt → serving copy."""
    logger = get_run_logger()
    logger.info("========== Pipeline Start ==========")

    date_str = extract_and_land()
    load_bronze_task(date_str)
    dbt_build_task()
    publish_serving_copy()

    logger.info("========== Pipeline Complete ==========")

if __name__ == "__main__":
    # -------------------------------------------------
    # STEP A — MANUAL TEST (run this first)
    # -------------------------------------------------
    # run_pipeline()

    # -------------------------------------------------
    # STEP B — SCHEDULED DEPLOYMENT (uncomment after
    # manual test works, then run this file again)
    # -------------------------------------------------
    run_pipeline.serve(name="final-project", cron="0 6 * * *")
    # -------------------------------------------------
    # uv run python pipeline/flow.py