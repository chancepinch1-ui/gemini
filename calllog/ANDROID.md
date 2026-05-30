# 안드로이드 통화녹음 자동 업로드 연동 가이드

OS 기본 전화앱이 저장한 **통화녹음 파일**을 안드로이드 앱이 백그라운드에서 스캔하여
서버로 자동 업로드하는 방식의 규격입니다.

> ⚠️ **아이폰은 지원 불가**
> iOS 기본 전화앱에는 통화녹음 기능이 없고, 앱 샌드박스 때문에 다른 앱/시스템 파일에
> 접근할 수 없습니다. 아이폰 사용자는 웹의 **"통화 입력"** 탭으로 수동 입력해야 합니다.

> ⚖️ **법적 유의** 통화 녹음·수집은 지역 법령과 사내 규정의 적용을 받습니다.
> 통화 당사자 동의, 근로자 고지·동의, 보관 기간 등을 반드시 사전에 검토하세요.

---

## 1. 안드로이드 측에서 필요한 것

### 권한
- `android.permission.READ_CALL_LOG` — 번호·상대 이름·통화 시각·통화 시간·수발신 종류
- `android.permission.READ_CONTACTS` — 번호를 고객명으로 변환(선택)
- `android.permission.MANAGE_EXTERNAL_STORAGE` — 녹음 폴더 접근(안드로이드 11+에서 필요한
  "모든 파일 접근"). Play스토어 정식 배포는 제한되므로 **사내 배포(사이드로드/MDM)** 권장.
- `android.permission.INTERNET`

### 녹음 파일이 저장되는 대표 폴더 (기기 제조사별 상이)
```
/storage/emulated/0/Call/
/storage/emulated/0/Recordings/Call/
/storage/emulated/0/Sounds/CallRecordings/
/storage/emulated/0/MIUI/sound_recorder/call_rec/   (샤오미)
```
파일명에 보통 상대 번호와 타임스탬프가 포함됩니다
(예: `Call recording 01012345678_260530_103000.m4a`).

### 동작 흐름 (앱이 주기적으로 / 통화 종료 후)
1. `CallLog.Calls` 콘텐츠 프로바이더로 최근 통화(번호·시각·통화시간·type) 조회
2. 녹음 폴더에서 신규 파일을 찾아 통화기록과 매칭(번호·시각 근접도)
3. 아직 업로드하지 않은 항목을 서버 업로드 API로 전송
4. 성공한 항목 ID를 로컬에 기록해 중복 업로드 방지

`CallLog.Calls.TYPE` 매핑: `INCOMING_TYPE→수신`, `OUTGOING_TYPE→발신`,
`MISSED_TYPE→부재중`, 그 외 `기타`.

---

## 2. 서버 업로드 API

```
POST /api/logs/upload?<메타데이터 쿼리스트링>
Header: X-Api-Key: <CALLLOG_API_KEY>          # 서버에 키를 설정한 경우 필수
Header: X-Audio-Filename: <원본 파일명.m4a>     # 확장자로 MIME 판별
Body  : 녹음 파일의 raw 바이트 (녹음이 없으면 본문 비움 → 메타만 기록)
```

### 쿼리스트링 메타데이터
| 키 | 필수 | 설명 |
|----|------|------|
| `employee` | ✅ | 직원명 (해당 단말의 사용자) |
| `customer` | | 고객명 (연락처에서 변환) |
| `phone` | | 상대 전화번호 |
| `duration_sec` | | 통화 시간(초) |
| `direction` | | 수신/발신/부재중/기타 |
| `category` | | 문의/상담/불만/계약/AS/기타 (기본 기타) |
| `content` | | 메모(선택) |
| `called_at` | | 통화 일시 ISO8601 (미지정 시 서버 수신 시각) |

모든 값은 URL 인코딩(한글 포함). 성공 시 `201 {"id":N,"audio_filename":"..."}`.

### 예시 (curl)
```bash
curl -X POST "http://서버:8770/api/logs/upload?employee=홍길동&phone=01012345678&duration_sec=42&direction=수신&called_at=2026-05-30T10:30:00" \
  -H "X-Api-Key: secret123" \
  -H "X-Audio-Filename: call_01012345678_260530.m4a" \
  --data-binary @"/sdcard/Call/call_01012345678_260530.m4a"
```

파이썬 예제는 [`examples/upload_recording.py`](../examples/upload_recording.py) 참고.

---

## 3. 서버 실행 (업로드 인증 키 설정)

```bash
CALLLOG_HOST=0.0.0.0 CALLLOG_PORT=8770 CALLLOG_API_KEY=secret123 python -m calllog
```

업로드된 녹음은 관리자 **"관리자 조회"** 탭에서 표 안의 재생 버튼으로 바로 들을 수 있습니다.
