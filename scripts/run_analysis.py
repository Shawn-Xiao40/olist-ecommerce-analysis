"""Run the analysis SQL files (sql/02_* onwards) to build the ana_* result tables and export them as CSV.

Usage:
    python scripts/run_analysis.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "processed" / "ecommerce.duckdb"
SQL_DIR = ROOT / "sql"
CSV_DIR = ROOT / "data" / "processed" / "csv"


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("Database not found. Run scripts/load_data.py first.")

    con = duckdb.connect(str(DB_PATH))
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        if sql_file.name.startswith("01_"):
            continue  # staging is handled by load_data.py
        print(f"Running {sql_file.name}")
        con.execute(sql_file.read_text(encoding="utf-8"))

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name LIKE 'ana_%' ORDER BY 1").fetchall()]
    for t in tables:
        out = (CSV_DIR / f"{t}.csv").as_posix()
        con.execute(f"COPY {t} TO '{out}' (HEADER, DELIMITER ',')")
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<32} {n:>6} rows")

    con.close()
    print(f"Done. CSV files exported to {CSV_DIR}")


if __name__ == "__main__":
    main()
