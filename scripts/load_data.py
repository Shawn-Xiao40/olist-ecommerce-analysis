"""Load the Olist CSV files into DuckDB and build the cleaned fact tables.

Usage:
    python scripts/load_data.py                        # read the real data from data/raw/
    python scripts/load_data.py --source data/sample   # read the synthetic sample data
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "processed" / "ecommerce.duckdb"
SQL_DIR = ROOT / "sql"

# raw table name -> Olist CSV file name
RAW_FILES = {
    "raw_customers": "olist_customers_dataset.csv",
    "raw_orders": "olist_orders_dataset.csv",
    "raw_order_items": "olist_order_items_dataset.csv",
    "raw_order_payments": "olist_order_payments_dataset.csv",
    "raw_order_reviews": "olist_order_reviews_dataset.csv",
    "raw_products": "olist_products_dataset.csv",
    "raw_sellers": "olist_sellers_dataset.csv",
    "raw_category_translation": "product_category_name_translation.csv",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/raw", help="CSV directory, relative to the project root")
    args = parser.parse_args()
    source = (ROOT / args.source).resolve()

    missing = [f for f in RAW_FILES.values() if not (source / f).exists()]
    if missing:
        raise SystemExit(
            f"Missing files in {source}:\n  " + "\n  ".join(missing)
            + "\nDownload the Olist dataset first (see README), "
              "or run scripts/make_sample_data.py to generate sample data."
        )

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    for table, filename in RAW_FILES.items():
        path = (source / filename).as_posix()
        con.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT * FROM read_csv_auto('{path}', header=true, sample_size=-1)"
        )
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<28} {n:>8,} rows")

    print("Building fact tables (sql/01_staging.sql) ...")
    con.execute((SQL_DIR / "01_staging.sql").read_text(encoding="utf-8"))
    for t in ("fct_orders", "fct_order_items"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<28} {n:>8,} rows")

    con.close()
    print(f"Done -> {DB_PATH}")


if __name__ == "__main__":
    main()
