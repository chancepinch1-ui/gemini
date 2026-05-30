"""SQLite 저장 계층.

모든 직원의 통화기록을 단일 SQLite 파일에 모아 관리자가 통합 조회할 수 있게 합니다.
표준 라이브러리 sqlite3만 사용하며, 스레드 안전을 위해 호출마다 커넥션을 엽니다.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import CallLog

_SCHEMA = """
CREATE TABLE IF NOT EXISTS call_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee    TEXT NOT NULL,
    customer    TEXT NOT NULL,
    phone       TEXT NOT NULL,
    content     TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT '기타',
    called_at   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_call_logs_employee ON call_logs(employee);
CREATE INDEX IF NOT EXISTS idx_call_logs_called_at ON call_logs(called_at);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def add(
        self,
        employee: str,
        customer: str,
        phone: str,
        content: str,
        category: str = "기타",
        called_at: Optional[str] = None,
    ) -> int:
        now = _now_iso()
        called = called_at or now
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO call_logs "
                "(employee, customer, phone, content, category, called_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (employee, customer, phone, content, category, called, now),
            )
            return int(cur.lastrowid)

    def list(
        self,
        employee: Optional[str] = None,
        category: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 500,
    ) -> List[CallLog]:
        """필터 조건에 맞는 통화기록을 최신순으로 반환."""
        where: List[str] = []
        params: List[Any] = []
        if employee:
            where.append("employee = ?")
            params.append(employee)
        if category:
            where.append("category = ?")
            params.append(category)
        if query:
            where.append(
                "(customer LIKE ? OR phone LIKE ? OR content LIKE ? OR employee LIKE ?)"
            )
            like = f"%{query}%"
            params.extend([like, like, like, like])

        sql = "SELECT * FROM call_logs"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY called_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_log(r) for r in rows]

    def get(self, log_id: int) -> Optional[CallLog]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM call_logs WHERE id = ?", (log_id,)
            ).fetchone()
        return self._row_to_log(row) if row else None

    def delete(self, log_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM call_logs WHERE id = ?", (log_id,))
            return cur.rowcount > 0

    def employees(self) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT employee FROM call_logs ORDER BY employee"
            ).fetchall()
        return [r["employee"] for r in rows]

    def stats(self) -> Dict[str, Any]:
        """관리자 대시보드용 집계: 총 건수, 직원별/분류별 건수, 오늘 건수."""
        today = _now_iso()[:10]
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM call_logs").fetchone()["c"]
            today_count = conn.execute(
                "SELECT COUNT(*) AS c FROM call_logs WHERE substr(called_at,1,10) = ?",
                (today,),
            ).fetchone()["c"]
            by_employee = [
                {"employee": r["employee"], "count": r["c"]}
                for r in conn.execute(
                    "SELECT employee, COUNT(*) AS c FROM call_logs "
                    "GROUP BY employee ORDER BY c DESC"
                ).fetchall()
            ]
            by_category = [
                {"category": r["category"], "count": r["c"]}
                for r in conn.execute(
                    "SELECT category, COUNT(*) AS c FROM call_logs "
                    "GROUP BY category ORDER BY c DESC"
                ).fetchall()
            ]
        return {
            "total": total,
            "today": today_count,
            "by_employee": by_employee,
            "by_category": by_category,
        }

    @staticmethod
    def _row_to_log(row: sqlite3.Row) -> CallLog:
        return CallLog(
            id=row["id"],
            employee=row["employee"],
            customer=row["customer"],
            phone=row["phone"],
            content=row["content"],
            category=row["category"],
            called_at=row["called_at"],
            created_at=row["created_at"],
        )
