"""진입점: `python -m calllog`.

SQLite DB를 초기화하고 웹 서버를 띄웁니다. Ctrl+C 로 종료합니다.
"""

import signal
import sys
import threading

from .config import Config
from .db import Database
from .web import address, make_server


def main() -> int:
    cfg = Config.from_env()
    db = Database(cfg.db_path)
    httpd = make_server(db, cfg.host, cfg.port)

    stop = threading.Event()

    def shutdown(*_args) -> None:
        if stop.is_set():
            return
        stop.set()
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    host, port = address(httpd)
    print(f"통화기록 통합관리 시스템: http://{host}:{port}  (DB={cfg.db_path})")

    try:
        httpd.serve_forever(poll_interval=0.5)
    finally:
        httpd.server_close()
        print("종료되었습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
