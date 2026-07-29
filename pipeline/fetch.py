# Day 1: Fetch & Land
# docker compose up -d (RustFS)
# fetch.py: fetch 1 page (100 books) from OpenLibrary, save to data/temp/books.json, upload to RustFS
# Verify in RustFS console
# https://openlibrary.org/subjects/sciencemathematics.json

# pipeline/fetch.py

import json          # Built-in library for parsing and writing JSON data
import os            # Built-in library for interacting with the operating system (not used directly here, but loaded for env vars)
from datetime import datetime   # Built-in module to get current date/time for filenames
from pathlib import Path        # Modern, object-oriented way to handle file system paths

import boto3         # AWS SDK for Python — used here to talk to S3-compatible storage (RustFS)
import httpx         # Modern HTTP client (like requests) to call the OpenLibrary API
from dotenv import load_dotenv  # Loads environment variables from a .env file into os.environ

load_dotenv()        # Execute: read .env file (if it exists) and inject variables into the environment

# ---------- Config ----------
# These are constants that configure the behavior of the script
RUSTFS_ENDPOINT = "http://localhost:9000"   # URL where your local RustFS (S3-compatible) instance is running
RUSTFS_ACCESS_KEY = "rustfsadmin"           # Username/key for authenticating with RustFS
RUSTFS_SECRET_KEY = "rustfsadmin"           # Password/secret for authenticating with RustFS
BUCKET_NAME = "raw"                         # S3 bucket name where raw data will be stored
SUBJECT = "sciencemathematics"              # OpenLibrary subject to search for
LIMIT = 100                                 # Number of books to fetch in one API call
# ----------------------------


# ---------- S3 Client ----------
def get_s3_client():
    """Return a boto3 client pointing at our local RustFS."""
    return boto3.client(
        "s3",                           # Service name: we're using S3 API compatibility
        endpoint_url=RUSTFS_ENDPOINT,   # Override AWS endpoint to point at local RustFS instead of Amazon
        aws_access_key_id=RUSTFS_ACCESS_KEY,      # Pass credentials for authentication
        aws_secret_access_key=RUSTFS_SECRET_KEY,  # Pass secret for authentication
        region_name="us-east-1",        # Required by boto3 even though RustFS ignores it (no real AWS regions in local)
    )


# ---------- Fetch ----------
# https://openlibrary.org/subjects/sciencemathematics.json?limit=100
def fetch_books() -> dict:
    """Download one page of books from OpenLibrary."""
    url = f"https://openlibrary.org/subjects/{SUBJECT}.json"  # Build the API URL dynamically from SUBJECT constant
    params = {"limit": LIMIT}            # Query parameters: ask API for 100 results only
    print(f"Fetching: {url}?limit={LIMIT}")  # Log what we're about to request (helpful for debugging)
    resp = httpx.get(url, params=params, timeout=30)  # Make HTTP GET request; wait max 30 seconds
    resp.raise_for_status()              # If status is 4xx or 5xx, raise an exception immediately (fail fast)
    data = resp.json()                   # Parse the JSON response body into a Python dictionary
    works = data.get("works", [])        # Safely extract the "works" list (the actual book records); default to empty list
    print(f"Received {len(works)} books") # Confirm how many books came back
    return data                          # Return the full API response dict (not just works)

# ---------- Save & Upload local ----------
# These functions are called by main()
#data/temp/math_books_2026-07-28.json
def save_local(data: dict) -> Path: 
    """Write raw JSON to disk so we can inspect it."""
    today = datetime.now().strftime("%Y-%m-%d")  # Get current date as string "2026-07-28"
    temp_dir = Path("data/temp")                   # Define the local directory path object
    temp_dir.mkdir(parents=True, exist_ok=True)   # Create directory (and any parent dirs) if they don't exist; don't error if already there
    filepath = temp_dir / f"math_books_{today}.json"  # Build full file path: data/temp/math_books_2026-07-28.json
    filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")  # Convert dict to pretty JSON string and write to file
    print(f"Saved locally: {filepath}")   # Confirm where the file was written
    return filepath                      # Return the path so the next function knows where to find it


# ---------- Upload to RustFS ----------
# openlibrary/math_books_2026-07-28.json
def upload_to_rustfs(filepath: Path) -> str:
    """Push the file to RustFS (S3) with a date key."""
    s3 = get_s3_client()                 # Initialize the S3 client connection

    # Create the bucket if this is the first run
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)  # Check if bucket exists (lightweight metadata check)
    except s3.exceptions.ClientError:       # If bucket doesn't exist, head_bucket throws an error
        s3.create_bucket(Bucket=BUCKET_NAME)  # Create the bucket on the fly
        print(f"Created bucket: {BUCKET_NAME}")  # Log the creation

    today = datetime.now().strftime("%Y-%m-%d")  # Get today's date again for the S3 key
    s3_key = f"openlibrary/math_books_{today}.json"  # Define the object path/key inside the bucket

    s3.upload_file(
        Filename=str(filepath),           # Local file path to read from
        Bucket=BUCKET_NAME,               # Target bucket
        Key=s3_key,                        # Target path/key inside the bucket
    )
    print(f"Uploaded to RustFS: s3://{BUCKET_NAME}/{s3_key}")  # Confirm upload location
    return s3_key                         # Return the key for reference/logging

# ---------- Main Function ----------
def main():
    print("=== Step 1: Fetch & Land ===")  # Header to show which pipeline stage is running
    data = fetch_books()                  # STEP 1: Call OpenLibrary API and get raw JSON
    filepath = save_local(data)           # STEP 2: Persist raw data to local disk (landing zone)
    upload_to_rustfs(filepath)            # STEP 3: Push the local file to object storage (RustFS/S3)
    print("All done. Check http://localhost:9001 to see your file.")  # Point user to RustFS web UI

if __name__ == "__main__":
    main()                                # Entry point: only run main() when script is executed directly (not imported)
    
    
    
    
# ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
# │  OpenLibrary    │────▶│  Your Computer │────▶│  RustFS Storage │
# │  (Internet)     │     │  data/temp/     │     │  Bucket: "raw"  │
# │  100 math books │     │  .json file     │     │  S3 object      │
# └─────────────────┘     └─────────────────┘     └─────────────────┘
#         fetch_books()        save_local()           upload_to_rustfs()

# Grabs 100 math books from the internet
# Saves a copy on your computer
# Uploads a copy to your storage bin (RustFS)