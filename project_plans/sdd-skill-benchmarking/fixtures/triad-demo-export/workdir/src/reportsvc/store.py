"""SQLite access for reportsvc (fixture stub). Tables: accounts, usage_events."""
import sqlite3


def connect(path: str = "reportsvc.db") -> sqlite3.Connection:
    return sqlite3.connect(path)


def query_usage(account_id: str, month: str) -> dict:
    return {"account_id": account_id, "month": month, "rows": []}
