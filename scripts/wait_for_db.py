#!/usr/bin/env python3
"""Wait for the database to become available (used by CI).

Usage: python scripts/wait_for_db.py
Exits 0 when the database is reachable, 1 on timeout or error.
"""
import os
import sys
import time

import psycopg2


def main(timeout: int = 30) -> int:
    deadline = time.time() + timeout
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1

    while True:
        try:
            conn = psycopg2.connect(dsn)
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
