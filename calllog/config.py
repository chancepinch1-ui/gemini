"""환경 변수로부터 읽어오는 설정.

기존 agent 모듈과 동일하게, 모든 설정은 기본값이 있는 단일 환경 변수입니다.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    db_path: str
    recordings_dir: str
    api_key: str  # 비어 있으면 업로드 인증을 요구하지 않음

    @staticmethod
    def from_env() -> "Config":
        return Config(
            host=os.environ.get("CALLLOG_HOST", "127.0.0.1"),
            port=int(os.environ.get("CALLLOG_PORT", "8770")),
            db_path=os.environ.get("CALLLOG_DB", "calllog.db"),
            recordings_dir=os.environ.get("CALLLOG_RECORDINGS", "recordings"),
            api_key=os.environ.get("CALLLOG_API_KEY", ""),
        )
