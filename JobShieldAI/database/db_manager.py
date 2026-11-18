"""
Database Management Module for JobShield AI
Handles SQLite persistence for job advertisement scan logs, summary metrics,
and scan history retrieval/deletion.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "jobshield.db")

class DatabaseManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection configured with row dictionary access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables and indexes if not present."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    job_title TEXT,
                    company_name TEXT,
                    job_text TEXT NOT NULL,
                    prediction TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    risk_level TEXT NOT NULL,
                    warning_count INTEGER DEFAULT 0,
                    warnings_json TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_risk_level ON scans(risk_level)")

            # User Authentication and Access Management
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT DEFAULT 'analyst',
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            conn.commit()

    def create_user(self, email: str, password_hash: str, salt: str, full_name: str, role: str = "analyst") -> Optional[int]:
        """Creates a new user record. Returns user id or None if duplicate."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (email, password_hash, salt, full_name, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (email.lower().strip(), password_hash, salt, full_name.strip(), role, now))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves a user by email address."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, password_hash, salt, full_name, role, created_at
                FROM users
                WHERE email = ?
            """, (email.lower().strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves user profile by id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, full_name, role, created_at
                FROM users
                WHERE id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_scan(
        self,
        job_text: str,
        prediction: str,
        risk_score: int,
        risk_level: str,
        job_title: str = "",
        company_name: str = "",
        warnings: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Inserts a new scan record and returns the generated row ID."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        warnings_str = json.dumps(warnings or [])
        warning_count = len(warnings or [])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scans (
                    timestamp, job_title, company_name, job_text,
                    prediction, risk_score, risk_level, warning_count, warnings_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now, job_title, company_name, job_text,
                prediction, risk_score, risk_level, warning_count, warnings_str
            ))
            conn.commit()
            return cursor.lastrowid

    def get_recent_scans(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves past scans ordered by newest first."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, job_title, company_name, job_text,
                       prediction, risk_score, risk_level, warning_count, warnings_json
                FROM scans
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            
            records = []
            for r in rows:
                rec = dict(r)
                try:
                    rec["warnings"] = json.loads(rec["warnings_json"]) if rec["warnings_json"] else []
                except Exception:
                    rec["warnings"] = []
                records.append(rec)
            return records

    def get_statistics(self) -> Dict[str, Any]:
        """Calculates aggregated metrics for the dashboard."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM scans")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scans WHERE risk_level = 'Low Risk'")
            low_risk = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scans WHERE risk_level = 'Medium Risk'")
            med_risk = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scans WHERE risk_level = 'High Risk'")
            high_risk = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(risk_score) FROM scans")
            avg_score = cursor.fetchone()[0]
            avg_score = round(avg_score, 1) if avg_score is not None else 0.0

            return {
                "total_scans": total,
                "low_risk_count": low_risk,
                "medium_risk_count": med_risk,
                "high_risk_count": high_risk,
                "average_risk_score": avg_score
            }

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
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scans")
            conn.commit()
            return True

