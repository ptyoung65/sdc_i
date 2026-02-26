# [2026-02-26] 공지사항 팝업 다시보기 기능 추가 및 MAX_POPUP_COUNT 주석 보강

## 1. 변경 개요

### 1.1 공지사항 다시보기 아이콘 추가 (Navbar)
Navbar 상단 우측에 **메가폰(확성기) 아이콘**을 추가하여, 모든 사용자(관리자+일반)가 언제든 활성 공지사항 팝업을 다시 볼 수 있도록 기능 구현.

### 1.2 MAX_POPUP_COUNT 기능 흐름 주석 보강
팝업 표시 개수(MAX_POPUP_COUNT) 설정이 저장되고 적용되는 전체 데이터 흐름을 관련 4개 파일에 `[2026-02-26]` 날짜 주석으로 상세 문서화.

---

## 2. 신규 기능: 공지사항 다시보기

### 2.1 기능 설명

| 항목 | 내용 |
|------|------|
| **대상** | 모든 사용자 (admin + user 공통) |
| **아이콘** | 메가폰(확성기) SVG |
| **위치** | Navbar 우측 아이콘 중 첫 번째 (알림설정 벨 아이콘 왼쪽) |
| **Tooltip** | "공지사항 다시보기" |
| **공지 있을 때** | PopupAnnouncementModal 팝업 표시 |
| **공지 없을 때** | toast.info('등록된 공지사항이 없습니다.') |

### 2.2 로그인 시 자동 팝업과의 차이

| 항목 | 로그인 시 자동 팝업 (+layout.svelte) | 다시보기 버튼 (Navbar.svelte) |
|------|------|------|
| 호출 시점 | onMount 자동 실행 | 사용자 클릭 시 |
| "오늘 하루 보지 않기" | 적용됨 (localStorage 날짜키 체크) | **무시 (항상 표시)** |
| exportConfig 호출 | O (MAX_POPUP_COUNT 프론트에서도 제한) | X (백엔드에서만 제한, 404 오류 방지) |
| MAX_POPUP_COUNT 적용 | 백엔드 + 프론트엔드 이중 제한 | 백엔드에서만 제한 |

### 2.3 Navbar 아이콘 순서 (좌→우)

```
[공지 다시보기(전체)] → [알림설정(admin)] → [관리자패널(admin)] → [주야간(전체)] → [설정(admin)] → [프로필] → [도움말] → [카테고리]
```

---

## 3. MAX_POPUP_COUNT 데이터 흐름 상세

### 3.1 저장 흐름 (관리자 설정 화면)

```
관리자: /admin/settings/notification 에서 팝업 표시 개수 입력 (1~10)
    ↓
Notification.svelte handlePopupCountChange()
    ↓ (1초 디바운스)
Notification.svelte savePopupCount()
    ↓
configs/index.ts updateConfigPartial(token, { MAX_POPUP_COUNT: N })
    ↓
configs/index.ts exportConfig() → GET /api/v1/configs/export (현재 설정 조회)
    ↓
기존 config에 { MAX_POPUP_COUNT: N } 병합
    ↓
configs/index.ts importConfig() → POST /api/v1/configs/import
    ↓
configs.py import_config() → save_config(form_data.config)
    ↓
PostgreSQL config 테이블 → data 컬럼(JSONB) → MAX_POPUP_COUNT 키 저장
```

### 3.2 적용 흐름 (로그인 시 팝업)

```
+layout.svelte onMount()
    ↓
loadPopupAnnouncements()
    ↓
exportConfig(token) → GET /api/v1/configs/export → MAX_POPUP_COUNT 조회
    ↓
getActiveAnnouncements(token) → GET /api/v1/configs/announcements/active
    ↓
configs.py get_active_announcements():
  - get_config() → config 테이블에서 MAX_POPUP_COUNT 읽기 (기본값 3)
  - PopupAnnouncements.get_active_announcements(limit=max_popup_count)
  - 활성 공지 중 최근 N개만 반환
    ↓
+layout.svelte에서 start_date 내림차순 정렬 → maxPopupCount개로 이중 제한
    ↓
PopupAnnouncementModal 컴포넌트에 전달 → 팝업 표시
```

### 3.3 적용 흐름 (Navbar 공지 다시보기)

```
사용자: Navbar 메가폰 아이콘 클릭
    ↓
Navbar.svelte loadAndShowAnnouncements()
    ↓
getActiveAnnouncements(token) → GET /api/v1/configs/announcements/active
    ↓
configs.py get_active_announcements():
  - get_config() → MAX_POPUP_COUNT 읽기 (기본값 3)
  - 활성 공지 중 최근 N개만 반환
    ↓
Navbar.svelte에서 start_date 내림차순 정렬
    ↓
PopupAnnouncementModal 컴포넌트에 전달 → 팝업 표시
```

---

## 4. 수정 파일 상세

### 4.1 Navbar.svelte (신규 기능 + 주석 보강)
**경로**: `src/lib/components/chat/Navbar.svelte`

| 변경 항목 | 내용 |
|---|---|
| import 추가 | PopupAnnouncementModal, getActiveAnnouncements |
| 상태 변수 추가 | showAnnouncementPopup, popupAnnouncements |
| 함수 추가 | loadAndShowAnnouncements() - 활성 공지 로드 후 팝업 표시 |
| 아이콘 버튼 추가 | 메가폰 SVG 아이콘 (모든 사용자 표시) |
| 모달 렌더링 추가 | PopupAnnouncementModal (bind:show, announcements, on:close) |
| [2026-02-26] 주석 | import 설명, 함수 데이터 흐름, 아이콘 버튼 동작 설명, 모달 Props/Events 설명 |
| 404 오류 수정 | exportConfig 호출 제거 (백엔드에서 MAX_POPUP_COUNT 적용하므로 불필요) |

### 4.2 Notification.svelte (주석 보강)
**경로**: `src/lib/components/admin/Settings/Notification.svelte`

| 변경 항목 | 내용 |
|---|---|
| [2026-02-26] 블록 주석 추가 | MAX_POPUP_COUNT 전체 데이터 흐름 (저장 경로, 적용 경로) 상세 설명 |
| loadPopupSettings 주석 | exportConfig로 현재 값 조회 과정 설명 |
| savePopupCount 주석 | updateConfigPartial로 저장 과정 설명 |
| handlePopupCountChange 주석 | 디바운스 자동 저장 과정 설명 |
| UI 영역 주석 | input 값 변경 → 저장 경로 → 적용 시점 설명 |

### 4.3 configs.py (주석 보강)
**경로**: `backend/open_webui/routers/configs.py`

| 변경 항목 | 내용 |
|---|---|
| [2026-02-26] 블록 주석 추가 | get_active_announcements 함수 내 MAX_POPUP_COUNT 적용 상세 설명 |
| 설정값 조회 과정 | get_config() → config 테이블 data(JSONB) 조회 과정 |
| 설정값 저장 경로 | Notification.svelte → updateConfigPartial → importConfig → DB 저장 |
| 호출하는 곳 | +layout.svelte (로그인 시), Navbar.svelte (다시보기 클릭 시) |

### 4.4 +layout.svelte (주석 보강)
**경로**: `src/routes/(app)/+layout.svelte`

| 변경 항목 | 내용 |
|---|---|
| [2026-02-26] 블록 주석 추가 | loadPopupAnnouncements 함수 전체 데이터 흐름 설명 |
| 호출 시점 | onMount → 페이지 최초 로드 시 |
| MAX_POPUP_COUNT 반영 경로 | 관리자 설정 변경 → config 테이블 저장 → 다음 로그인 시 적용 |
| 인라인 주석 | exportConfig 호출, getActiveAnnouncements 호출, 이중 제한 적용 |

---

## 5. DB 저장 구조

### config 테이블

| 항목 | 내용 |
|---|---|
| 테이블 | config |
| 컬럼 | data (JSONB) |
| 키 | MAX_POPUP_COUNT |
| 값 타입 | 정수 (1~10) |
| 기본값 | 3 |

```json
{
  "MAX_POPUP_COUNT": 5,
  "DEFAULT_MODELS": "...",
  "MODEL_ORDER_LIST": [...],
  ...
}
```

---

## 6. 영향 범위

### 영향 받는 화면
- `/` (메인 채팅 화면) - Navbar에 공지 다시보기 아이콘 추가
- `/admin/settings/notification` - MAX_POPUP_COUNT 주석 보강 (기능 변경 없음)

### 영향 받는 API
- `GET /api/v1/configs/announcements/active` - 주석 보강 (기능 변경 없음)

### 영향 받지 않는 API/화면
- `GET /api/v1/configs/export` - 변경 없음
- `POST /api/v1/configs/import` - 변경 없음
- 기타 모든 API - 변경 없음

---

## 7. 패키지 파일 목록

```
0226.noti.tar.gz
├── 0226_NOTIFICATION_CHANGELOG.md                         # 본 설명서
├── src/lib/components/chat/Navbar.svelte                  # 공지 다시보기 아이콘+모달+주석
├── src/lib/components/admin/Settings/Notification.svelte  # MAX_POPUP_COUNT 주석 보강
├── src/routes/(app)/+layout.svelte                        # 팝업 로드 주석 보강
└── backend/open_webui/routers/configs.py                  # 백엔드 주석 보강
```

---

## 8. 배포 순서

### Step 1: 파일 배포
```bash
# 수정된 파일을 해당 경로에 배포 (tar.gz 해제 시 디렉토리 구조 유지)
cd /home/chatpro/open-webui-main
tar xzf 0226.noti.tar.gz
```

### Step 2: 프론트엔드 빌드
```bash
cd /home/chatpro/open-webui-main
npm run build
```

### Step 3: 컨테이너 재시작
```bash
podman restart sdc-open-webui
```

### Step 4: 검증
- 일반 사용자: 메가폰 아이콘 클릭 → 활성 공지팝업 표시
- 관리자: 메가폰 아이콘 클릭 → 활성 공지팝업 표시
- 관리자: /admin/settings/notification → 팝업 표시 개수 변경 → 저장 → 다시보기 클릭 시 변경된 개수 반영
- 공지 없을 때: 클릭 시 toast "등록된 공지사항이 없습니다" 표시
