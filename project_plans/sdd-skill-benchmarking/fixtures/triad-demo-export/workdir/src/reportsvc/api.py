"""HTTP handlers for reportsvc (fixture stub)."""
from . import store


def usage_report(account_id: str, month: str) -> dict:
    return store.query_usage(account_id, month)
