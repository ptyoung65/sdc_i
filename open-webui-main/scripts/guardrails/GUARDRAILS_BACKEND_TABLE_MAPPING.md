# 가드레일 백엔드-테이블 연관관계 문서

## 개요
이 문서는 가드레일 백엔드 서비스들과 `guardrails_db` 데이터베이스 테이블 간의 연관관계를 설명합니다.

> **수정 이력**: 2026-01-14 - 미사용 테이블 13개 삭제 (22개 → 9개)

---

## 백엔드 서비스 구성

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              가드레일 백엔드 구성                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │           1. Arthur Guardrails Service (포트 8001)                        │  │
│  │                                                                           │  │
│  │   역할: 실시간 텍스트 필터링, 키워드 관리, PII 탐지                        │  │
│  │   컨테이너: sdc-guardrails                                                │  │
│  │   소스: /services/arthur-guardrails/arthur_guardrails_service.py         │  │
│  │   DB 연결: database.py (SQLAlchemy + asyncpg)                            │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │           2. Monitoring Backend (포트 3001)                               │  │
│  │                                                                           │  │
│  │   역할: 대시보드 통계, 정책 관리, 기준정보 관리                             │  │
│  │   컨테이너: sdc-monitoring                                                │  │
│  │   소스: /services/monitoring-backend/main.py                              │  │
│  │   DB 연결: psycopg2 직접 연결                                             │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │           3. Guardrails Pipeline (Open WebUI 내장)                        │  │
│  │                                                                           │  │
│  │   역할: 채팅 요청/응답 인터셉트, 실시간 필터링                              │  │
│  │   소스: /pipelines/guardrails_pipe.py                                     │  │
│  │   호출: Arthur Guardrails API (8001)                                     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Arthur Guardrails Service (포트 8001)

### 1.1 서비스 개요

| 항목 | 값 |
|------|-----|
| **서비스명** | Arthur AI Guardrails Service |
| **포트** | 8001 |
| **컨테이너** | sdc-guardrails |
| **소스 파일** | `/services/arthur-guardrails/arthur_guardrails_service.py` |
| **DB 연결 파일** | `/services/arthur-guardrails/database.py` |
| **프레임워크** | FastAPI + SQLAlchemy (asyncpg) |

### 1.2 DB 연결 정보

```python
# database.py에서 설정
DB_HOST = os.getenv("DB_HOST", "192.168.122.85")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_USER = os.getenv("DB_USER", "sdc_dev_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sdc_dev_pass_2025")
DB_NAME = os.getenv("DB_NAME", "guardrails_db")
```

### 1.3 SQLAlchemy 모델 정의

#### GuardrailKeyword 모델
```python
class GuardrailKeyword(Base):
    __tablename__ = "guardrail_keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String(255), nullable=False)
    category = Column(String(50), default='basic')
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

#### GuardrailSettings 모델
```python
class GuardrailSettings(Base):
    __tablename__ = "guardrail_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

#### GuardrailLog 모델
```python
class GuardrailLog(Base):
    __tablename__ = "guardrail_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_text = Column(Text, nullable=False)
    is_safe = Column(Boolean, nullable=False)
    blocked_keywords = Column(ARRAY(String))
    blocked_categories = Column(ARRAY(String))
    confidence_score = Column(DECIMAL(3, 2))
    action_taken = Column(String(20))
    sensitivity = Column(DECIMAL(3, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 1.4 API 엔드포인트와 테이블 연관

| API 엔드포인트 | HTTP | 테이블 | 작업 | 설명 |
|---------------|------|--------|------|------|
| `/health` | GET | `guardrail_keywords`, `guardrail_settings` | SELECT | 서비스 상태 확인 |
| `/status` | GET | `guardrail_keywords`, `guardrail_settings` | SELECT | 통계 및 상태 정보 |
| `/test` | POST | `guardrail_keywords`, `guardrail_logs`, `guardrail_check_logs` | SELECT, INSERT | 텍스트 검사 및 로그 저장 |
| `/api/check` | POST | `guardrail_keywords`, `guardrail_logs`, `guardrail_check_logs` | SELECT, INSERT | 필터 유형별 검사 |
| `/keywords` | GET | `guardrail_keywords` | SELECT | 키워드 목록 조회 |
| `/keywords` | POST | `guardrail_keywords` | INSERT | 키워드 추가 |
| `/keywords/{id}` | PUT | `guardrail_keywords` | UPDATE | 키워드 수정 |
| `/keywords/{id}` | DELETE | `guardrail_keywords` | DELETE | 키워드 삭제 |
| `/settings` | GET | `guardrail_settings` | SELECT | 설정 조회 |
| `/settings/{key}` | PUT | `guardrail_settings` | UPDATE/INSERT | 설정 변경 |
| `/logs` | GET | `guardrail_logs` | SELECT | 로그 조회 |
| `/logs/stats` | GET | `guardrail_logs` | SELECT | 로그 통계 |

### 1.5 데이터베이스 매니저 함수와 테이블

| 함수명 | 테이블 | 작업 | 설명 |
|--------|--------|------|------|
| `init_database()` | 전체 | 검증 | 필수 테이블 존재 확인 |
| `init_default_data()` | `guardrail_keywords`, `guardrail_settings` | INSERT | 기본 데이터 초기화 |
| `get_all_keywords()` | `guardrail_keywords` | SELECT | 전체 키워드 조회 |
| `get_keywords_by_category(category)` | `guardrail_keywords` | SELECT | 카테고리별 키워드 조회 |
| `get_keyword_by_id(id)` | `guardrail_keywords` | SELECT | ID로 키워드 조회 |
| `add_keyword(data)` | `guardrail_keywords` | INSERT | 키워드 추가 |
| `update_keyword(id, data)` | `guardrail_keywords` | UPDATE | 키워드 수정 |
| `delete_keyword(id)` | `guardrail_keywords` | DELETE | 키워드 삭제 |
| `get_settings()` | `guardrail_settings` | SELECT | 전체 설정 조회 |
| `update_setting(key, value)` | `guardrail_settings` | UPDATE/INSERT | 설정 변경 |
| `log_test_result(data)` | `guardrail_logs`, `guardrail_check_logs` | INSERT | 검사 결과 로그 저장 |
| `get_logs(limit, offset, filter)` | `guardrail_logs` | SELECT | 로그 조회 |

---

## 2. Monitoring Backend (포트 3001)

### 2.1 서비스 개요

| 항목 | 값 |
|------|-----|
| **서비스명** | Monitoring Backend |
| **포트** | 3001 |
| **컨테이너** | sdc-monitoring |
| **소스 파일** | `/services/monitoring-backend/main.py` |
| **프레임워크** | FastAPI + psycopg2 |

### 2.2 API 엔드포인트와 테이블 연관

#### 대시보드 API

| API 엔드포인트 | HTTP | 테이블 | 작업 | 설명 |
|---------------|------|--------|------|------|
| `/api/guardrails/dashboard` | GET | `guardrail_policies`, `guardrail_check_logs` | SELECT | 대시보드 통계 |
| `/api/guardrails/trend` | GET | `guardrail_check_logs` | SELECT | 추이 데이터 |
| `/api/guardrails/logs` | GET | `guardrail_check_logs` | SELECT | 검사 로그 목록 |

#### 정책 관리 API

| API 엔드포인트 | HTTP | 테이블 | 작업 | 설명 |
|---------------|------|--------|------|------|
| `/api/guardrails/policies` | GET | `guardrail_policies`, `guardrail_check_logs` | SELECT | 정책 목록 |
| `/api/guardrails/policies` | POST | `guardrail_policies` | INSERT | 정책 생성 |
| `/api/guardrails/policies/{id}` | GET | `guardrail_policies` | SELECT | 정책 상세 |
| `/api/guardrails/policies/{id}` | PUT | `guardrail_policies` | UPDATE | 정책 수정 |
| `/api/guardrails/policies/{id}` | DELETE | `guardrail_policies`, `guardrail_check_logs` | DELETE | 정책 삭제 |
| `/api/guardrails/policies/{id}/toggle` | PUT | `guardrail_policies` | UPDATE | 정책 토글 |
| `/api/guardrails/policies/export` | GET | `guardrail_policies` | SELECT | 엑셀 내보내기 |
| `/api/guardrails/policies/import` | POST | `guardrail_policies` | INSERT | CSV 가져오기 |

#### 기준정보 관리 API

| API 엔드포인트 | HTTP | 테이블 | 작업 | 설명 |
|---------------|------|--------|------|------|
| `/api/guardrails/master/all` | GET | 마스터 테이블 4개 | SELECT | 전체 기준정보 |
| `/api/guardrails/master/policy-types` | GET/POST/DELETE | `guardrail_master_policy_types` | CRUD | 정책 유형 관리 |
| `/api/guardrails/master/filter-types` | GET/POST/DELETE | `guardrail_master_filter_types` | CRUD | 필터 유형 관리 |
| `/api/guardrails/master/severity-levels` | GET/POST/DELETE | `guardrail_master_severity_levels` | CRUD | 심각도 관리 |
| `/api/guardrails/master/action-types` | GET/POST/DELETE | `guardrail_master_action_types` | CRUD | 조치 유형 관리 |

---

## 3. 테이블별 백엔드 연관 요약

### 기본 테이블 (5개)

| 테이블명 | Arthur (8001) | Monitoring (3001) | 용도 |
|---------|--------------|-------------------|------|
| `guardrail_keywords` | ✅ CRUD | ❌ | 실시간 필터링 키워드 |
| `guardrail_settings` | ✅ CRUD | ❌ | 전역 설정 관리 |
| `guardrail_logs` | ✅ INSERT/SELECT | ❌ | 기본 검사 로그 |
| `guardrail_policies` | ❌ | ✅ CRUD | 정책 정의 및 관리 |
| `guardrail_check_logs` | ✅ INSERT | ✅ SELECT | 상세 검사 로그 (공유) |

### 마스터 테이블 (4개)

| 테이블명 | Arthur (8001) | Monitoring (3001) | 용도 |
|---------|--------------|-------------------|------|
| `guardrail_master_policy_types` | ❌ | ✅ CRUD | 정책 유형 코드 |
| `guardrail_master_filter_types` | ❌ | ✅ CRUD | 필터 유형 코드 |
| `guardrail_master_severity_levels` | ❌ | ✅ CRUD | 심각도 레벨 |
| `guardrail_master_action_types` | ❌ | ✅ CRUD | 조치 유형 |

---

## 4. 데이터 흐름도

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              사용자 입력                                      │
│                          (Open WebUI 채팅)                                   │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Guardrails Pipeline (입력 필터)                            │
│                   /pipelines/guardrails_pipe.py                              │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│               Arthur Guardrails Service (포트 8001)                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        텍스트 검사 프로세스                              │ │
│  │                                                                        │ │
│  │  1. guardrail_settings 조회                                            │ │
│  │     └─ guardrails_enabled, auto_block, sensitivity 확인               │ │
│  │                                                                        │ │
│  │  2. guardrail_keywords 조회 (카테고리별)                                │ │
│  │     └─ basic, personal, blacklist, whitelist, corporate, toxicity     │ │
│  │                                                                        │ │
│  │  3. PII 패턴 탐지 (코드 내장)                                           │ │
│  │     └─ 주민번호, 전화번호, 이메일, 카드번호, 계좌번호 등                │ │
│  │                                                                        │ │
│  │  4. 검사 결과 판정                                                      │ │
│  │     └─ is_safe, action (pass/warn/block), detection_score             │ │
│  │                                                                        │ │
│  │  5. 로그 저장 (백그라운드)                                              │ │
│  │     └─ guardrail_logs + guardrail_check_logs                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
   ┌────────────┐        ┌────────────┐        ┌────────────┐
   │   PASS     │        │   WARN     │        │   BLOCK    │
   │  (통과)    │        │  (경고)    │        │  (차단)    │
   └──────┬─────┘        └──────┬─────┘        └──────┬─────┘
          │                      │                      │
          ▼                      ▼                      ▼
   ┌────────────┐        ┌────────────┐        ┌────────────┐
   │ AI 처리   │        │ 경고 표시 │        │ 차단 메시지│
   │   진행    │        │ + AI 처리 │        │   반환     │
   └────────────┘        └────────────┘        └────────────┘
```

---

## 5. 백엔드별 SQL 쿼리 예시

### Arthur Guardrails Service (8001)

#### 키워드 조회
```sql
-- 전체 키워드
SELECT id, text, category, enabled, created_at, updated_at
FROM guardrail_keywords;

-- 카테고리별 키워드
SELECT id, text, category, enabled
FROM guardrail_keywords
WHERE category = 'basic';
```

#### 설정 조회
```sql
SELECT setting_key, setting_value
FROM guardrail_settings;
```

#### 로그 저장
```sql
-- guardrail_logs
INSERT INTO guardrail_logs (test_text, is_safe, blocked_keywords, blocked_categories,
                            confidence_score, action_taken, sensitivity)
VALUES ($1, $2, $3, $4, $5, $6, $7);

-- guardrail_check_logs
INSERT INTO guardrail_check_logs (request_id, user_id, check_type, original_text,
                                   text_length, check_result, detection_score,
                                   detected_categories, detected_keywords, action_taken,
                                   processing_time_ms, created_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW());
```

### Monitoring Backend (3001)

#### 대시보드 통계
```sql
-- 정책 통계
SELECT COUNT(*) as total, SUM(CASE WHEN enabled THEN 1 ELSE 0 END) as active
FROM guardrail_policies;

-- 검사 결과 통계
SELECT check_result, COUNT(*) as count
FROM guardrail_check_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY check_result;

-- 정책별 통계
SELECT p.id, p.name, p.category, p.severity,
       COUNT(l.id) as total_checks,
       SUM(CASE WHEN l.check_result = 'block' THEN 1 ELSE 0 END) as block_count
FROM guardrail_policies p
LEFT JOIN guardrail_check_logs l ON p.id = l.policy_id
GROUP BY p.id, p.name, p.category, p.severity;
```

#### 기준정보 조회
```sql
-- 정책 유형
SELECT code, type_id as id, name, description, is_active, sort_order
FROM guardrail_master_policy_types
WHERE is_active = true
ORDER BY sort_order;

-- 전체 기준정보
SELECT code, type_id as id, name FROM guardrail_master_policy_types WHERE is_active = true
UNION ALL
SELECT code, type_id as id, name FROM guardrail_master_filter_types WHERE is_active = true
UNION ALL
SELECT code, level_id as id, name FROM guardrail_master_severity_levels WHERE is_active = true
UNION ALL
SELECT code, action_id as id, name FROM guardrail_master_action_types WHERE is_active = true;
```

---

## 6. 환경 변수 설정

### Arthur Guardrails Service

| 환경 변수 | 기본값 | 설명 |
|-----------|--------|------|
| `DB_HOST` | - | 데이터베이스 호스트 (필수) |
| `DB_PORT` | 5433 | 데이터베이스 포트 |
| `DB_USER` | sdc_dev_user | 데이터베이스 사용자 |
| `DB_PASSWORD` | sdc_dev_pass_2025 | 데이터베이스 비밀번호 |
| `DB_NAME` | guardrails_db | 데이터베이스 이름 |
| `LOG_DIR` | /app/logs | 로그 디렉토리 |

### Monitoring Backend

| 환경 변수 | 기본값 | 설명 |
|-----------|--------|------|
| `GUARDRAILS_DB_HOST` | 192.168.122.85 | guardrails_db 호스트 |
| `GUARDRAILS_DB_PORT` | 5433 | guardrails_db 포트 |
| `GUARDRAILS_DB_USER` | sdc_dev_user | DB 사용자 |
| `GUARDRAILS_DB_PASSWORD` | sdc_dev_pass_2025 | DB 비밀번호 |
| `GUARDRAILS_DB_NAME` | guardrails_db | DB 이름 |

---

## 문서 정보
- **작성일**: 2026-01-14
- **대상 시스템**: Arthur Guardrails Service, Monitoring Backend
- **데이터베이스**: guardrails_db (PostgreSQL 5433)
- **관련 문서**:
  - `GUARDRAILS_DB_TABLES_GUIDE.md` - 테이블 상세 설명
  - `GUARDRAILS_SCREEN_TABLE_MAPPING.md` - 화면-테이블 연관관계
