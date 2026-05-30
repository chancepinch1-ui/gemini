"""통화기록 데이터 모델."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

# 통화 분류(관리자가 필터링/통계에 사용)
CATEGORIES = ("문의", "상담", "불만", "계약", "AS", "기타")


@dataclass
class CallLog:
    id: Optional[int]
    employee: str       # 직원명
    customer: str       # 고객명
    phone: str          # 전화번호
    content: str        # 통화내용
    category: str       # 분류 (CATEGORIES 중 하나)
    called_at: str      # 통화 일시 (ISO 문자열)
    created_at: str     # 기록 등록 일시 (ISO 문자열)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee": self.employee,
            "customer": self.customer,
            "phone": self.phone,
            "content": self.content,
            "category": self.category,
            "called_at": self.called_at,
            "created_at": self.created_at,
        }
