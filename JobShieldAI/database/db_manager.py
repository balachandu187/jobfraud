"""
Database Management Module for JobShield AI
Handles SQLite persistence for job advertisement scan logs, summary metrics,
and scan history retrieval/deletion.

The schema is versioned via ``PRAGMA user_version`` so an existing database created by
an older build is migrated in place instead of crashing on a missing column.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "jobshield.db")

SCHEMA_VERSION = 2

#: Columns present in schema v1, in creation order.
_V1_COLUMNS = (
    "id INTEGER PRIMARY KEY AUTOINCREMENT",
    "timestamp TEXT NOT NULL",
    "job_title TEXT",
    "company_name TEXT",
    "job_text TEXT NOT NULL",
    "prediction TEXT NOT NULL",
    "risk_score INTEGER NOT NULL",
    "risk_level TEXT NOT NULL",
    "warning_count INTEGER DEFAULT 0",
    "warnings_json TEXT",
)

#: Columns added in schema v2 (URL provenance + provenance metadata).
_V2_EXTRA_COLUMNS = (
    ("source_url", "TEXT DEFAULT ''"),
    ("source_type", "TEXT DEFAULT 'text'"),
)


class DatabaseManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        #: Set when the original file was unusable and a fresh one was created.
        self.quarantined_path: Optional[str] = None
        self._init_db()

    # ------------------------------------------------------------------
    # Connection / schema
    # ------------------------------------------------------------------
    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection configured with row dictionary access."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        # Journal mode is a per-database setting, not a per-connection one; setting it
        # on every open is a write and fails on a read-only or damaged file.
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        return conn

    def health(self) -> Dict[str, Any]:
        """Cheap readiness probe used by /api/status."""
        try:
            with self._get_connection() as conn:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                count = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
            return {"ok": integrity == "ok", "integrity": integrity, "rows": count,
                    "path": self.db_path}
        except sqlite3.DatabaseError as exc:
            return {"ok": False, "error": str(exc), "path": self.db_path}

    def _quarantine_and_reset(self, reason: str) -> None:
        """
        Moves an unusable database file aside and starts a fresh one.

        The audit log is valuable but never important enough to prevent the application
        from starting, so a corrupt/locked file is preserved under a timestamped name
        for manual recovery instead of raising during import.
        """
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = f"{self.db_path}.corrupt-{stamp}"
        try:
            os.replace(self.db_path, backup)
            self.quarantined_path = backup
        except OSError:
            backup = None
        # WAL sidecars must go too, otherwise SQLite replays the bad journal.
        for suffix in ("-wal", "-shm"):
            try:
                os.remove(f"{self.db_path}{suffix}")
            except OSError:
                pass
        logger.error(
            "Database at %s was unusable (%s). Started a fresh audit log%s.",
            self.db_path, reason,
            f"; original preserved at {backup}" if backup else "",
        )

    def _init_db(self) -> None:
        """Creates the table if absent, then applies any pending migrations."""
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        try:
            self._create_schema()
        except sqlite3.DatabaseError as exc:
            self._quarantine_and_reset(str(exc))
            self._create_schema()

    def _create_schema(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS scans ("
                + ", ".join(_V1_COLUMNS)
                + ")"
            )
            cursor.execute("PRAGMA user_version")
            version = cursor.fetchone()[0]

            existing = {row["name"] for row in cursor.execute("PRAGMA table_info(scans)")}
            if version < 2:
                for column, definition in _V2_EXTRA_COLUMNS:
                    if column not in existing:
                        cursor.execute(f"ALTER TABLE scans ADD COLUMN {column} {definition}")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_risk_level ON scans(risk_level)")
            cursor.execute("PRAGMA user_version = %d" % SCHEMA_VERSION)
            conn.commit()

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------
    def save_scan(
        self,
        job_text: str,
        prediction: str,
        risk_score: int,
        risk_level: str,
        job_title: str = "",
        company_name: str = "",
        warnings: Optional[List[Dict[str, Any]]] = None,
        source_url: str = "",
        source_type: str = "text",
    ) -> int:
        """Inserts a new scan record and returns the generated row ID."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        warnings_str = json.dumps(warnings or [])
        warning_count = len(warnings or [])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scans (
                    timestamp, job_title, company_name, job_text,
                    prediction, risk_score, risk_level, warning_count, warnings_json,
                    source_url, source_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now, job_title, company_name, job_text,
                    prediction, int(risk_score), risk_level, warning_count, warnings_str,
                    source_url or "", source_type or "text",
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> Dict[str, Any]:
        record = dict(row)
        try:
            record["warnings"] = json.loads(record["warnings_json"]) if record.get("warnings_json") else []
        except (TypeError, ValueError):
            record["warnings"] = []
        record.pop("warnings_json", None)
        record.setdefault("source_url", "")
        record.setdefault("source_type", "text")
        return record

    def get_recent_scans(
        self,
        limit: int = 50,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves past scans ordered newest first, optionally filtered."""
        limit = max(1, min(int(limit or 50), 500))
        clauses: List[str] = []
        params: List[Any] = []

        if risk_level:
            clauses.append("risk_level = ?")
            params.append(risk_level)
        if search:
            clauses.append("(job_title LIKE ? OR company_name LIKE ? OR job_text LIKE ?)")
            needle = f"%{search}%"
            params.extend([needle, needle, needle])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        try:
            with self._get_connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT id, timestamp, job_title, company_name, job_text,
                           prediction, risk_score, risk_level, warning_count, warnings_json,
                           source_url, source_type
                    FROM scans
                    {where}
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    params,
                ).fetchall()
            return [self._row_to_record(row) for row in rows]
        except sqlite3.DatabaseError:
            # History is a convenience surface; never break the UI over it.
            return []

    def get_scan(self, scan_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
            return self._row_to_record(row) if row else None
        except sqlite3.DatabaseError:
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Calculates aggregated metrics for the dashboard.

        Degrades to zeroed metrics (plus ``storage_error``) rather than raising, so a
        damaged or locked database cannot take down the dashboard.
        """
        try:
            return self._compute_statistics()
        except sqlite3.DatabaseError as exc:
            return {
                "total_scans": 0, "low_risk_count": 0, "medium_risk_count": 0,
                "high_risk_count": 0, "average_risk_score": 0.0,
                "top_warnings": [], "trend_7d": [], "storage_error": str(exc),
            }

    def _compute_statistics(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            total = cursor.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
            low_risk = cursor.execute("SELECT COUNT(*) FROM scans WHERE risk_level = 'Low Risk'").fetchone()[0]
            med_risk = cursor.execute("SELECT COUNT(*) FROM scans WHERE risk_level = 'Medium Risk'").fetchone()[0]
            high_risk = cursor.execute("SELECT COUNT(*) FROM scans WHERE risk_level = 'High Risk'").fetchone()[0]
            avg_score = cursor.execute("SELECT AVG(risk_score) FROM scans").fetchone()[0]

            # Top triggered heuristics, used by the dashboard breakdown card.
            top_rules: List[Dict[str, Any]] = []
            for row in cursor.execute("SELECT warnings_json FROM scans WHERE warnings_json IS NOT NULL"):
                try:
                    for warning in json.loads(row["warnings_json"] or "[]"):
                        title = warning.get("title") or warning.get("id")
                        if not title:
                            continue
                        found = next((item for item in top_rules if item["title"] == title), None)
                        if found:
                            found["count"] += 1
                        else:
                            top_rules.append({"title": title, "count": 1})
                except (TypeError, ValueError):
                    continue
            top_rules.sort(key=lambda item: item["count"], reverse=True)

            # 7-day trend of scan volume, oldest first, zero-filled.
            trend: List[Dict[str, Any]] = []
            today = datetime.now().date()
            for offset in range(6, -1, -1):
                day = today - timedelta(days=offset)
                label = day.strftime("%Y-%m-%d")
                count = cursor.execute(
                    "SELECT COUNT(*) FROM scans WHERE date(timestamp) = ?", (label,)
                ).fetchone()[0]
                trend.append({"date": label, "count": count})

        return {
            "total_scans": total,
            "low_risk_count": low_risk,
            "medium_risk_count": med_risk,
            "high_risk_count": high_risk,
            "average_risk_score": round(avg_score, 1) if avg_score is not None else 0.0,
            "top_warnings": top_rules[:5],
            "trend_7d": trend,
        }

    # ------------------------------------------------------------------
    # Deletes
    # ------------------------------------------------------------------
    def delete_scan(self, scan_id: int) -> bool:
        """Deletes a single scan by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_history(self) -> bool:
        """Clears all scan history."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM scans")
            conn.commit()
        return True
