#!/usr/bin/env python3
"""통화녹음 업로드 예제 — 안드로이드 앱이 보낼 요청을 흉내 냅니다.

표준 라이브러리만 사용합니다. 안드로이드 앱(또는 PC 동기화 스크립트)이
OS 기본 전화앱의 녹음 파일을 서버로 올리는 방식을 그대로 보여줍니다.

사용법:
  python examples/upload_recording.py 녹음파일.m4a \\
      --server http://127.0.0.1:8770 \\
      --employee 홍길동 --phone 01012345678 --duration 42 \\
      --direction 수신 --api-key secret123
"""

import argparse
import json
import os
import urllib.parse
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser(description="통화녹음 + 메타데이터 업로드")
    p.add_argument("audio", help="업로드할 녹음 파일 경로")
    p.add_argument("--server", default="http://127.0.0.1:8770")
    p.add_argument("--employee", required=True, help="직원명")
    p.add_argument("--customer", default="")
    p.add_argument("--phone", default="")
    p.add_argument("--duration", type=int, default=0, help="통화 시간(초)")
    p.add_argument("--direction", default="기타", help="수신/발신/부재중/기타")
    p.add_argument("--category", default="기타")
    p.add_argument("--content", default="")
    p.add_argument("--called-at", default="", help="통화 일시 ISO8601")
    p.add_argument("--api-key", default="", help="서버에 키가 설정된 경우 필요")
    args = p.parse_args()

    with open(args.audio, "rb") as f:
        body = f.read()

    query = urllib.parse.urlencode({
        "employee": args.employee,
        "customer": args.customer,
        "phone": args.phone,
        "duration_sec": args.duration,
        "direction": args.direction,
        "category": args.category,
        "content": args.content,
        "called_at": args.called_at,
    })
    url = f"{args.server}/api/logs/upload?{query}"

    headers = {
        "Content-Type": "application/octet-stream",
        "X-Audio-Filename": os.path.basename(args.audio),
    }
    if args.api_key:
        headers["X-Api-Key"] = args.api_key

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    print(f"업로드 완료: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
