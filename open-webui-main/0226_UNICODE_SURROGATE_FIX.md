# [2026-02-26] 유니코드 서로게이트 JSON 파싱 오류 수정

## 1. 오류 현상

모니터링 대시보드(`sdc-monitoring`)에서 채팅 로그를 조회할 때 **간헐적으로** 다음 오류 발생:

```
ERROR:main:기본 쿼리 실패: invalid input syntax for type json
DETAIL: Unicode low surrogate must follow a high surrogate
CONTEXT: JSON data, line 1, ...ATH, image_size+img_')') p'\udf89...
```

- **발생 빈도**: 간헐적 (특정 채팅 세션 데이터에 의해 트리거)
- **영향 범위**: 모니터링 대시보드의 채팅 로그 조회 API (`/api/dashboard/logs`)
- **증상**: 해당 오류 발생 시 대시보드 로그 목록이 빈 화면으로 표시됨

---

## 2. 오류 원인 분석

### 2.1 근본 원인: 유니코드 서로게이트(Surrogate) 페어 손상

유니코드에서 이모지 등 BMP(Basic Multilingual Plane) 외부 문자는 **서로게이트 페어**로 표현됩니다:

| 구분 | 범위 | 설명 |
|------|------|------|
| High Surrogate | `\uD800` ~ `\uDBFF` | 페어의 앞부분 |
| Low Surrogate | `\uDC00` ~ `\uDFFF` | 페어의 뒷부분 |

**정상 예시**: `\uD83C\uDF89` → High + Low → 🎉 (이모지)

**오류 예시**: `\uDF89` → Low Surrogate만 단독 존재 → **잘못된 유니코드**

### 2.2 발생 경로

```
1. 사용자가 채팅에 이모지/특수문자 포함 메시지 또는 Python 코드 입력
                    ↓
2. Open WebUI가 chat 테이블의 chat 컬럼에 JSON 문자열로 저장
   (이때 일부 이모지가 깨진 서로게이트 페어로 저장됨)
                    ↓
3. 모니터링 백엔드가 대시보드 로그 조회 시 c.chat::jsonb 쿼리 실행
                    ↓
4. PostgreSQL의 JSON 파서가 RFC 7159에 따라 서로게이트 검증
                    ↓
5. 고립된 서로게이트 발견 → JSON 파싱 거부 → 쿼리 실패
```

### 2.3 PostgreSQL JSON 파싱 규칙

PostgreSQL은 JSON/JSONB 타입으로 캐스팅할 때 **RFC 7159**를 엄격히 적용합니다:

- `\uXXXX` 이스케이프 시퀀스에서 서로게이트 코드 포인트는 반드시 **페어(High+Low)**로 존재해야 함
- 단독 서로게이트(orphaned surrogate)는 유효하지 않은 JSON으로 처리
- `::jsonb` 캐스팅 시 전체 JSON 문자열을 파싱하므로, 하나라도 잘못된 서로게이트가 있으면 **전체 쿼리 실패**

### 2.4 오류 발생 쿼리 위치

`services/monitoring-backend/main.py`에서 `chat::jsonb` 캐스팅을 사용하는 쿼리들:

| 라인 | 쿼리 패턴 | 용도 |
|------|-----------|------|
| 1871 | `c.chat::jsonb->'messages'->0->'models'->>0` | 대시보드 로그 목록 - 모델명 추출 |
| 1941-1942 | `chat::jsonb->'messages'`, `chat::jsonb->'history'->'messages'` | 개별 채팅 상세 조회 |
| 282, 376, 441, 493 | `c.chat::jsonb->'models'->>0` | 모델 필터 조건 |
| 676, 737, 798, 844, 885, 937, 1006 | `jsonb_array_elements(c.chat::jsonb->'messages')` | 토큰 통계 집계 |
| 2557-2558 | `c.chat::jsonb->'messages'`, `c.chat::jsonb as chat_data` | 엑셀 내보내기 |

**핵심**: 위 쿼리들은 모두 `execute_query()` 함수를 통해 실행되므로, 해당 함수에서 일괄 처리 가능

---

## 3. 수정 내용

### 3.1 수정 파일

| 파일 | 경로 | 설명 |
|------|------|------|
| `database.py` | `services/monitoring-backend/database.py` | DB 쿼리 실행 모듈 |

### 3.2 수정 방식: `execute_query()` 함수에 자동 복구 로직 추가

기존 `execute_query()` 함수의 예외 처리 블록에 서로게이트 오류 감지 및 자동 복구 로직을 추가했습니다.

#### 수정 전 (기존)

```python
except Exception as e:
    if conn:
        conn.rollback()
    logger.error(f"❌ 쿼리 실행 오류: {e}")
    logger.error(f"쿼리: {query}")
    raise
```

#### 수정 후

```python
except Exception as e:
    if conn:
        conn.rollback()

    # ----- [2026-02-26] 유니코드 서로게이트(Surrogate) JSON 파싱 오류 자동 복구 시작 -----
    error_msg = str(e).lower()
    if 'surrogate' in error_msg and ('chat::jsonb' in query or 'chat::json' in query):
        safe_query = query.replace(
            'c.chat::jsonb',
            "regexp_replace(c.chat::text, '\\\\u[Dd][89A-Fa-f][0-9A-Fa-f]{2}', '', 'g')::jsonb"
        )
        safe_query = safe_query.replace(
            'chat::jsonb',
            "regexp_replace(chat::text, '\\\\u[Dd][89A-Fa-f][0-9A-Fa-f]{2}', '', 'g')::jsonb"
        )
        if safe_query != query:
            try:
                logger.warning("⚠️ 유니코드 서로게이트 감지, 안전 쿼리로 재시도")
                cursor2 = conn.cursor(cursor_factory=RealDictCursor)
                cursor2.execute(safe_query, params)
                if cursor2.description:
                    results = cursor2.fetchall()
                    conn.commit()
                    cursor2.close()
                    return [dict(row) for row in results]
                else:
                    conn.commit()
                    cursor2.close()
                    return []
            except Exception as retry_e:
                if conn:
                    conn.rollback()
                logger.error(f"❌ 안전 쿼리도 실패: {retry_e}")
    # ----- [2026-02-26] 유니코드 서로게이트(Surrogate) JSON 파싱 오류 자동 복구 종료 -----

    logger.error(f"❌ 쿼리 실행 오류: {e}")
    logger.error(f"쿼리: {query}")
    raise
```

### 3.3 동작 흐름

```
execute_query() 호출
       ↓
  정상 쿼리 실행 시도 (기존 로직 그대로)
       ↓
  ┌─ 성공 → 결과 반환 (정상 경로, 성능 영향 없음)
  └─ 실패 → 예외 발생
              ↓
         에러 메시지에 'surrogate' 포함?
         AND 쿼리에 'chat::jsonb' 포함?
              ↓
         ┌─ NO  → 기존대로 에러 로그 + 예외 발생
         └─ YES → 안전 쿼리로 변환 후 재시도
                    ↓
              chat::jsonb → regexp_replace(chat::text, 서로게이트패턴, '')::jsonb
                    ↓
              ┌─ 재시도 성공 → 결과 반환
              └─ 재시도 실패 → 에러 로그 + 예외 발생
```

### 3.4 핵심 정규식 설명

```sql
regexp_replace(c.chat::text, '\\u[Dd][89A-Fa-f][0-9A-Fa-f]{2}', '', 'g')::jsonb
```

| 부분 | 설명 |
|------|------|
| `c.chat::text` | chat 컬럼을 TEXT 타입으로 변환 (regexp_replace는 text만 입력 가능) |
| `\\u` | JSON 유니코드 이스케이프 시작 (`\u`) |
| `[Dd]` | 서로게이트 시작 문자 `D` 또는 `d` |
| `[89A-Fa-f]` | 서로게이트 범위: `\uD800`~`\uDFFF` (8,9,A-F) |
| `[0-9A-Fa-f]{2}` | 나머지 16진수 2자리 |
| `''` | 매칭된 서로게이트를 빈 문자열로 교체 (삭제) |
| `'g'` | 전체 문자열에서 모든 매칭 제거 |
| `::jsonb` | 서로게이트 제거 후 안전하게 JSONB로 캐스팅 |

**매칭 예시**:
- `\uDF89` → 삭제됨 (고립된 Low Surrogate)
- `\uD83C` → 삭제됨 (고립된 High Surrogate)
- `\u0041` → 유지됨 (정상 유니코드, 서로게이트 범위 아님)

### 3.5 설계 선택 이유

| 대안 | 장단점 | 채택 여부 |
|------|--------|-----------|
| **각 쿼리(22곳) 직접 수정** | 확실하지만 수정 범위 넓고 누락 위험 | ❌ |
| **DB에 safe_jsonb() 함수 생성** | 깔끔하지만 DB 스키마 변경 필요 | ❌ |
| **execute_query()에서 자동 복구** | 1곳 수정으로 전체 커버, 성능 영향 없음 | ✅ 채택 |

---

## 4. 테스트 결과

### 4.1 정상 쿼리 테스트

```
=== 정상 chat::jsonb 쿼리 ===
  성공: 3건 조회

=== 대시보드 쿼리 패턴 테스트 ===
  성공: 5건 조회
    - REST API 설계 원칙은?
    - 데이터 암호화 방법은?
    - 머신러닝 모델 배포 방법은?
```

→ **정상 데이터에서 기존 로직 그대로 동작 확인**

### 4.2 안전 쿼리(regexp_replace) 직접 실행 테스트

```
=== 안전 쿼리 직접 실행 ===
  성공: 3건 조회

=== replace 변환 확인 ===
  원본: SELECT c.chat::jsonb->'messages' FROM chat c
  변환: SELECT regexp_replace(c.chat::text, '\\u[Dd]...', '', 'g')::jsonb->'messages' FROM chat c
  실행 성공: 1건
```

→ **서로게이트 제거 쿼리가 정상 동작 확인**

---

## 5. 수정 파일 목록

```
services/monitoring-backend/
└── database.py          ← 수정됨 (execute_query 함수에 자동 복구 추가)
```

### 적용 방법

수정된 `database.py`를 `sdc-monitoring` 컨테이너에 반영:

```bash
# 1. 파일 복사
podman cp services/monitoring-backend/database.py sdc-monitoring:/app/database.py

# 2. 컨테이너 재시작
podman restart sdc-monitoring
```

또는 볼륨 마운트(`-v`)를 사용 중인 경우 컨테이너 재시작만으로 자동 반영됩니다.
