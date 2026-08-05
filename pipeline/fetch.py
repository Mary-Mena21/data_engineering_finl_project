# pipeline/fetch.py
import json
import os
from datetime import datetime
from pathlib import Path

import boto3
import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------- Config ----------
RUSTFS_ENDPOINT = "http://localhost:9000"
RUSTFS_ACCESS_KEY = "rustfsadmin"
RUSTFS_SECRET_KEY = "rustfsadmin"
BUCKET_NAME = "raw"
SUBJECT = "science_fiction"
LIMIT = 100
# ----------------------------

def get_s3_client():
    """Return a boto3 client pointing at our local RustFS."""
    return boto3.client(
        "s3",
        endpoint_url=RUSTFS_ENDPOINT,
        aws_access_key_id=RUSTFS_ACCESS_KEY,
        aws_secret_access_key=RUSTFS_SECRET_KEY,
        region_name="us-east-1",  # RustFS ignores this, but boto3 needs it
    )

def fetch_books() -> dict:
    """Download one page of books from OpenLibrary."""
    url = f"https://openlibrary.org/subjects/{SUBJECT}.json"
    params = {"limit": LIMIT}
    print(f"Fetching: {url}?limit={LIMIT}")
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()  # crash loudly if the API is down
    data = resp.json()
    works = data.get("works", [])
    print(f"Received {len(works)} books")
    return data

def save_local(data: dict) -> Path:
    """Write raw JSON to disk so we can inspect it."""
    today = datetime.now().strftime("%Y-%m-%d")
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    filepath = temp_dir / f"scifi_books_{today}.json"
    filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved locally: {filepath}")
    return filepath

def upload_to_rustfs(filepath: Path) -> str:
    """Push the file to RustFS (S3) with a date key."""
    s3 = get_s3_client()

    # Create the bucket if this is the first run
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except s3.exceptions.ClientError:
        s3.create_bucket(Bucket=BUCKET_NAME)
        print(f"Created bucket: {BUCKET_NAME}")

    today = datetime.now().strftime("%Y-%m-%d")
    s3_key = f"openlibrary/scifi_books_{today}.json"

    s3.upload_file(
        Filename=str(filepath),
        Bucket=BUCKET_NAME,
        Key=s3_key,
    )
    print(f"Uploaded to RustFS: s3://{BUCKET_NAME}/{s3_key}")
    return s3_key

def main():
    print("=== Step 1: Fetch & Land ===")
    data = fetch_books()
    filepath = save_local(data)
    upload_to_rustfs(filepath)
    print("All done. Check http://localhost:9001 to see your file.")

if __name__ == "__main__":
    main()