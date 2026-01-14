# 가드레일 데이터베이스 테이블 가이드

## 개요
가드레일(Guardrails) 시스템은 AI 응답의 안전성을 보장하기 위한 필터링 및 모니터링 시스템입니다.
이 문서는 `guardrails_db` 데이터베이스의 9개 테이블에 대한 상세 설명을 제공합니다.

> **수정 이력**: 2026-01-14 - 미사용 테이블 13개 삭제 (22개 → 9개)

---

## 데이터베이스 연결 정보
- **호스트**: 192.168.122.85
- **포트**: 5433
- **데이터베이스**: guardrails_db
- **사용자**: sdc_dev_user
- **비밀번호**: sdc_dev_pass_2025

---

## 테이블 구조 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           GUARDRAILS DATABASE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      1. 기본 테이블 (5개)                        │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  guardrail_keywords    → 금지/허용 키워드 목록 (243개)           │    │
│  │  guardrail_settings    → 전역 설정값                             │    │
│  │  guardrail_logs        → 기본 실행 로그                          │    │
│  │  guardrail_policies    → 정책 정의                               │    │
│  │  guardrail_check_logs  → 상세 체크 로그                          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      2. 마스터 테이블 (4개)                       │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  guardrail_master_policy_types    → 정책 유형 마스터             │    │
│  │  guardrail_master_filter_types    → 필터 유형 마스터             │    │
│  │  guardrail_master_severity_levels → 심각도 마스터                │    │
│  │  guardrail_master_action_types    → 조치 유형 마스터             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 기본 테이블 (5개)

### 1.1 guardrail_keywords
**역할**: 차단/허용할 키워드 목록을 저장하는 핵심 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | 기본키 |
| text | VARCHAR(255) | 키워드 텍스트 |
| category | VARCHAR(50) | 카테고리 (basic, personal, blacklist, whitelist, corporate, toxicity) |
| enabled | BOOLEAN | 활성화 여부 |
| created_at | TIMESTAMP | 생성 시간 |
| updated_at | TIMESTAMP | 수정 시간 |

**카테고리별 설명**:
- `basic`: 욕설, 비속어 (40개)
- `personal`: 개인정보 관련 키워드 (40개)
- `blacklist`: 보안/불법 관련 키워드 (40개)
- `whitelist`: 허용 키워드 (40개)
- `corporate`: 기업 정보 관련 키워드 (71개)
- `toxicity`: 유해 콘텐츠 키워드 (12개)

**인덱스**:
- `idx_keywords_category` (category)
- `idx_keywords_enabled` (enabled)

---

### 1.2 guardrail_settings
**역할**: 시스템 전역 설정값 저장

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | 기본키 |
| setting_key | VARCHAR(100) | 설정 키 (UNIQUE) |
| setting_value | TEXT | 설정 값 |
| description | TEXT | 설명 |
| updated_at | TIMESTAMPTZ | 수정 시간 |

**초기 설정값**:
| 키 | 값 | 설명 |
|-----|-----|------|
| guardrails_enabled | true | 가드레일 활성화 |
| korean_guardrails_enabled | true | 한국어 가드레일 활성화 |
| global_sensitivity | 0.7 | 전역 민감도 (0.0-1.0) |
| auto_block | true | 자동 차단 활성화 |
| logging_enabled | true | 로깅 활성화 |

---

### 1.3 guardrail_logs
**역할**: 가드레일 검사 실행 기본 로그

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | UUID | 기본키 |
| test_text | TEXT | 검사 대상 텍스트 |
| is_safe | BOOLEAN | 안전 여부 |
| blocked_keywords | VARCHAR[] | 탐지된 키워드 배열 |
| blocked_categories | VARCHAR[] | 탐지된 카테고리 배열 |
| confidence_score | NUMERIC(3,2) | 신뢰도 점수 |
| action_taken | VARCHAR(20) | 수행된 조치 |
| sensitivity | NUMERIC(3,2) | 적용 민감도 |
| created_at | TIMESTAMPTZ | 생성 시간 |

**인덱스**:
- `idx_logs_created_at` (created_at)
- `idx_logs_is_safe` (is_safe)

---

### 1.4 guardrail_policies
**역할**: 가드레일 정책 정의

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | VARCHAR(100) | 정책 ID (기본키) |
| name | VARCHAR(255) | 정책 이름 |
| category | VARCHAR(100) | 정책 카테고리 |
| description | TEXT | 정책 설명 |
| enabled | BOOLEAN | 활성화 여부 |
| severity | VARCHAR(20) | 심각도 (critical, high, medium, low) |
| rules | JSONB | 정책 규칙 (JSON) |
| filter_type | VARCHAR(30) | 필터 유형 |
| action_type | VARCHAR(20) | 조치 유형 |
| created_at | TIMESTAMP | 생성 시간 |
| updated_at | TIMESTAMP | 수정 시간 |

**인덱스**:
- `idx_policies_category` (category)
- `idx_policies_enabled` (enabled)
- `idx_policies_severity` (severity)

---

### 1.5 guardrail_check_logs
**역할**: 상세 검사 로그 (통계 분석용)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | BIGSERIAL | 기본키 |
| request_id | VARCHAR(100) | 요청 ID |
| session_id | VARCHAR(100) | 세션 ID |
| user_id | VARCHAR(255) | 사용자 ID |
| user_email | VARCHAR(255) | 사용자 이메일 |
| check_type | VARCHAR(30) | 검사 유형 (input/output) |
| model_id | VARCHAR(100) | AI 모델 ID |
| original_text | TEXT | 원본 텍스트 |
| processed_text | TEXT | 처리된 텍스트 |
| text_length | INTEGER | 텍스트 길이 |
| policy_id | VARCHAR(100) | 적용 정책 ID |
| policy_name | VARCHAR(100) | 정책 이름 |
| check_result | VARCHAR(30) | 검사 결과 (pass/block/warn) |
| detection_score | NUMERIC(5,4) | 탐지 점수 |
| detected_categories | JSONB | 탐지된 카테고리 |
| detected_keywords | TEXT[] | 탐지된 키워드 |
| detection_details | JSONB | 탐지 상세 정보 |
| action_taken | VARCHAR(30) | 수행된 조치 |
| action_reason | TEXT | 조치 사유 |
| processing_time_ms | INTEGER | 처리 시간 (밀리초) |
| client_ip | VARCHAR(45) | 클라이언트 IP |
| user_agent | TEXT | 사용자 에이전트 |
| created_at | TIMESTAMP | 생성 시간 |

**인덱스**:
- `idx_check_logs_created_at` (created_at)
- `idx_check_logs_user_id` (user_id)
- `idx_check_logs_result` (check_result)
- `idx_check_logs_policy_id` (policy_id)
- `idx_check_logs_date_result` (DATE(created_at), check_result)

---

## 2. 마스터 테이블 (4개)

### 2.1 guardrail_master_policy_types
**역할**: 정책 유형 마스터 데이터

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | 기본키 |
| code | VARCHAR(10) | 유형 코드 (UNIQUE) |
| type_id | VARCHAR(50) | 유형 ID (UNIQUE) |
| name | VARCHAR(100) | 유형 이름 |
| description | TEXT | 설명 |
| is_active | BOOLEAN | 활성화 여부 |
| sort_order | INTEGER | 정렬 순서 |
| created_at | TIMESTAMPTZ | 생성 시간 |
| updated_at | TIMESTAMPTZ | 수정 시간 |

**초기 데이터**:
| 코드 | type_id | 이름 |
|------|---------|------|
| PT001 | company | 회사정보 (Company) |
| PT002 | compliance | 규정준수 (Compliance) |
| PT003 | content | 콘텐츠 (Content) |
| PT004 | privacy | 개인정보 (Privacy) |
| PT005 | security | 보안 (Security) |

---

### 2.2 guardrail_master_filter_types
**역할**: 필터 유형 마스터 데이터

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | 기본키 |
| code | VARCHAR(10) | 필터 코드 (UNIQUE) |
| type_id | VARCHAR(50) | 필터 ID (UNIQUE) |
| name | VARCHAR(100) | 필터 이름 |
| description | TEXT | 설명 |
| is_active | BOOLEAN | 활성화 여부 |
| sort_order | INTEGER | 정렬 순서 |
| created_at | TIMESTAMPTZ | 생성 시간 |
| updated_at | TIMESTAMPTZ | 수정 시간 |

**초기 데이터**:
| 코드 | type_id | 이름 |
|------|---------|------|
| FT001 | input_filter | 입력 필터 |
| FT002 | output_filter | 출력 필터 |
| FT003 | pii_detection | PII 탐지 |
| FT004 | toxicity | 유해성 탐지 |
| FT005 | custom | 커스텀 |

---

### 2.3 guardrail_master_severity_levels
**역할**: 심각도 레벨 마스터 데이터

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | 기본키 |
| code | VARCHAR(10) | 심각도 코드 (UNIQUE) |
| level_id | VARCHAR(50) | 레벨 ID (UNIQUE) |
| name | VARCHAR(100) | 심각도 이름 |
| color | VARCHAR(20) | 표시 색상 (HEX) |
| priority | INTEGER | 우선순위 |
| description | TEXT | 설명 |
| is_active | BOOLEAN | 활성화 여부 |
| sort_order | INTEGER | 정렬 순서 |
| created_at | TIMESTAMPTZ | 생성 시간 |
| updated_at | TIMESTAMPTZ | 수정 시간 |

**초기 데이터**:
| 코드 | level_id | 이름 | 색상 | 우선순위 |
|------|----------|------|------|----------|
| SV001 | critical | Critical (치명적) | #dc2626 | 100 |
| SV002 | high | High (높음) | #ea580c | 75 |
| SV003 | medium | Medium (중간) | #ca8a04 | 50 |
| SV004 | low | Low (낮음) | #16a34a | 25 |

---

### 2.4 guardrail_master_action_types
**역할**: 조치 유형 마스터 데이터

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | 기본키 |
| code | VARCHAR(10) | 조치 코드 (UNIQUE) |
| action_id | VARCHAR(50) | 조치 ID (UNIQUE) |
| name | VARCHAR(100) | 조치 이름 |
| description | TEXT | 설명 |
| is_active | BOOLEAN | 활성화 여부 |
| sort_order | INTEGER | 정렬 순서 |
| created_at | TIMESTAMPTZ | 생성 시간 |
| updated_at | TIMESTAMPTZ | 수정 시간 |

**초기 데이터**:
| 코드 | action_id | 이름 | 설명 |
|------|-----------|------|------|
| AT001 | block | 차단 (Block) | 요청을 완전히 차단 |
| AT002 | warn | 경고 (Warn) | 경고 후 계속 진행 |
| AT003 | log_only | 로그만 (Log Only) | 로그 기록만 수행 |
| AT004 | replace | 대체 (Replace) | 민감 정보 마스킹 |

---

## 테이블 요약

| 구분 | 테이블명 | 설명 | 레코드 수 |
|------|---------|------|-----------|
| 기본 | guardrail_keywords | 키워드 목록 | 243개 |
| 기본 | guardrail_settings | 전역 설정 | 5개 |
| 기본 | guardrail_logs | 기본 로그 | 동적 |
| 기본 | guardrail_policies | 정책 정의 | 동적 |
| 기본 | guardrail_check_logs | 상세 로그 | 동적 |
| 마스터 | guardrail_master_policy_types | 정책 유형 | 5개 |
| 마스터 | guardrail_master_filter_types | 필터 유형 | 5개 |
| 마스터 | guardrail_master_severity_levels | 심각도 | 4개 |
| 마스터 | guardrail_master_action_types | 조치 유형 | 4개 |

---

## 문서 정보
- **작성일**: 2026-01-14
- **수정일**: 2026-01-14
- **대상 시스템**: guardrails_db (PostgreSQL 5433)
- **테이블 수**: 9개
