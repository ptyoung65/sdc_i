# 변경사항 설명서 (2026-01-22)

## 개요
본 문서는 2026년 1월 22일에 수행된 Open WebUI 시스템 변경 내역을 설명합니다.

---

## 목차
1. [대시보드2 집계 유형별 표시 개선](#1-대시보드2-집계-유형별-표시-개선)
2. [벡터화파일수/파일명 표시 로직 변경](#2-벡터화파일수파일명-표시-로직-변경)
3. [메시지 입력창 파일 첨부 제한](#3-메시지-입력창-파일-첨부-제한)
4. [파일 업로드 형식 제한](#4-파일-업로드-형식-제한)
5. [채팅 아카이브 서비스](#5-채팅-아카이브-서비스)

---

## 1. 대시보드2 집계 유형별 표시 개선

### 수정 파일
- `src/routes/(app)/admin/dashboard2/+page.svelte`

### 변경 내용

#### 1.1 한국시간(KST) 변환 함수 추가
```javascript
// [2026-01-22] 한국시간 변환 함수 추가
function formatToKST(dateStr: string | null | undefined): string {
    if (!dateStr || dateStr === '-') return '-';
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
        return date.toLocaleString('ko-KR', {
            timeZone: 'Asia/Seoul',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    } catch {
        return dateStr || '-';
    }
}
```
- **목적**: 서버에서 반환되는 UTC 시간을 한국 시간대(KST, UTC+9)로 변환
- **적용 위치**: 질의일시, 답변일시 컬럼

#### 1.2 집계 유형별 통계 카드 표시
| 구분 | 질문단위집계 | 세션단위집계 |
|------|-------------|-------------|
| 1행 제목 | 총 질문수 | 총 세션수 |
| 강조 항목 | 질문수 | 세션수 |
| 2행 제목 | 활성 세션 | 활성 세션 |

#### 1.3 테이블 헤더 구분
- **질문단위집계**: 질의일시, 사용자, 부서, 세션제목, 질문(간략), 답변일시, 토큰, 파일수, 파일명, 피드백
- **세션단위집계**: 질의일시, 사용자, 부서, 세션제목, 질문(간략), 답변일시, 토큰, **질문수**, 파일수, 파일명, 피드백

#### 1.4 모달 팝업 개선
- **질문단위집계**: 단일 질문-답변 표시 (파란색/녹색 스타일)
- **세션단위집계**: 해당 세션의 모든 질문-답변 표시 (인디고 스타일, 번호 부여)

#### 1.5 차트 범례 변경
- 질문단위: "질문 수", "답변 수"
- 세션단위: "세션 수", "답변 수"

---

## 2. 벡터화파일수/파일명 표시 로직 변경

### 수정 파일
- `services/monitoring-backend/main.py`

### 변경 전
- 사용자의 file 테이블에서 전체 벡터화된 파일을 집계하여 표시
- 해당 사용자가 업로드한 모든 파일의 총합

### 변경 후
- 해당 **질문** 또는 **세션**에 첨부된 파일만 표시
- 채팅 메시지의 `files` 배열에서 직접 추출

### 상세 변경 내용

#### 2.1 헬퍼 함수 추가
```python
# ----- [2026-01-22] 메시지에서 첨부파일 추출 헬퍼 함수 시작 -----
def extract_files_from_message(msg):
    """단일 메시지에서 첨부 파일 정보 추출"""
    files_info = []
    if isinstance(msg, dict) and 'files' in msg:
        files = msg.get('files', [])
        for f in (files or []):
            if isinstance(f, dict):
                file_obj = f.get('file', f)
                if isinstance(file_obj, dict):
                    filename = file_obj.get('filename', '') or file_obj.get('name', '')
                    if filename and not filename.startswith('tmp.'):
                        files_info.append(filename)
    return files_info

def extract_all_files_from_messages(messages):
    """메시지 리스트에서 모든 첨부 파일 추출 (세션 전체)"""
    all_files = []
    for msg in (messages or []):
        all_files.extend(extract_files_from_message(msg))
    return list(dict.fromkeys(all_files))  # 중복 제거
# ----- [2026-01-22] 메시지에서 첨부파일 추출 헬퍼 함수 종료 -----
```

#### 2.2 집계 유형별 파일 추출
| 집계 유형 | 파일 추출 방식 | 설명 |
|----------|--------------|------|
| 질문단위집계 | `extract_files_from_message(msg)` | 해당 질문 메시지에 첨부된 파일만 |
| 세션단위집계 | `extract_all_files_from_messages(messages)` | 세션 내 모든 메시지의 첨부 파일 |

#### 2.3 수정된 API 엔드포인트
- `GET /api/dashboard/logs` - 로그 조회 API
- `GET /api/dashboard/logs/export` - 엑셀 내보내기 API

#### 2.4 출력 데이터 변경
```python
# 변경 전
"vectorized_file_count": user_total_file_count,
"vectorized_filenames": user_total_filenames,

# 변경 후 [2026-01-22]
"vectorized_file_count": attached_file_count,  # 해당 질문/세션 첨부파일 수
"vectorized_filenames": attached_filenames,    # 해당 질문/세션 첨부파일명
```

---

## 3. 메시지 입력창 파일 첨부 제한

### 수정 파일
- `src/lib/components/chat/MessageInput.svelte`

### 변경 내용

#### 3.1 드래그앤드롭 비활성화
```javascript
const onDrop = async (e) => {
    e.preventDefault();
    console.log(e);

    // [2026-01-22] 드래그앤드롭으로 파일 첨부 비활성화
    // 파일 업로드를 차단하고 사용자에게 알림
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
        toast.error($i18n.t('파일 드래그앤드롭이 비활성화되어 있습니다. 문서첨부 버튼을 사용해주세요.'));
    }

    dragged = false;
};
```

#### 3.2 Ctrl+V 파일/이미지 붙여넣기 비활성화
```javascript
on:paste={async (e) => {
    e = e.detail.event;
    console.log(e);

    const clipboardData = e.clipboardData || window.clipboardData;

    // [2026-01-22] Ctrl+V로 파일/이미지 붙여넣기 비활성화
    // 텍스트 붙여넣기만 허용
    if (clipboardData && clipboardData.items) {
        for (const item of clipboardData.items) {
            if (item.type.indexOf('image') !== -1) {
                // 이미지 붙여넣기 차단
                e.preventDefault();
                toast.error($i18n.t('이미지 붙여넣기가 비활성화되어 있습니다. 문서첨부 버튼을 사용해주세요.'));
                return;
            } else if (item?.kind === 'file' && item.type !== 'text/plain') {
                // 파일 붙여넣기 차단 (텍스트 제외)
                e.preventDefault();
                toast.error($i18n.t('파일 붙여넣기가 비활성화되어 있습니다. 문서첨부 버튼을 사용해주세요.'));
                return;
            }
            // 텍스트는 기본 동작 허용 (별도 처리 없음)
        }
    }
}}
```

#### 3.3 파일 첨부 방식 요약
| 방식 | 상태 | 메시지 |
|------|------|--------|
| 드래그앤드롭 | ❌ 차단 | "파일 드래그앤드롭이 비활성화되어 있습니다. 문서첨부 버튼을 사용해주세요." |
| Ctrl+V 이미지 | ❌ 차단 | "이미지 붙여넣기가 비활성화되어 있습니다. 문서첨부 버튼을 사용해주세요." |
| Ctrl+V 파일 | ❌ 차단 | "파일 붙여넣기가 비활성화되어 있습니다. 문서첨부 버튼을 사용해주세요." |
| Ctrl+V 텍스트 | ✅ 허용 | - |
| 문서첨부 버튼 | ✅ 허용 | - |

---

## 4. 파일 업로드 형식 제한

### 수정 파일
- `src/lib/components/chat/MessageInput.svelte`

### 변경 내용

#### 4.1 허용되는 파일 형식
| 확장자 | MIME Type | 설명 |
|--------|-----------|------|
| `.pdf` | `application/pdf` | PDF 문서 |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Word 문서 |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Excel 문서 |
| `.pptx` | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | PowerPoint 문서 |

#### 4.2 차단되는 파일 형식
| 파일 유형 | 예시 | 에러 메시지 |
|----------|------|------------|
| 압축 파일 | zip, rar, 7z | "지원하지 않는 파일 형식입니다..." |
| 텍스트 파일 | txt, csv, json | "지원하지 않는 파일 형식입니다..." |
| 이미지 파일 | jpg, png, gif | "지원하지 않는 파일 형식입니다..." |
| 동영상 파일 | mp4, avi, mov | "지원하지 않는 파일 형식입니다..." |
| 기타 | exe, dll, etc | "지원하지 않는 파일 형식입니다..." |

#### 4.3 구현 코드
```javascript
// ----- [2026-01-22] 허용된 파일 형식 정의 시작 -----
const ALLOWED_EXTENSIONS = ['pptx', 'xlsx', 'docx', 'pdf'];
const ALLOWED_MIME_TYPES = [
    'application/vnd.openxmlformats-officedocument.presentationml.presentation', // pptx
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // xlsx
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // docx
    'application/pdf' // pdf
];
// ----- [2026-01-22] 허용된 파일 형식 정의 종료 -----

// 파일 형식 검증
const fileExtension = file.name.split('.').pop()?.toLowerCase();
const isAllowedExtension = ALLOWED_EXTENSIONS.includes(fileExtension);
const isAllowedMimeType = ALLOWED_MIME_TYPES.includes(file.type);

if (!isAllowedExtension && !isAllowedMimeType) {
    toast.error(
        $i18n.t('지원하지 않는 파일 형식입니다.\n\n허용되는 형식: PDF, Word(docx), Excel(xlsx), PowerPoint(pptx)\n\n압축파일, 텍스트파일(txt, csv), 이미지, 동영상 등은 첨부할 수 없습니다.')
    );
    return;
}
```

#### 4.4 에러 메시지 (팝업)
```
지원하지 않는 파일 형식입니다.

허용되는 형식: PDF, Word(docx), Excel(xlsx), PowerPoint(pptx)

압축파일, 텍스트파일(txt, csv), 이미지, 동영상 등은 첨부할 수 없습니다.
```

---

## 파일 구조

```
open-webui-main/
├── src/
│   ├── lib/
│   │   └── components/
│   │       └── chat/
│   │           └── MessageInput.svelte     # 파일 첨부 제한 (드래그앤드롭, Ctrl+V)
│   └── routes/
│       └── (app)/
│           └── admin/
│               └── dashboard2/
│                   └── +page.svelte         # 집계 유형별 표시, 한국시간 변환
├── services/
│   └── monitoring-backend/
│       └── main.py                          # 벡터화파일수/파일명 로직 변경
└── 0122_CHANGELOG.md                        # 이 파일
```

---

## 적용 방법

### 1. 프론트엔드 빌드
```bash
cd /home/chatpro/open-webui-main
npm run build
```

### 2. 컨테이너 재시작
```bash
# Open WebUI 컨테이너
podman stop sdc-open-webui && podman start sdc-open-webui

# Monitoring 백엔드 컨테이너
podman cp services/monitoring-backend/main.py sdc-monitoring:/app/main.py
podman restart sdc-monitoring
```

### 3. 확인
- **대시보드2**: http://192.168.122.178:3000/admin/dashboard2
  - 집계 유형(세션/질문) 변경 시 통계 카드, 테이블, 모달 변경 확인
  - 한국시간(KST) 표시 확인
- **채팅 화면**: http://192.168.122.178:3000
  - 드래그앤드롭 파일 첨부 시 에러 메시지 확인
  - Ctrl+V 이미지/파일 붙여넣기 시 에러 메시지 확인
  - Ctrl+V 텍스트 붙여넣기는 정상 동작 확인

---

## 주요 변경 코드 위치

### dashboard2/+page.svelte
| 라인 번호 | 설명 |
|----------|------|
| 451-475 | 한국시간 변환 함수 `formatToKST()` |
| 795-854 | 1행 통계 카드 집계 유형별 표시 |
| 856-969 | 2행 통계 카드 집계 유형별 표시 |
| 971-1129 | 차트 제목 및 범례 집계 유형별 표시 |
| 1181-1261 | 테이블 헤더 집계 유형별 구분 |
| 1329-1340 | 한국시간(KST) 변환 적용 |
| 1471-1652 | 모달 팝업 집계 유형별 표시 |

### monitoring-backend/main.py
| 라인 번호 | 설명 |
|----------|------|
| 1628-1652 | 첨부파일 추출 헬퍼 함수 (로그 API) |
| 1666-1669 | 초기 변수 설정 변경 |
| 1698-1737 | 질문단위집계 파일 추출 |
| 1763-1825 | 세션단위집계 파일 추출 |
| 1917-1935 | 결과 출력 시 첨부파일 정보 사용 |
| 2119-2140 | 첨부파일 추출 헬퍼 함수 (엑셀 API) |
| 2166-2209 | 엑셀 내보내기 질문단위 파일 추출 |
| 2256-2365 | 엑셀 내보내기 세션단위 파일 추출 |

### MessageInput.svelte
| 라인 번호 | 설명 |
|----------|------|
| 636-649 | 허용된 파일 형식 정의 (ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES) |
| 666-683 | 파일 형식 검증 및 차단 |
| 686-691 | 허용된 파일만 업로드 처리 |
| 795-806 | 드래그앤드롭 비활성화 |
| 1349-1373 | Ctrl+V 파일/이미지 붙여넣기 비활성화 |

---

## 주의사항
- 컨테이너 파일(Containerfile, Dockerfile)은 수정하지 않음
- 기존 API 호환성 유지
- 데이터베이스 스키마 변경 없음
- 텍스트 붙여넣기(Ctrl+V)는 정상 작동

---

---

## 5. 채팅 아카이브 서비스

### 신규 파일
- `services/chat-archive/chat_archive_service.py` - 메인 서비스 스크립트
- `services/chat-archive/schema.sql` - 데이터베이스 스키마
- `services/chat-archive/requirements.txt` - 의존성 패키지
- `services/chat-archive/start_archive_service.sh` - 시작 스크립트
- `services/chat-archive/.env` - 환경설정

### 기능 설명

#### 5.1 핵심 기능
| 기능 | 설명 |
|------|------|
| 자동 아카이브 | 2주(14일) 경과 채팅을 자동으로 압축 보관 |
| 스케줄러 | 매일 자정(00:00) 자동 실행 |
| 수동 실행 | API를 통한 즉시 실행 가능 |
| 벡터파일 삭제 | 아카이브 시 연관 벡터파일 자동 삭제 |
| 데이터 압축 | gzip 압축으로 저장공간 절약 (~75% 압축률) |

#### 5.2 데이터베이스 스키마

##### chat_archive 테이블
```sql
CREATE TABLE IF NOT EXISTS chat_archive (
    id VARCHAR(255) PRIMARY KEY,           -- 원본 chat.id
    user_id VARCHAR(255) NOT NULL,         -- 원본 chat.user_id
    title TEXT,                            -- 원본 chat.title
    chat_data_compressed BYTEA,            -- 압축된 채팅 데이터 (gzip)
    original_size INTEGER,                 -- 원본 데이터 크기 (bytes)
    compressed_size INTEGER,               -- 압축 데이터 크기 (bytes)
    message_count INTEGER DEFAULT 0,       -- 메시지 수
    file_count INTEGER DEFAULT 0,          -- 첨부 파일 수
    created_at BIGINT,                     -- 원본 생성 시간 (Unix timestamp)
    updated_at BIGINT,                     -- 원본 수정 시간 (Unix timestamp)
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_by VARCHAR(255) DEFAULT 'system',
    meta JSONB DEFAULT '{}'::jsonb         -- 추가 메타데이터
);
```

##### chat_archive_log 테이블
```sql
CREATE TABLE IF NOT EXISTS chat_archive_log (
    id SERIAL PRIMARY KEY,
    execution_type VARCHAR(50) NOT NULL,   -- 'auto' / 'manual'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    chats_archived INTEGER DEFAULT 0,
    chats_deleted INTEGER DEFAULT 0,
    files_deleted INTEGER DEFAULT 0,
    total_size_before BIGINT DEFAULT 0,
    total_size_after BIGINT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'running',  -- 'running', 'completed', 'failed'
    error_message TEXT,
    executed_by VARCHAR(255) DEFAULT 'system'
);
```

#### 5.3 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 상태 확인 |
| `/api/archive/run` | POST | 수동 아카이브 실행 |
| `/api/archive/status` | GET | 아카이브 상태 및 통계 조회 |
| `/api/archive/logs` | GET | 실행 로그 조회 |
| `/api/archive/search` | GET | 아카이브 검색 |
| `/api/archive/{id}` | GET | 아카이브 상세 조회 |
| `/api/archive/{id}/restore` | POST | 아카이브 복원 |

#### 5.4 수동 실행 예시
```bash
# 수동 아카이브 실행
curl -X POST http://localhost:3010/api/archive/run \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'

# 상태 확인
curl http://localhost:3010/api/archive/status

# 로그 조회
curl "http://localhost:3010/api/archive/logs?limit=10"
```

#### 5.5 벡터파일 삭제 로직
```python
# 아카이브 시 연관 벡터파일 자동 삭제
def delete_vector_files(chat_id: str, file_ids: List[str]) -> int:
    """
    채팅에 연결된 벡터 파일 삭제
    - file_ids: chat.chat에서 추출한 파일 ID 목록
    - Open WebUI API 호출로 파일 삭제
    - 삭제 실패 시 로그 기록 후 계속 진행
    """
```

#### 5.6 서비스 설정

| 환경변수 | 기본값 | 설명 |
|---------|-------|------|
| `DB_HOST` | 192.168.122.85 | PostgreSQL 호스트 |
| `DB_PORT` | 5433 | PostgreSQL 포트 |
| `DB_USER` | sdc_dev_user | 데이터베이스 사용자 |
| `DB_PASSWORD` | sdc_dev_pass_2025 | 데이터베이스 비밀번호 |
| `DB_NAME` | sdc_dev | 데이터베이스 이름 |
| `ARCHIVE_DAYS` | 14 | 아카이브 기준 일수 |
| `ARCHIVE_PORT` | 3010 | 서비스 포트 |

### 서비스 시작

```bash
# 1. 데이터베이스 테이블 생성 (최초 1회)
cd services/chat-archive
PGPASSWORD='sdc_dev_pass_2025' psql -h 192.168.122.85 -p 5433 \
  -U sdc_dev_user -d sdc_dev -f schema.sql

# 2. 서비스 시작
./start_archive_service.sh

# 또는 직접 실행
python3 chat_archive_service.py
```

### 테스트 결과
```
📋 아카이브 대상 채팅: 22개 (기준: 14일 경과)
✅ 아카이브 완료: mock-old-chat-4 (메시지: 2, 파일: 0, 압축률: 75.4%)
✅ 아카이브 완료: mock-old-chat-3 (메시지: 2, 파일: 0, 압축률: 75.4%)
...
🎉 채팅 아카이브 완료: 22개 아카이브, 0개 파일 삭제
```

---

## 파일 구조

```
open-webui-main/
├── src/
│   ├── lib/
│   │   └── components/
│   │       └── chat/
│   │           └── MessageInput.svelte     # 파일 첨부 제한 (드래그앤드롭, Ctrl+V)
│   └── routes/
│       └── (app)/
│           └── admin/
│               └── dashboard2/
│                   └── +page.svelte         # 집계 유형별 표시, 한국시간 변환
├── services/
│   ├── monitoring-backend/
│   │   └── main.py                          # 벡터화파일수/파일명 로직 변경
│   └── chat-archive/                        # [신규] 채팅 아카이브 서비스
│       ├── chat_archive_service.py          # 메인 서비스
│       ├── schema.sql                       # 데이터베이스 스키마
│       ├── requirements.txt                 # 의존성
│       ├── start_archive_service.sh         # 시작 스크립트
│       └── .env                             # 환경설정
└── 0122_CHANGELOG.md                        # 이 파일
```

---

## 작성자
Claude Code (2026-01-22)
