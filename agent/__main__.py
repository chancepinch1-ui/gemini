"""Entry point: `python -m agent`.

Runs the scheduler on a background thread and serves the dashboard
on the main thread. Ctrl+C (or SIGTERM) shuts both down cleanly.
"""

import signal
import sys
import threading

from .config import Config
from .scheduler import Scheduler
from .state import AgentState
from .web import address, make_server


def main() -> int:
    cfg = Config.from_env()
    state = AgentState(history_size=cfg.history_size, log_size=cfg.log_size)
    scheduler = Scheduler(state, cfg.interval_seconds)
    httpd = make_server(state, scheduler, cfg.host, cfg.port)

    stop = threading.Event()

    def shutdown(*_args) -> None:
        if stop.is_set():
            return
        stop.set()
        state.log("shutdown signal received")
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    scheduler.start()
    host, port = address(httpd)
    print(f"agent: dashboard on http://{host}:{port}  (interval={cfg.interval_seconds}s)")
    state.log(f"dashboard listening on http://{host}:{port}")

    try:
        httpd.serve_forever(poll_interval=0.5)
    finally:
        scheduler.stop()
        httpd.server_close()
        print("agent: stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
