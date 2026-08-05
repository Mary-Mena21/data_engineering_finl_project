# pipeline/load.py
from datetime import datetime
from pathlib import Path

import boto3
import duckdb
from dotenv import load_dotenv

load_dotenv()

RUSTFS_ENDPOINT = "http://localhost:9000"
RUSTFS_ACCESS_KEY = "rustfsadmin"
RUSTFS_SECRET_KEY = "rustfsadmin"
BUCKET_NAME = "raw"

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=RUSTFS_ENDPOINT,
        aws_access_key_id=RUSTFS_ACCESS_KEY,
        aws_secret_access_key=RUSTFS_SECRET_KEY,
        region_name="us-east-1",
    )

def download_from_rustfs(date_str: str) -> Path:
    s3 = get_s3_client()
    key = f"openlibrary/scifi_books_{date_str}.json"
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    local_path = temp_dir / f"scifi_books_{date_str}.json"
    
    print(f"Downloading s3://{BUCKET_NAME}/{key} ...")
    s3.download_file(Bucket=BUCKET_NAME, Key=key, Filename=str(local_path))
    print(f"Saved to: {local_path}")
    return local_path

def load_bronze(local_path: Path) -> None:
    db_path = Path("data/warehouse.duckdb")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))

    # DuckDB reads the JSON file directly much cleaner
    con.execute(f"""
        CREATE OR REPLACE TABLE bronze_openlibrary_books AS
        SELECT * FROM read_json_auto('{str(local_path).replace("\\", "/")}')
    """)

    count = con.execute("SELECT COUNT(*) FROM bronze_openlibrary_books").fetchone()[0]
    print(f"Bronze table loaded: {count} rows")
    con.close()

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print("=== Step 2: Load Bronze ===")
    local_path = download_from_rustfs(today)
    load_bronze(local_path)
    print("Done. Warehouse: data/warehouse.duckdb")

if __name__ == "__main__":
    main()