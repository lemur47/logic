"""
Opt-in local estimation log (SQLite) — the calibration-memory storage layer.

Activated by the ``PMORUN_DB`` environment variable (a filesystem path). When the
variable is unset the server never touches this module at tool-call time and the
runtime stays fully stateless — the pre-calibration behaviour, unchanged.

Design constraints:

- **stdlib only.** ``sqlite3`` ships with CPython; the lean PyPI dependency set
  is untouched.
- **D1-portable schema.** Cloudflare D1 executes SQLite SQL, so this exact DDL
  is the rehearsal for the hosted calibration memory's data model: no SQLite
  extensions, no triggers, ISO-8601 TEXT timestamps, JSON packed into TEXT.
- **Self-contained rows.** ``pert_expected`` is materialised at write time so a
  row is a complete (estimated, actual) observation on its own — downstream
  analytics never need to re-run the estimator to interpret the log.
- **Connection per operation.** The stdio server is single-process and calls are
  short; opening per call avoids held locks and half-open state entirely.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

ENV_VAR = "PMORUN_DB"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS estimation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_category TEXT NOT NULL,
    description TEXT,
    tags TEXT,
    unit TEXT NOT NULL DEFAULT 'sessions',
    optimistic REAL NOT NULL,
    most_likely REAL NOT NULL,
    pessimistic REAL NOT NULL,
    pert_expected REAL NOT NULL,
    actual REAL,
    estimated_at TEXT NOT NULL,
    actual_recorded_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_estimation_log_category
    ON estimation_log (task_category);
"""


def db_path() -> str | None:
    """The configured log path, or ``None`` when persistence is off."""
    path = os.environ.get(ENV_VAR, "").strip()
    return path or None


def utc_now() -> str:
    """ISO-8601 UTC timestamp, seconds precision — the log's time format."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def insert_estimate(
    path: str,
    *,
    task_category: str,
    optimistic: float,
    most_likely: float,
    pessimistic: float,
    pert_expected: float,
    unit: str,
    description: str | None,
    tags: str | None,
) -> tuple[int, str]:
    """Insert a new estimate row; returns ``(row id, estimated_at)``."""
    now = utc_now()
    with closing(_connect(path)) as conn, conn:
        cursor = conn.execute(
            """
            INSERT INTO estimation_log
                (task_category, description, tags, unit,
                 optimistic, most_likely, pessimistic, pert_expected, estimated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_category,
                description,
                tags,
                unit,
                optimistic,
                most_likely,
                pessimistic,
                pert_expected,
                now,
            ),
        )
        row_id = cursor.lastrowid
    assert row_id is not None  # sqlite always assigns one on INSERT
    return row_id, now


def set_actual(path: str, estimate_id: int, actual: float) -> dict:
    """Record (or correct) the actual for an estimate; returns the full row.

    Raises ``KeyError`` when the id does not exist — the caller maps that to a
    structured tool error.
    """
    now = utc_now()
    with closing(_connect(path)) as conn, conn:
        cursor = conn.execute(
            "UPDATE estimation_log SET actual = ?, actual_recorded_at = ? WHERE id = ?",
            (actual, now, estimate_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"No estimate with id {estimate_id} in the log.")
        row = conn.execute("SELECT * FROM estimation_log WHERE id = ?", (estimate_id,)).fetchone()
    return dict(row)


def completed_pairs(path: str, task_category: str | None = None) -> list[dict]:
    """All rows with a recorded actual, oldest first (the Bayesian update is
    sequential, so observation order is preserved). Optionally one category."""
    query = "SELECT * FROM estimation_log WHERE actual IS NOT NULL"
    params: tuple = ()
    if task_category is not None:
        query += " AND task_category = ?"
        params = (task_category,)
    query += " ORDER BY id"
    with closing(_connect(path)) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def actuals_for_category(path: str, task_category: str) -> list[float]:
    """Recorded actual durations for one category, oldest first."""
    return [row["actual"] for row in completed_pairs(path, task_category)]
