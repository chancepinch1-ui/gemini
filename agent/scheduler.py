"""Background scheduler running on its own thread."""

import threading
import time

from .state import AgentState, RunRecord
from .tasks import registry


class Scheduler:
    def __init__(self, state: AgentState, interval_seconds: int) -> None:
        self._state = state
        self._interval = max(1, interval_seconds)
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="agent-scheduler", daemon=True)

    def start(self) -> None:
        self._state.log(f"scheduler starting (interval={self._interval}s)")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=10)
        self._state.log("scheduler stopped")

    def trigger_now(self) -> None:
        """Ask the loop to run immediately instead of waiting for the interval."""
        self._wake.set()

    def _run_all(self) -> None:
        for name, fn in registry().items():
            started = time.time()
            try:
                detail = fn(self._state)
                self._state.record_run(
                    RunRecord(name, started, time.time(), True, detail)
                )
            except Exception as exc:  # noqa: BLE001 - surface any task failure
                self._state.log(f"[{name}] ERROR: {exc!r}")
                self._state.record_run(
                    RunRecord(name, started, time.time(), False, repr(exc))
                )

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._run_all()
            self._state.set_next_run(time.time() + self._interval)
            self._wake.wait(timeout=self._interval)
            self._wake.clear()
        self._state.set_running(False)
