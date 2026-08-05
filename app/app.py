# app/app.py
from pathlib import Path

import duckdb
import streamlit as st


@st.cache_data
def load_data():
    """Read gold tables from the serving copy."""
    serving_path = Path("data/serving/warehouse.duckdb")
    with duckdb.connect(str(serving_path), read_only=True) as con:
        authors = con.sql("""
            SELECT author_name, work_count, avg_editions, first_published
            FROM gold_author_stats
            ORDER BY work_count DESC
            LIMIT 20
        """).df()

        years = con.sql("""
            SELECT first_publish_year, COUNT(*) AS book_count
            FROM silver_books
            WHERE first_publish_year IS NOT NULL
            GROUP BY first_publish_year
            ORDER BY first_publish_year
        """).df()

    return authors, years


st.title("📚 OpenLibrary Science Fiction Dashboard")
st.caption("Built from bronze → silver → gold with dbt + Prefect")

# ---------- View 1: Top Authors ----------
st.header("1. Which authors have the most works?")
authors_df, _ = load_data()
st.bar_chart(authors_df.set_index("author_name")["work_count"])
st.dataframe(authors_df, use_container_width=True)

# ---------- View 2: Books by Year ----------
st.header("2. How many sci-fi books were published each year?")
_, years_df = load_data()
st.line_chart(years_df.set_index("first_publish_year")["book_count"])
st.dataframe(years_df, use_container_width=True)