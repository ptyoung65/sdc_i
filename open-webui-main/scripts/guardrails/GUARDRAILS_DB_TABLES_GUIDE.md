# 가드레일 데이터베이스 테이블 가이드

## 개요
가드레일(Guardrails) 시스템은 AI 응답의 안전성을 보장하기 위한 필터링 및 모니터링 시스템입니다.
이 문서는 `guardrails_db` 데이터베이스의 22개 테이블에 대한 상세 설명을 제공합니다.

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
│  │                      1. 기본 테이블 (6개)                        │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  guardrail_keywords    → 금지/허용 키워드 목록 (243개)           │    │
│  │  guardrail_settings    → 전역 설정값                             │    │
│  │  guardrail_logs        → 기본 실행 로그                          │    │
│  │  guardrail_policies    → 정책 정의                               │    │
│  │  guardrail_check_logs  → 상세 체크 로그                          │    │
│  │  guardrail_filter_logs → 필터 실행 로그                          │    │
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
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      3. 코드 테이블 (5개)                        │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  guardrail_policy_types    → 정책 유형 코드                      │    │
│  │  guardrail_filter_types    → 필터 유형 코드                      │    │
│  │  guardrail_severity_levels → 심각도 코드                         │    │
│  │  guardrail_action_types    → 조치 유형 코드                      │    │
│  │  guardrail_categories      → 카테고리 코드                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     4. 통계/분석 테이블 (4개)                     │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  guardrail_daily_stats      → 일별 통계                          │    │
│  │  guardrail_hourly_stats     → 시간별 통계                        │    │
│  │  guardrail_keyword_stats    → 키워드 통계                        │    │
│  │  guardrail_user_violations  → 사용자별 위반 통계                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      5. 기타 테이블 (3개)                        │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  guardrail_activities   → 관리자 활동 로그                       │    │
│  │  guardrail_validations  → 검증 로그                              │    │
│  │  guardrail_pii_patterns → PII 패턴 정의                          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 기본 테이블 (6개)

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

**예시 데이터**:
```sql
SELECT * FROM guardrail_keywords WHERE category = 'personal' LIMIT 5;
-- 주민번호, 신용카드, 계좌번호, 비밀번호, 여권번호
```

---

### 1.2 guardrail_settings
**역할**: 시스템 전역 설정값을 저장

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | 기본키 |
| setting_key | VARCHAR(100) | 설정 키 (UNIQUE) |
| setting_value | TEXT | 설정 값 |
| description | TEXT | 설정 설명 |
| updated_at | TIMESTAMPTZ | 수정 시간 |

**현재 설정값**:
| 설정 키 | 값 | 설명 |
|---------|-----|------|
| guardrails_enabled | true | 기본 가드레일 활성화 |
| korean_guardrails_enabled | true | 한국어 가드레일 활성화 |
| global_sensitivity | 0.7 | 전역 민감도 (0.0~1.0) |
| auto_block | true | 자동 차단 기능 |
| logging_enabled | true | 로깅 기능 |

---

### 1.3 guardrail_logs
**역할**: 가드레일 실행의 기본 로그를 저장

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | UUID | 기본키 |
| test_text | TEXT | 검사된 텍스트 |
| is_safe | BOOLEAN | 안전 여부 |
| blocked_keywords | VARCHAR[] | 차단된 키워드 배열 |
| blocked_categories | VARCHAR[] | 차단된 카테고리 배열 |
| confidence_score | NUMERIC(3,2) | 신뢰도 점수 |
| action_taken | VARCHAR(20) | 취해진 조치 |
| sensitivity | NUMERIC(3,2) | 민감도 |
| created_at | TIMESTAMPTZ | 생성 시간 |

---

### 1.4 guardrail_policies
**역할**: 가드레일 정책을 정의하고 관리

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | VARCHAR(100) | 정책 ID (기본키) |
| name | VARCHAR(255) | 정책명 |
| category | VARCHAR(100) | 카테고리 |
| description | TEXT | 정책 설명 |
| enabled | BOOLEAN | 활성화 여부 |
| severity | VARCHAR(20) | 심각도 (critical/high/medium/low) |
| rules | JSONB | 정책 규칙 (JSON 형식) |
| filter_type | VARCHAR(30) | 필터 유형 |
| action_type | VARCHAR(20) | 조치 유형 |
| created_at | TIMESTAMP | 생성 시간 |
| updated_at | TIMESTAMP | 수정 시간 |

---

### 1.5 guardrail_check_logs
**역할**: 상세한 검사 로그를 저장 (대시보드 분석용)

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
| policy_id | VARCHAR(100) | 적용된 정책 ID |
| policy_name | VARCHAR(100) | 적용된 정책명 |
| check_result | VARCHAR(30) | 검사 결과 (pass/block/warn) |
| detection_score | NUMERIC(5,4) | 탐지 점수 |
| detected_categories | JSONB | 탐지된 카테고리 |
| detected_keywords | TEXT[] | 탐지된 키워드 |
| detection_details | JSONB | 탐지 상세 정보 |
| action_taken | VARCHAR(30) | 취해진 조치 |
| action_reason | TEXT | 조치 사유 |
| processing_time_ms | INTEGER | 처리 시간 (ms) |
| client_ip | VARCHAR(45) | 클라이언트 IP |
| user_agent | TEXT | User Agent |
| created_at | TIMESTAMP | 생성 시간 |

**인덱스**:
- `idx_check_logs_created_at`: 생성일 기준 조회
- `idx_check_logs_user_id`: 사용자별 조회
- `idx_check_logs_result`: 결과별 조회
- `idx_check_logs_policy_id`: 정책별 조회
- `idx_check_logs_date_result`: 일자+결과 복합 조회

---

### 1.6 guardrail_filter_logs
**역할**: 필터 실행 로그를 저장

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | BIGSERIAL | 기본키 |
| request_id | VARCHAR(100) | 요청 ID |
| user_id | VARCHAR(255) | 사용자 ID |
| filter_type | VARCHAR(30) | 필터 유형 |
| input_text | TEXT | 입력 텍스트 |
| output_text | TEXT | 출력 텍스트 |
| is_modified | BOOLEAN | 수정 여부 |
| is_blocked | BOOLEAN | 차단 여부 |
| matched_policies | JSONB | 매칭된 정책 |
| matched_keywords | TEXT[] | 매칭된 키워드 |
| detection_score | NUMERIC(5,4) | 탐지 점수 |
| action_taken | VARCHAR(30) | 취해진 조치 |
| processing_time_ms | INTEGER | 처리 시간 (ms) |
| error_message | TEXT | 에러 메시지 |
| metadata | JSONB | 추가 메타데이터 |
| created_at | TIMESTAMP | 생성 시간 |

---

## 2. 마스터 테이블 (4개)

### 2.1 guardrail_master_policy_types
**역할**: 정책 유형의 마스터 데이터 (UI 드롭다운용)

| 코드 | 유형 ID | 이름 | 설명 |
|------|---------|------|------|
| PT001 | company | 회사정보 | 회사 관련 정보 보호 정책 |
| PT002 | compliance | 규정준수 | 법률 및 규정 준수 관련 정책 |
| PT003 | content | 콘텐츠 | 콘텐츠 품질 및 적합성 관련 정책 |
| PT004 | privacy | 개인정보 | 개인정보 보호 관련 정책 |
| PT005 | security | 보안 | 시스템 보안 관련 정책 |

---

### 2.2 guardrail_master_filter_types
**역할**: 필터 유형의 마스터 데이터

| 코드 | 유형 ID | 이름 | 설명 |
|------|---------|------|------|
| FT001 | input_filter | 입력 필터 | 사용자 입력 검증 필터 |
| FT002 | output_filter | 출력 필터 | AI 응답 출력 검증 필터 |
| FT003 | pii_detection | PII 탐지 | 개인식별정보 탐지 필터 |
| FT004 | toxicity | 유해성 탐지 | 유해 콘텐츠 탐지 필터 |
| FT005 | custom | 커스텀 | 사용자 정의 필터 |

---

### 2.3 guardrail_master_severity_levels
**역할**: 심각도 레벨의 마스터 데이터

| 코드 | 레벨 ID | 이름 | 색상 | 우선순위 | 설명 |
|------|---------|------|------|----------|------|
| SV001 | critical | Critical | #dc2626 | 100 | 즉시 조치 필요 |
| SV002 | high | High | #ea580c | 75 | 빠른 조치 필요 |
| SV003 | medium | Medium | #ca8a04 | 50 | 주의 필요 |
| SV004 | low | Low | #16a34a | 25 | 참고용 |

---

### 2.4 guardrail_master_action_types
**역할**: 조치 유형의 마스터 데이터

| 코드 | 조치 ID | 이름 | 설명 |
|------|---------|------|------|
| AT001 | block | 차단 | 요청을 완전히 차단 |
| AT002 | warn | 경고 | 경고 메시지와 함께 처리 계속 |
| AT003 | log_only | 로그만 | 로그만 기록하고 처리 계속 |
| AT004 | replace | 대체 | 민감 정보를 마스킹/대체 후 처리 |

---

## 3. 코드 테이블 (5개)

### 3.1 guardrail_policy_types
**역할**: 정책 유형 코드 (서비스에서 참조)

| 코드 | 이름 | 설명 |
|------|------|------|
| company | 회사정보 | 회사 기밀 정보 보호 정책 |
| compliance | 규정준수 | 법률 및 규정 준수 정책 |
| content | 콘텐츠 | 콘텐츠 필터링 정책 |
| privacy | 개인정보 | 개인정보 보호 정책 |
| security | 보안 | 시스템 보안 정책 |

---

### 3.2 guardrail_filter_types
**역할**: 필터 유형 코드 (대시보드 집계에 사용)

| 코드 | 이름 | 설명 |
|------|------|------|
| input_filter | 입력 필터 | 사용자 입력 검사 |
| output_filter | 출력 필터 | AI 응답 검사 |
| pii_detection | PII 탐지 | 개인식별정보 탐지 |
| toxicity | 유해성 탐지 | 유해 콘텐츠 탐지 |
| custom | 커스텀 | 사용자 정의 규칙 |

---

### 3.3 guardrail_severity_levels
**역할**: 심각도 코드

| 코드 | 이름 | 색상 | 우선순위 |
|------|------|------|----------|
| critical | Critical | #dc2626 | 1 |
| high | High | #f97316 | 2 |
| medium | Medium | #eab308 | 3 |
| low | Low | #22c55e | 4 |

---

### 3.4 guardrail_action_types
**역할**: 조치 유형 코드

| 코드 | 이름 | 설명 |
|------|------|------|
| block | 차단 | 완전 차단 |
| warn | 경고 | 경고 후 사용자 선택 |
| log_only | 로그만 | 로그 기록만 |
| replace | 대체 | 마스킹 처리 |

---

### 3.5 guardrail_categories
**역할**: 정책 카테고리 코드

| ID | 이름 | 정책 수 |
|----|------|---------|
| company | 기업정보 | 0 |
| compliance | 컴플라이언스 | 30 |
| content | 콘텐츠 | 30 |
| privacy | 개인정보 | 30 |
| security | 보안 | 30 |

---

## 4. 통계/분석 테이블 (4개)

### 4.1 guardrail_daily_stats
**역할**: 일별 가드레일 실행 통계 (대시보드용)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | BIGSERIAL | 기본키 |
| stat_date | DATE | 통계 날짜 |
| policy_id | VARCHAR(100) | 정책 ID |
| policy_name | VARCHAR(255) | 정책명 |
| category | VARCHAR(100) | 카테고리 |
| total_checks | INTEGER | 전체 검사 수 |
| pass_count | INTEGER | 통과 수 |
| block_count | INTEGER | 차단 수 |
| warn_count | INTEGER | 경고 수 |
| avg_detection_score | NUMERIC(5,4) | 평균 탐지 점수 |
| avg_processing_time_ms | INTEGER | 평균 처리 시간 |
| unique_users | INTEGER | 유니크 사용자 수 |

**UNIQUE 제약**: (stat_date, policy_id)

---

### 4.2 guardrail_hourly_stats
**역할**: 시간별 가드레일 실행 통계 (실시간 모니터링용)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | BIGSERIAL | 기본키 |
| stat_hour | TIMESTAMP | 통계 시간 |
| total_checks | INTEGER | 전체 검사 수 |
| pass_count | INTEGER | 통과 수 |
| block_count | INTEGER | 차단 수 |
| warn_count | INTEGER | 경고 수 |
| avg_processing_time_ms | INTEGER | 평균 처리 시간 |

---

### 4.3 guardrail_keyword_stats
**역할**: 키워드별 탐지 통계

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | BIGSERIAL | 기본키 |
| stat_date | DATE | 통계 날짜 |
| keyword_id | INTEGER | 키워드 ID |
| keyword_text | VARCHAR(255) | 키워드 텍스트 |
| category | VARCHAR(50) | 카테고리 |
| detection_count | INTEGER | 탐지 수 |
| block_count | INTEGER | 차단 수 |
| warn_count | INTEGER | 경고 수 |

---

### 4.4 guardrail_user_violations
**역할**: 사용자별 위반 통계 (위험 사용자 관리)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | BIGSERIAL | 기본키 |
| user_id | VARCHAR(255) | 사용자 ID |
| user_email | VARCHAR(255) | 사용자 이메일 |
| stat_date | DATE | 통계 날짜 |
| total_violations | INTEGER | 전체 위반 수 |
| block_count | INTEGER | 차단 수 |
| warn_count | INTEGER | 경고 수 |
| violation_categories | JSONB | 위반 카테고리별 통계 |
| last_violation_at | TIMESTAMP | 마지막 위반 시간 |
| risk_level | VARCHAR(20) | 위험 수준 (low/medium/high/critical) |

---

## 5. 기타 테이블 (3개)

### 5.1 guardrail_activities
**역할**: 관리자 활동 로그 (감사 추적)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | BIGSERIAL | 기본키 |
| activity_type | VARCHAR(50) | 활동 유형 (create/update/delete) |
| entity_type | VARCHAR(50) | 대상 엔티티 유형 |
| entity_id | VARCHAR(100) | 대상 엔티티 ID |
| user_id | VARCHAR(255) | 수행한 사용자 ID |
| description | TEXT | 활동 설명 |
| old_value | JSONB | 변경 전 값 |
| new_value | JSONB | 변경 후 값 |
| ip_address | VARCHAR(45) | IP 주소 |
| created_at | TIMESTAMP | 활동 시간 |

---

### 5.2 guardrail_validations
**역할**: 검증 로그

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | BIGSERIAL | 기본키 |
| validation_type | VARCHAR(50) | 검증 유형 |
| input_value | TEXT | 입력 값 |
| is_valid | BOOLEAN | 유효 여부 |
| validation_result | JSONB | 검증 결과 |
| error_message | TEXT | 에러 메시지 |
| processing_time_ms | INTEGER | 처리 시간 |
| user_id | VARCHAR(255) | 사용자 ID |
| created_at | TIMESTAMP | 생성 시간 |

---

### 5.3 guardrail_pii_patterns
**역할**: PII(개인식별정보) 탐지 패턴 정의

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | SERIAL | 기본키 |
| pattern_id | VARCHAR(50) | 패턴 ID (UNIQUE) |
| name | VARCHAR(100) | 패턴 이름 |
| pattern | TEXT | 정규표현식 패턴 |
| description | TEXT | 설명 |
| severity | VARCHAR(20) | 심각도 |
| action_on_detect | VARCHAR(20) | 탐지 시 조치 |
| is_active | BOOLEAN | 활성화 여부 |
| sort_order | INTEGER | 정렬 순서 |

**현재 정의된 PII 패턴**:

| 패턴 ID | 이름 | 정규표현식 | 심각도 | 조치 |
|---------|------|------------|--------|------|
| ssn | 주민등록번호 | `\d{6}[-\s]?\d{7}` | critical | block |
| phone | 전화번호 | `(01[0-9]\|02\|0[3-9][0-9])[-\s]?\d{3,4}[-\s]?\d{4}` | high | warn |
| email | 이메일 | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | high | warn |
| credit_card | 신용카드번호 | `\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}` | critical | block |
| bank_account | 계좌번호 | `\d{3,4}[-\s]?\d{2,4}[-\s]?\d{4,6}` | high | warn |
| passport | 여권번호 | `[A-Z]{1,2}\d{7,8}` | high | warn |
| driver_license | 운전면허번호 | `\d{2}-\d{2}-\d{6}-\d{2}` | high | warn |

---

## 스크립트 사용법

### 1. 새 환경에 데이터베이스 초기화

```bash
# 데이터베이스 생성 (먼저 guardrails_db 데이터베이스를 생성해야 함)
PGPASSWORD='sdc_dev_pass_2025' psql -h 192.168.122.85 -p 5433 -U sdc_dev_user -d postgres -c "CREATE DATABASE guardrails_db WITH ENCODING 'UTF8';"

# 테이블 및 초기 데이터 생성
PGPASSWORD='sdc_dev_pass_2025' psql -h 192.168.122.85 -p 5433 -U sdc_dev_user -d guardrails_db -f init_guardrails_db.sql
```

### 2. 테이블 확인

```bash
# 테이블 목록 확인
PGPASSWORD='sdc_dev_pass_2025' psql -h 192.168.122.85 -p 5433 -U sdc_dev_user -d guardrails_db -c "\dt"

# 키워드 수 확인
PGPASSWORD='sdc_dev_pass_2025' psql -h 192.168.122.85 -p 5433 -U sdc_dev_user -d guardrails_db -c "SELECT COUNT(*) FROM guardrail_keywords;"
```

---

## 문서 정보
- **작성일**: 2026-01-14
- **대상 데이터베이스**: guardrails_db
- **테이블 수**: 22개
- **초기 데이터**: 키워드 243개, PII 패턴 7개, 설정 5개 등
