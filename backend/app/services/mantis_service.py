"""
Service for reading Mantis issues from a SQLite database.
"""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple

from app.core.config import settings


class MantisService:
    """Provides read-only access to Mantis issues stored in SQLite."""

    TABLE_NAME = settings.MANTIS_TABLE_NAME

    # Columns exposed to the API. Their order controls the SELECT statement.
    COLUMNS = [
        "id",
        "issue_id",
        "project_id",
        "url",
        "category",
        "summary",
        "description",
        "steps_to_reproduce",
        "additional_information",
        "status",
        "resolution",
        "reporter_id",
        "priority",
        "severity",
        "date_submitted",
        "last_updated",
        "version",
        "fixed_in_version",
        "target_version",
        "bugnotes",
        "scraped_at",
    ]

    DEFAULT_SORT = "date_submitted"

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path or settings.MANTIS_DB_PATH)
        self._available_columns: List[str] = []

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Mantis database not found at {self.db_path}. Update MANTIS_DB_PATH or place the file at that location."
            )

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_available_columns(self, conn: sqlite3.Connection) -> List[str]:
        """Read available columns from the SQLite table and cache them."""
        if not self._available_columns:
            cursor = conn.execute(f"PRAGMA table_info({self.TABLE_NAME})")
            self._available_columns = [row[1] for row in cursor.fetchall() if row and len(row) > 1]

        if not self._available_columns:
            raise ValueError(f"Table {self.TABLE_NAME} has no columns")

        return self._available_columns

    def _build_filters(
        self,
        search: Optional[str],
        status: Optional[str],
        exclude_statuses: Optional[List[str]],
        priority: Optional[str],
        severity: Optional[str],
        category: Optional[str],
    ) -> Tuple[str, List[str]]:
        conditions: List[str] = []
        params: List[str] = []

        if search:
            conditions.append(
                "(" "summary LIKE ? OR description LIKE ? OR category LIKE ? OR issue_id LIKE ?" ")"
            )
            like = f"%{search}%"
            params.extend([like, like, like, like])

        if status:
            conditions.append("LOWER(status) = LOWER(?)")
            params.append(status)

        if exclude_statuses:
            placeholders = ", ".join("?" for _ in exclude_statuses)
            conditions.append(f"LOWER(status) NOT IN ({placeholders})")
            params.extend([value.lower() for value in exclude_statuses])

        if priority:
            conditions.append("LOWER(priority) = LOWER(?)")
            params.append(priority)

        if severity:
            conditions.append("LOWER(severity) = LOWER(?)")
            params.append(severity)

        if category:
            conditions.append("LOWER(category) = LOWER(?)")
            params.append(category)

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return where_clause, params

    def _validate_sort(
        self,
        sort_by: Optional[str],
        sort_order: Optional[str],
        available_columns: List[str],
    ) -> Tuple[str, str]:
        default_sort = self.DEFAULT_SORT if self.DEFAULT_SORT in available_columns else available_columns[0]
        sort_column = sort_by if sort_by in available_columns else default_sort
        order = "DESC" if (sort_order or "").lower() == "desc" else "ASC"
        return sort_column, order

    def _normalize_rows(self, rows: List[sqlite3.Row], available_columns: List[str]) -> List[Dict]:
        missing_columns = set(self.COLUMNS) - set(available_columns)

        normalized_rows: List[Dict] = []
        for row in rows:
            row_dict = dict(row)
            for column in missing_columns:
                row_dict.setdefault(column, None)
            normalized_rows.append(row_dict)

        return normalized_rows

    def list_issues(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        exclude_statuses: Optional[List[str]] = None,
        priority: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[Dict], int, Dict[str, int]]:
        offset = max(page - 1, 0) * page_size
        where_clause, params = self._build_filters(
            search,
            status,
            exclude_statuses,
            priority,
            severity,
            category,
        )
        select_columns: str

        with self._connect() as conn:
            available_columns = self._get_available_columns(conn)
            sort_column, order = self._validate_sort(sort_by, sort_order, available_columns)
            select_columns = ", ".join(available_columns)

            base_query = f"FROM {self.TABLE_NAME}{where_clause}"
            results_query = (
                f"SELECT {select_columns} {base_query} "
                f"ORDER BY {sort_column} {order} LIMIT ? OFFSET ?"
            )
            total_query = f"SELECT COUNT(*) {base_query}"

            cursor = conn.cursor()
            total = cursor.execute(total_query, params).fetchone()[0]
            rows = cursor.execute(results_query, [*params, page_size, offset]).fetchall()
            status_counts = cursor.execute(
                f"SELECT LOWER(status) as status, COUNT(*) as count {base_query} GROUP BY LOWER(status)",
                params,
            ).fetchall()

        normalized_counts = {row["status"]: row["count"] for row in status_counts}

        return self._normalize_rows(rows, available_columns), total, normalized_counts

    def list_all_issues(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        exclude_statuses: Optional[List[str]] = None,
        priority: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[Dict], int, Dict[str, int]]:
        where_clause, params = self._build_filters(
            search,
            status,
            exclude_statuses,
            priority,
            severity,
            category,
        )

        with self._connect() as conn:
            available_columns = self._get_available_columns(conn)
            sort_column, order = self._validate_sort(sort_by, sort_order, available_columns)
            select_columns = ", ".join(available_columns)

            base_query = f"FROM {self.TABLE_NAME}{where_clause}"
            results_query = f"SELECT {select_columns} {base_query} ORDER BY {sort_column} {order}"
            total_query = f"SELECT COUNT(*) {base_query}"

            cursor = conn.cursor()
            total = cursor.execute(total_query, params).fetchone()[0]
            rows = cursor.execute(results_query, params).fetchall()
            status_counts = cursor.execute(
                f"SELECT LOWER(status) as status, COUNT(*) as count {base_query} GROUP BY LOWER(status)",
                params,
            ).fetchall()

        normalized_counts = {row["status"]: row["count"] for row in status_counts}

        return self._normalize_rows(rows, available_columns), total, normalized_counts

    def get_issue(self, issue_id: int) -> Optional[Dict]:
        with self._connect() as conn:
            available_columns = self._get_available_columns(conn)
            select_columns = ", ".join(available_columns)
            query = f"SELECT {select_columns} FROM {self.TABLE_NAME} WHERE id = ?"

            row = conn.execute(query, (issue_id,)).fetchone()

        if not row:
            return None

        missing_columns = set(self.COLUMNS) - set(available_columns)
        issue = dict(row)
        for column in missing_columns:
            issue.setdefault(column, None)

        return issue

    def get_db_last_modified(self) -> str:
        """Return the database file's last modified timestamp in ISO format."""
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Mantis database not found at {self.db_path}. Update MANTIS_DB_PATH or place the file at that location."
            )

        modified_ts = self.db_path.stat().st_mtime
        return datetime.fromtimestamp(modified_ts, tz=timezone.utc).isoformat()


mantis_service = MantisService()
