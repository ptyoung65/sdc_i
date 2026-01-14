# 가드레일 화면-테이블 연관관계 문서

## 개요
이 문서는 Open WebUI의 가드레일 관련 화면들과 `guardrails_db` 데이터베이스 테이블 간의 연관관계를 설명합니다.

> **수정 이력**: 2026-01-14 - 미사용 테이블 13개 삭제 (22개 → 9개)

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              프론트엔드 (Svelte)                                  │
│                                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ guardrails  │  │ guardrails2 │  │ dashboard2  │  │ monitoring / monitoring2│ │
│  │  +page      │  │  +page      │  │  +page      │  │      +page              │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                │                      │               │
│         └────────────────┼────────────────┼──────────────────────┘               │
│                          │                │                                      │
│                          ▼                ▼                                      │
│              ┌─────────────────────────────────────────┐                        │
│              │  Guardrails.svelte (공통 컴포넌트)       │                        │
│              │  - 대시보드 탭                           │                        │
│              │  - 정책 현황 탭                          │                        │
│              │  - 정책 관리 탭                          │                        │
│              │  - 기준정보 관리 탭                      │                        │
│              └─────────────────┬───────────────────────┘                        │
│                                │                                                 │
└────────────────────────────────┼─────────────────────────────────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ▼                                     ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│ Arthur Guardrails API   │           │ Monitoring Backend API  │
│ (포트: 8001)            │           │ (포트: 3001)            │
│                         │           │                         │
│ - /health               │           │ - /api/guardrails/*     │
│ - /keywords             │           │ - /api/dashboard/*      │
│ - /settings             │           │ - /api/monitoring/*     │
│ - /logs                 │           │                         │
│ - /test                 │           │                         │
└───────────┬─────────────┘           └───────────┬─────────────┘
            │                                     │
            └─────────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │         guardrails_db             │
              │       (PostgreSQL 5433)           │
              │                                   │
              │          9개 테이블               │
              └───────────────────────────────────┘
```

---

## 화면별 테이블 연관관계

### 1. 가드레일 관리 화면 (`/admin/guardrails`, `/admin/guardrails2`)

**경로**: `src/routes/(app)/admin/guardrails/+page.svelte`
**컴포넌트**: `src/lib/components/admin/Settings/Guardrails.svelte`

#### 1.1 대시보드 탭

| 화면 요소 | API 엔드포인트 | 사용 테이블 | 설명 |
|-----------|---------------|-------------|------|
| 정책 통계 카드 | `/api/guardrails/dashboard` | `guardrail_policies` | 전체/활성 정책 수 |
| 검사 결과 통계 | `/api/guardrails/dashboard` | `guardrail_check_logs` | pass/block/warn 건수 |
| 정책별 사용 현황 | `/api/guardrails/dashboard` | `guardrail_policies` + `guardrail_check_logs` | 정책별 검사 건수 |
| 최근 차단 로그 | `/api/guardrails/dashboard` | `guardrail_check_logs` + `guardrail_policies` | 최근 10건 차단 이력 |
| 추이 차트 | `/api/guardrails/trend` | `guardrail_check_logs` | 일별/시간별 검사 추이 |

#### 1.2 정책 현황 탭

| 화면 요소 | API 엔드포인트 | 사용 테이블 | 설명 |
|-----------|---------------|-------------|------|
| 정책 목록 | `/api/guardrails/policies` | `guardrail_policies` | 정책 ID, 이름, 카테고리, 심각도 |
| 정책별 통계 | `/api/guardrails/policies` | `guardrail_check_logs` | 정책별 검사/차단/경고 건수 |
| 필터 (정책유형) | - | `guardrail_master_policy_types` | 드롭다운 필터 |
| 필터 (필터유형) | - | `guardrail_master_filter_types` | 드롭다운 필터 |
| 필터 (심각도) | - | `guardrail_master_severity_levels` | 드롭다운 필터 |
| 필터 (동작유형) | - | `guardrail_master_action_types` | 드롭다운 필터 |

#### 1.3 정책 관리 탭

| 화면 요소 | API 엔드포인트 | 사용 테이블 | 설명 |
|-----------|---------------|-------------|------|
| 정책 생성 | `POST /api/guardrails/policies` | `guardrail_policies` | 새 정책 등록 |
| 정책 수정 | `PUT /api/guardrails/policies/{id}` | `guardrail_policies` | 정책 내용 수정 |
| 정책 삭제 | `DELETE /api/guardrails/policies/{id}` | `guardrail_policies`, `guardrail_check_logs` | 정책 및 관련 로그 삭제 |
| 활성화 토글 | `PUT /api/guardrails/policies/{id}/toggle` | `guardrail_policies` | enabled 상태 변경 |
| 엑셀 내보내기 | `/api/guardrails/policies/export` | `guardrail_policies` | CSV/Excel 다운로드 |
| CSV 가져오기 | `POST /api/guardrails/policies/import` | `guardrail_policies` | 대량 정책 등록 |

#### 1.4 기준정보 관리 탭

| 서브탭 | API 엔드포인트 | 사용 테이블 | 설명 |
|--------|---------------|-------------|------|
| 정책 유형 | `/api/guardrails/master/policy-types` | `guardrail_master_policy_types` | 정책 유형 코드 관리 |
| 필터 유형 | `/api/guardrails/master/filter-types` | `guardrail_master_filter_types` | 필터 유형 코드 관리 |
| 심각도 | `/api/guardrails/master/severity-levels` | `guardrail_master_severity_levels` | 심각도 레벨 관리 |
| 동작 유형 | `/api/guardrails/master/action-types` | `guardrail_master_action_types` | 조치 유형 관리 |
| 전체 조회 | `/api/guardrails/master/all` | 위 4개 테이블 모두 | 초기 데이터 로드 |

---

### 2. Arthur Guardrails 서비스 (포트 8001)

**API 파일**: `src/lib/apis/guardrails.ts`

| API 엔드포인트 | 사용 테이블 | 설명 |
|---------------|-------------|------|
| `GET /health` | `guardrail_keywords`, `guardrail_settings` | 서비스 상태 및 키워드 수 |
| `GET /keywords` | `guardrail_keywords` | 필터링 키워드 목록 |
| `POST /keywords` | `guardrail_keywords` | 키워드 추가 |
| `PUT /keywords/{id}` | `guardrail_keywords` | 키워드 수정 |
| `DELETE /keywords/{id}` | `guardrail_keywords` | 키워드 삭제 |
| `GET /settings` | `guardrail_settings` | 전역 설정 조회 |
| `PUT /settings/{key}` | `guardrail_settings` | 설정값 변경 |
| `POST /test` | `guardrail_keywords`, `guardrail_logs` | 텍스트 검사 및 로그 기록 |
| `GET /logs` | `guardrail_logs` | 검사 로그 조회 |
| `GET /logs/stats` | `guardrail_logs` | 로그 통계 |

---

### 3. Dashboard2 화면 (`/admin/dashboard2`)

**경로**: `src/routes/(app)/admin/dashboard2/+page.svelte`
**API 서버**: Monitoring Backend (포트 3001)

| 화면 요소 | API 엔드포인트 | 사용 테이블 (sdc_dev) | 비고 |
|-----------|---------------|----------------------|------|
| 사용자 통계 | `/api/dashboard/summary` | `chat`, `user` | sdc_dev 사용 |
| 질문 통계 | `/api/dashboard/summary` | `chat` | sdc_dev 사용 |
| 로그 목록 | `/api/dashboard/logs` | `chat`, `feedback` | sdc_dev 사용 |
| 엑셀 다운로드 | `/api/dashboard/export` | `chat`, `user` | sdc_dev 사용 |

> **참고**: Dashboard2는 가드레일 테이블을 직접 사용하지 않고, `sdc_dev` 데이터베이스의 채팅 로그를 사용합니다.

---

## 테이블별 화면 연관관계

### 기본 테이블 (5개)

| 테이블명 | 연관 화면 | 용도 |
|---------|----------|------|
| `guardrail_keywords` | Guardrails 서비스, 기준정보 | 실시간 필터링에 사용되는 키워드 |
| `guardrail_settings` | Guardrails 서비스 | 전역 설정 (활성화 여부, 민감도 등) |
| `guardrail_logs` | Guardrails 서비스 | 기본 검사 로그 |
| `guardrail_policies` | 가드레일 관리 전체 | 정책 정의 및 관리 |
| `guardrail_check_logs` | 대시보드, 정책 현황 | 상세 검사 로그, 통계 집계 |

### 마스터 테이블 (4개)

| 테이블명 | 연관 화면 | 용도 |
|---------|----------|------|
| `guardrail_master_policy_types` | 기준정보 관리 > 정책유형 | 정책 유형 코드 정의 |
| `guardrail_master_filter_types` | 기준정보 관리 > 필터유형 | 필터 유형 코드 정의 |
| `guardrail_master_severity_levels` | 기준정보 관리 > 심각도 | 심각도 레벨 정의 |
| `guardrail_master_action_types` | 기준정보 관리 > 동작유형 | 조치 유형 정의 |

---

## 데이터 흐름도

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              사용자 입력                                     │
│                         (채팅 메시지 입력)                                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Arthur Guardrails 서비스                             │
│                              (포트 8001)                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  1. guardrail_settings 에서 활성화 여부 확인                          │  │
│  │  2. guardrail_keywords 에서 키워드 매칭                               │  │
│  │  3. guardrail_pii_patterns 에서 PII 패턴 검사                         │  │
│  │  4. guardrail_logs 에 검사 결과 기록                                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
   ┌────────────┐         ┌────────────┐         ┌────────────┐
   │   통과     │         │   경고     │         │   차단     │
   │  (PASS)    │         │  (WARN)    │         │  (BLOCK)   │
   └──────┬─────┘         └──────┬─────┘         └──────┬─────┘
          │                       │                       │
          ▼                       ▼                       ▼
   ┌──────────────────────────────────────────────────────────┐
   │              guardrail_check_logs 에 상세 기록            │
   │  - user_id, user_email                                   │
   │  - original_text, processed_text                         │
   │  - policy_id, check_result                               │
   │  - detected_keywords, detection_score                    │
   └──────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────┐
   │                    통계 테이블 집계                        │
   │  - guardrail_daily_stats (일별)                          │
   │  - guardrail_hourly_stats (시간별)                       │
   │  - guardrail_keyword_stats (키워드별)                    │
   │  - guardrail_user_violations (사용자별)                  │
   └──────────────────────────────────────────────────────────┘
```

---

## API 엔드포인트 요약

### Monitoring Backend API (포트 3001)

| 메서드 | 엔드포인트 | 테이블 | 설명 |
|--------|-----------|--------|------|
| GET | `/api/guardrails/dashboard` | policies, check_logs | 대시보드 통계 |
| GET | `/api/guardrails/policies` | policies, check_logs | 정책 목록 |
| POST | `/api/guardrails/policies` | policies | 정책 생성 |
| PUT | `/api/guardrails/policies/{id}` | policies | 정책 수정 |
| DELETE | `/api/guardrails/policies/{id}` | policies, check_logs | 정책 삭제 |
| PUT | `/api/guardrails/policies/{id}/toggle` | policies | 활성화 토글 |
| GET | `/api/guardrails/trend` | check_logs | 추이 데이터 |
| GET | `/api/guardrails/logs` | check_logs | 로그 목록 |
| GET | `/api/guardrails/master/all` | master_* (4개) | 기준정보 전체 |
| GET | `/api/guardrails/master/policy-types` | master_policy_types | 정책유형 |
| GET | `/api/guardrails/master/filter-types` | master_filter_types | 필터유형 |
| GET | `/api/guardrails/master/severity-levels` | master_severity_levels | 심각도 |
| GET | `/api/guardrails/master/action-types` | master_action_types | 동작유형 |

### Arthur Guardrails API (포트 8001)

| 메서드 | 엔드포인트 | 테이블 | 설명 |
|--------|-----------|--------|------|
| GET | `/health` | keywords, settings | 서비스 상태 |
| GET | `/keywords` | keywords | 키워드 목록 |
| POST | `/keywords` | keywords | 키워드 추가 |
| PUT | `/keywords/{id}` | keywords | 키워드 수정 |
| DELETE | `/keywords/{id}` | keywords | 키워드 삭제 |
| GET | `/settings` | settings | 설정 조회 |
| PUT | `/settings/{key}` | settings | 설정 변경 |
| POST | `/test` | keywords, logs | 텍스트 검사 |
| GET | `/logs` | logs | 로그 조회 |
| GET | `/logs/stats` | logs | 통계 조회 |

---

## 문서 정보
- **작성일**: 2026-01-14
- **대상 시스템**: Open WebUI 가드레일 모듈
- **데이터베이스**: guardrails_db (PostgreSQL 5433)
- **프론트엔드**: Svelte
- **백엔드 API**: FastAPI (3001), Arthur Guardrails (8001)
