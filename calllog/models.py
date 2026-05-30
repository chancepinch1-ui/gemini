"""통화기록 데이터 모델."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

# 통화 분류(관리자가 필터링/통계에 사용)
CATEGORIES = ("문의", "상담", "불만", "계약", "AS", "기타")

# 통화 방향(수발신 종류) — 안드로이드 통화기록의 type 과 매핑
DIRECTIONS = ("수신", "발신", "부재중", "기타")


@dataclass
class CallLog:
    id: Optional[int]
    employee: str             # 직원명
    customer: str             # 고객명
    phone: str                # 전화번호
    content: str              # 통화내용 (메모, 선택)
    category: str             # 분류 (CATEGORIES 중 하나)
    direction: str            # 수신/발신/부재중/기타
    duration_sec: int         # 통화 시간(초)
    audio_filename: str       # 녹음 파일명 (없으면 빈 문자열)
    audio_mime: str           # 녹음 MIME 타입
    called_at: str            # 통화 일시 (ISO 문자열)
    created_at: str           # 기록 등록 일시 (ISO 문자열)

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_filename)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee": self.employee,
            "customer": self.customer,
            "phone": self.phone,
            "content": self.content,
            "category": self.category,
            "direction": self.direction,
            "duration_sec": self.duration_sec,
            "has_audio": self.has_audio,
            "audio_filename": self.audio_filename,
            "audio_mime": self.audio_mime,
            "called_at": self.called_at,
            "created_at": self.created_at,
        }
