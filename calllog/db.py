"""SQLite 저장 계층.

모든 직원의 통화기록을 단일 SQLite 파일에 모아 관리자가 통합 조회할 수 있게 합니다.
통화 녹음 파일은 별도 디렉터리에 저장하고, DB 에는 파일명만 보관합니다.
표준 라이브러리 sqlite3만 사용하며, 스레드 안전을 위해 호출마다 커넥션을 엽니다.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import CallLog

_SCHEMA = """
CREATE TABLE IF NOT EXISTS call_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    employee       TEXT NOT NULL,
    customer       TEXT NOT NULL DEFAULT '',
    phone          TEXT NOT NULL DEFAULT '',
    content        TEXT NOT NULL DEFAULT '',
    category       TEXT NOT NULL DEFAULT '기타',
    direction      TEXT NOT NULL DEFAULT '기타',
    duration_sec   INTEGER NOT NULL DEFAULT 0,
    audio_filename TEXT NOT NULL DEFAULT '',
    audio_mime     TEXT NOT NULL DEFAULT '',
    called_at      TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_call_logs_employee ON call_logs(employee);
CREATE INDEX IF NOT EXISTS idx_call_logs_called_at ON call_logs(called_at);
"""

# 기존 DB(초기 버전)에 추가된 컬럼을 채우기 위한 마이그레이션 목록
_MIGRATIONS = {
    "direction": "ALTER TABLE call_logs ADD COLUMN direction TEXT NOT NULL DEFAULT '기타'",
    "duration_sec": "ALTER TABLE call_logs ADD COLUMN duration_sec INTEGER NOT NULL DEFAULT 0",
    "audio_filename": "ALTER TABLE call_logs ADD COLUMN audio_filename TEXT NOT NULL DEFAULT ''",
    "audio_mime": "ALTER TABLE call_logs ADD COLUMN audio_mime TEXT NOT NULL DEFAULT ''",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


class Database:
    def __init__(self, path: str, recordings_dir: str = "recordings") -> None:
        self._path = path
        self._rec_dir = recordings_dir
        os.makedirs(self._rec_dir, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            existing = {r["name"] for r in conn.execute("PRAGMA table_info(call_logs)")}
            for column, ddl in _MIGRATIONS.items():
                if column not in existing:
                    conn.execute(ddl)

    # ---- 녹음 파일 저장 ----

    def save_recording(self, data: bytes, original_name: str) -> str:
        """녹음 바이트를 저장하고 저장된 파일명을 반환."""
        ext = os.path.splitext(original_name)[1].lower()[:8] or ".bin"
        stored = f"{uuid.uuid4().hex}{ext}"
        with open(os.path.join(self._rec_dir, stored), "wb") as f:
            f.write(data)
        return stored

    def recording_path(self, filename: str) -> Optional[str]:
        """경로 우회(.. 등)를 막고 실제 파일 경로를 반환."""
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            return None
        path = os.path.join(self._rec_dir, filename)
        return path if os.path.isfile(path) else None

    # ---- 기록 CRUD ----

    def add(
        self,
        employee: str,
        customer: str = "",
        phone: str = "",
        content: str = "",
        category: str = "기타",
        direction: str = "기타",
        duration_sec: int = 0,
        audio_filename: str = "",
        audio_mime: str = "",
        called_at: Optional[str] = None,
    ) -> int:
        now = _now_iso()
        called = called_at or now
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO call_logs "
                "(employee, customer, phone, content, category, direction, "
                " duration_sec, audio_filename, audio_mime, called_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (employee, customer, phone, content, category, direction,
                 int(duration_sec or 0), audio_filename, audio_mime, called, now),
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
        log = self.get(log_id)
        if log is None:
            return False
        with self._connect() as conn:
            conn.execute("DELETE FROM call_logs WHERE id = ?", (log_id,))
        # 연결된 녹음 파일도 함께 삭제
        if log.audio_filename:
            path = self.recording_path(log.audio_filename)
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass
        return True

    def employees(self) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT employee FROM call_logs ORDER BY employee"
            ).fetchall()
        return [r["employee"] for r in rows]

    def stats(self) -> Dict[str, Any]:
        """관리자 대시보드용 집계: 총 건수, 직원별/분류별 건수, 오늘 건수, 녹음 보유 건수."""
        today = _now_iso()[:10]
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM call_logs").fetchone()["c"]
            today_count = conn.execute(
                "SELECT COUNT(*) AS c FROM call_logs WHERE substr(called_at,1,10) = ?",
                (today,),
            ).fetchone()["c"]
            with_audio = conn.execute(
                "SELECT COUNT(*) AS c FROM call_logs WHERE audio_filename != ''"
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
            "with_audio": with_audio,
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
            direction=row["direction"],
            duration_sec=row["duration_sec"],
            audio_filename=row["audio_filename"],
            audio_mime=row["audio_mime"],
            called_at=row["called_at"],
            created_at=row["created_at"],
        )
