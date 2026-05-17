"""Thread-safe shared state.

The background scheduler writes here; the web dashboard reads here.
A single lock guards everything because the data is small and access
is infrequent (once per interval / per HTTP request).
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional


@dataclass
class RunRecord:
    task: str
    started_at: float
    finished_at: float
    ok: bool
    detail: str

    @property
    def duration_ms(self) -> int:
        return int((self.finished_at - self.started_at) * 1000)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "ok": self.ok,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AgentState:
    history_size: int = 50
    log_size: int = 200

    started_at: float = field(default_factory=time.time)
    running: bool = True
    run_count: int = 0
    last_run: Optional[RunRecord] = None
    next_run_at: Optional[float] = None

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _history: Deque[RunRecord] = field(default_factory=deque, repr=False)
    _logs: Deque[str] = field(default_factory=deque, repr=False)

    def log(self, message: str) -> None:
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}"
        with self._lock:
            self._logs.append(line)
            while len(self._logs) > self.log_size:
                self._logs.popleft()

    def record_run(self, record: RunRecord) -> None:
        with self._lock:
            self.run_count += 1
            self.last_run = record
            self._history.append(record)
            while len(self._history) > self.history_size:
                self._history.popleft()

    def set_next_run(self, when: Optional[float]) -> None:
        with self._lock:
            self.next_run_at = when

    def set_running(self, running: bool) -> None:
        with self._lock:
            self.running = running

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            history: List[Dict[str, Any]] = [r.to_dict() for r in self._history]
            logs = list(self._logs)
            return {
                "started_at": self.started_at,
                "uptime_seconds": int(time.time() - self.started_at),
                "running": self.running,
                "run_count": self.run_count,
                "last_run": self.last_run.to_dict() if self.last_run else None,
                "next_run_at": self.next_run_at,
                "history": list(reversed(history)),
                "logs": list(reversed(logs)),
            }
