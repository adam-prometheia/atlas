#!/usr/bin/env python3
"""Wait for the database to become available (used by CI).

Usage: python scripts/wait_for_db.py
Exits 0 when the database is reachable, 1 on timeout or error.
"""
import os
import sys
import time

import psycopg2
from sqlalchemy.engine import make_url


def main(timeout: int = 30) -> int:
    deadline = time.time() + timeout
    url_value = os.environ.get("DATABASE_URL")
    if not url_value:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1

    try:
        url = make_url(url_value)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Invalid DATABASE_URL: {exc}", file=sys.stderr)
        return 1

    if not url.drivername.startswith("postgresql"):
        print("wait_for_db only supports PostgreSQL URLs.", file=sys.stderr)
        return 1

    connect_kwargs = {
        "dbname": url.database,
        "user": url.username,
        "password": url.password,
        "host": url.host or "localhost",
        "port": url.port or 5432,
    }
    connect_kwargs = {k: v for k, v in connect_kwargs.items() if v}

    while True:
        try:
            conn = psycopg2.connect(**connect_kwargs)
            conn.close()
            print("Database is ready")
            return 0
        except psycopg2.OperationalError:
            if time.time() > deadline:
                print("Timed out waiting for database", file=sys.stderr)
                return 1
            time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
