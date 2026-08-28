"""
Load data/qb_tiers.csv into data/qb_tiers.db (SQLite), table `qb_tiers`.

Run:
  python3 nfl/sources/qb_tiers/build_db.py
"""
import csv
import os
import sqlite3

HERE = os.path.dirname(__file__)
CSV_PATH = os.path.join(HERE, "data", "qb_tiers.csv")
DB_PATH = os.path.join(HERE, "data", "qb_tiers.db")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE qb_tiers (
            season          INTEGER NOT NULL,
            qb_name         TEXT NOT NULL,
            team            TEXT,
            tier            INTEGER NOT NULL,
            rank_in_season  INTEGER,
            source          TEXT NOT NULL,
            source_url      TEXT NOT NULL,
            PRIMARY KEY (season, qb_name, source)
        )
    """)

    with open(CSV_PATH) as f:
        reader = csv.DictReader(f)
        rows = [(
            int(r["season"]),
            r["qb_name"],
            r["team"] or None,
            int(r["tier"]),
            int(r["rank_in_season"]) if r["rank_in_season"] else None,
            r["source"],
            r["source_url"],
        ) for r in reader]

    cur.executemany("INSERT INTO qb_tiers VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM qb_tiers").fetchone()[0]
    conn.close()
    print(f"Wrote {n} rows to {DB_PATH}")


if __name__ == "__main__":
    main()
