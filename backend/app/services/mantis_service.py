"""
Service for reading Mantis issues from a SQLite database.
"""
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

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Mantis database not found at {self.db_path}. Update MANTIS_DB_PATH or place the file at that location."
            )

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _build_filters(
        self,
        search: Optional[str],
        status: Optional[str],
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

    def _validate_sort(self, sort_by: Optional[str], sort_order: Optional[str]) -> Tuple[str, str]:
        sort_column = sort_by if sort_by in self.COLUMNS else self.DEFAULT_SORT
        order = "DESC" if (sort_order or "").lower() == "desc" else "ASC"
        return sort_column, order

    def list_issues(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Tuple[List[Dict], int]:
        offset = max(page - 1, 0) * page_size
        where_clause, params = self._build_filters(search, status, priority, severity, category)
        sort_column, order = self._validate_sort(sort_by, sort_order)

        select_columns = ", ".join(self.COLUMNS)
        base_query = f"FROM {self.TABLE_NAME}{where_clause}"
        results_query = (
            f"SELECT {select_columns} {base_query} "
            f"ORDER BY {sort_column} {order} LIMIT ? OFFSET ?"
        )
        total_query = f"SELECT COUNT(*) {base_query}"

        with self._connect() as conn:
            cursor = conn.cursor()
            total = cursor.execute(total_query, params).fetchone()[0]
            rows = cursor.execute(results_query, [*params, page_size, offset]).fetchall()

        return [dict(row) for row in rows], total

    def get_issue(self, issue_id: int) -> Optional[Dict]:
        select_columns = ", ".join(self.COLUMNS)
        query = f"SELECT {select_columns} FROM {self.TABLE_NAME} WHERE id = ?"

        with self._connect() as conn:
            row = conn.execute(query, (issue_id,)).fetchone()

        return dict(row) if row else None


mantis_service = MantisService()
