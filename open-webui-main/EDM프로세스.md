# EDM 프로세스 상세 설명서

**작성일**: 2025-11-11
**버전**: 3.1
**목적**: Open WebUI EDM 문서 활용 기능의 전체 프로세스 및 설정 가이드

---

## 목차

1. [개요](#1-개요)
2. [오늘 수정사항 (2025-11-11)](#2-오늘-수정사항-2025-11-11)
3. [EDM 다운로드 프로세스](#3-edm-다운로드-프로세스)
4. [벡터라이징 프로세스](#4-벡터라이징-프로세스)
5. [채팅 통합 프로세스](#5-채팅-통합-프로세스)
6. [설정 파일 구조](#6-설정-파일-구조)
7. [프로세스 흐름도](#7-프로세스-흐름도)
8. [문제 해결](#8-문제-해결)

---

## 1. 개요

### 1.1 EDM 시스템이란?

**EDM (Enterprise Document Management)**은 삼성디스플레이의 전자문서관리 시스템으로, 회사 내 모든 문서를 체계적으로 관리하는 플랫폼입니다.

### 1.2 Open WebUI와의 통합

Open WebUI는 EDM 문서를 AI 챗봇에서 활용할 수 있도록 다음 기능을 제공합니다:

- **📥 EDM 파일 다운로드**: N8N 워크플로우를 통한 자동 다운로드
- **🔄 자동 벡터라이징**: Open WebUI 백엔드의 표준 파일 처리 API 활용
- **💬 지능형 검색**: 벡터 검색 기반 문서 활용
- **🎯 카테고리별 관리**: 사규, IT Help Desk, 지식용어 사전 등

---

## 2. 오늘 수정사항 (2025-11-11)

### 2.1 UI/UX 개선

#### 2.1.1 사이드바 라디오 버튼 변경

**파일**: `/src/lib/components/layout/RightSidebar.svelte`

**변경 내용**:
- 체크박스(다중 선택) → 라디오 버튼(단일 선택)
- 선택 로직 단순화: `selectedCategories.set()` 사용

```javascript
const toggleCategory = (displayCategory) => {
    const { actualIds } = displayCategory;
    const allSelected = actualIds.every(id => $selectedCategories.includes(id));

    if (allSelected) {
        // 이미 선택된 카테고리 → 선택 해제
        selectedCategories.set([]);
    } else {
        // 다른 카테고리 → 기존 선택 모두 해제하고 새로 선택
        selectedCategories.set(actualIds);
    }
};
```

**UI 변경**:
```svelte
<!-- Before: Checkbox -->
<div class="w-5 h-5 rounded border-2">
    {#if selected}<svg>✓</svg>{/if}
</div>

<!-- After: Radio Button -->
<div class="w-5 h-5 rounded-full border-2">
    {#if selected}<div class="w-2.5 h-2.5 rounded-full bg-white"></div>{/if}
</div>
```

#### 2.1.2 대사우 Assistant 카테고리 관리

**파일**: `/src/lib/components/chat/Chat.svelte`

**카테고리 구조**:
```javascript
const categories = [
    // 활성화된 카테고리
    { id: 'report', name: '보고서 초안 작성', ... },
    { id: 'edm', name: 'EDM 문서활용', ... },
    { id: 'dictionary', name: '대사우 Assistant [지식용어 사전]', ... },
    { id: 'code', name: 'Code 개발 지원', ... },

    // 준비중 카테고리 (비활성화)
    { id: 'guide', name: '대사우 Assistant [사규]', comingSoon: true },
    { id: 'helpdesk', name: '대사우 Assistant [IT Help Desk]', comingSoon: true }
];
```

**비활성화 처리**:
```javascript
// 카드 컨테이너 스타일
class="{category.comingSoon
    ? 'bg-gray-100 dark:bg-gray-800/60 opacity-40 pointer-events-none cursor-not-allowed'
    : 'bg-white dark:bg-gray-800 hover:shadow-xl'}"

// 버튼 비활성화
disabled={category.comingSoon}

// 클릭 핸들러 체크
if (category.comingSoon) {
    toast.error('🚧 아직 준비중입니다');
    return;
}
```

#### 2.1.3 대사우 Assistant 상세 페이지 비활성화

**파일**: `/src/lib/components/chat/Chat.svelte` (3561-3615번 라인)

**회사생활가이드 카드**:
```svelte
<div class="flex flex-col gap-2 p-4 rounded-xl
     bg-gray-100 dark:bg-gray-800/60
     border-2 border-gray-300 dark:border-gray-600
     opacity-40 pointer-events-none cursor-not-allowed">
    <div class="flex items-center gap-2 mb-2">
        <span>📋</span>
        <h4>회사생활가이드</h4>
    </div>
    <button disabled>육아휴직 신청 방법 알려 줘</button>
    <button disabled>연간 패밀리넷 사용 금액 알려 줘</button>
</div>
```

#### 2.1.4 외부 모델 비활성화

**파일**: `/src/lib/components/chat/Chat.svelte` (316번 라인)

**변경 내용**:
```javascript
// Before: 모든 모델을 models 스토어에 저장
models.set(allModels);

// After: 내부 모델만 저장
models.set(allModels.filter(m => getModelType(m) === 'internal'));
```

**효과**:
- 모델 선택 드롭다운에 내부 모델만 표시
- 외부 모델(external_llm) 선택 불가

#### 2.1.5 메시지 전송 버튼 비활성화

**파일**: `/src/lib/components/chat/Chat.svelte`, `/src/lib/components/chat/MessageInput.svelte`

**Chat.svelte**:
```javascript
// 준비중 카테고리 확인 reactive statement
$: hasComingSoonCategory = $selectedCategories.some(catId => {
    const category = categories.find(c => c.id === catId);
    return category?.comingSoon === true;
});

// MessageInput에 전달
<MessageInput
    submitDisabled={hasComingSoonCategory}
    ...
/>
```

**MessageInput.svelte**:
```javascript
// submitDisabled prop 추가
export let submitDisabled = false;

// 전송 버튼에 적용
<button
    disabled={submitDisabled || (prompt === '' && files.length === 0)}
    class="{!submitDisabled && !(prompt === '' && files.length === 0)
        ? 'text-gray-900 dark:text-white'
        : 'text-gray-400 dark:text-gray-600'}"
>
```

### 2.2 외부정보검색 카드 제거

**파일**: `/src/lib/components/chat/Chat.svelte`

**삭제된 내용**:
1. 카테고리 정의 (417-424번 라인 삭제)
2. 외부모델 섹션 UI (3787-3861번 라인 삭제)

---

## 3. EDM 다운로드 프로세스

### 3.1 프로세스 개요

```
[사용자 요청] → [EDM Download Pipeline] → [N8N Webhook] → [파일 다운로드]
    → [로컬 저장] → [Open WebUI 업로드] → [자동 벡터화]
```

### 3.2 파이프라인 파일

**파일 위치**: `/pipelines/edm_download_pipe.py`

**주요 클래스**:
```python
class Pipeline:
    class Valves(BaseModel):
        # N8N 웹훅 URL
        n8n_download_url: str = "http://192.168.122.177:5678/webhook/edm-download"

        # 다운로드 디렉토리
        download_base_dir: str = "/tmp/upload"

        # Open WebUI API
        openwebui_api_base: str = "http://localhost:8080/api/v1"

        # 지식베이스 ID (선택)
        knowledge_base_id: Optional[str] = None
```

### 3.3 다운로드 프로세스 상세

#### 3.3.1 다운로드 폴더 생성

**메서드**: `_create_download_folder()`

```python
def _create_download_folder(self) -> str:
    """
    /tmp/upload/날짜+랜덤폴더 생성

    Returns:
        /tmp/upload/20251111_a3f2b1c4
    """
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = str(uuid.uuid4())[:8]
    folder_name = f"{date_str}_{random_str}"
    folder_path = os.path.join(self.valves.download_base_dir, folder_name)

    os.makedirs(folder_path, exist_ok=True)
    return folder_path
```

**폴더 구조 예시**:
```
/tmp/upload/
├── 20251111_a3f2b1c4/
│   ├── 회사생활가이드.pdf
│   ├── IT_Help_Desk_매뉴얼.docx
│   └── 디스플레이_용어사전.xlsx
└── 20251111_f8e9d2a1/
    └── 보안_정책.pdf
```

#### 3.3.2 N8N 웹훅 호출

**메서드**: `_download_edm_file()`

```python
def _download_edm_file(
    self,
    objid: str,
    file_last_ver_sno: int,
    request_user: str,
    download_folder: str
) -> Dict[str, Any]:
    """N8N 웹훅을 통해 EDM 파일 다운로드"""

    # N8N 웹훅 페이로드
    payload = {
        "objid": objid,
        "fileLastVerSno": file_last_ver_sno,
        "requestUser": request_user
    }

    # N8N 호출
    response = requests.post(
        self.valves.n8n_download_url,
        json=payload,
        timeout=60
    )

    # 파일 저장
    result = response.json()
    file_name = result.get("file_name", f"downloaded_{objid}.pdf")
    file_content = result.get("file_content")  # base64

    file_path = os.path.join(download_folder, file_name)

    import base64
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(file_content))

    return {
        "file_name": file_name,
        "file_path": file_path,
        "success": True
    }
```

**N8N 웹훅 응답 예시**:
```json
{
    "file_name": "회사생활가이드_제1장.pdf",
    "file_content": "JVBERi0xLjQKJeLjz9MK...",  // base64
    "objid": "176126817626004568",
    "file_size": 2621440,
    "success": true
}
```

### 3.4 Open WebUI 업로드

**메서드**: `_upload_to_openwebui()`

```python
def _upload_to_openwebui(
    self,
    file_path: str,
    file_name: str,
    token: str,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """Open WebUI 백엔드 표준 API로 파일 업로드"""

    # multipart/form-data 업로드
    with open(file_path, 'rb') as f:
        files = {
            'file': (file_name, f, self._get_content_type(file_name))
        }

        headers = {
            'Authorization': f'Bearer {token}'
        }

        # Open WebUI 파일 업로드 API
        upload_url = f"{self.valves.openwebui_api_base}/files/"

        response = requests.post(
            upload_url,
            files=files,
            headers=headers,
            params={
                'process': 'true',  # 파일 처리 활성화
                'process_in_background': 'true'  # 백그라운드 처리
            },
            timeout=300
        )

        result = response.json()
        file_id = result.get('id')

        return {
            "file_id": file_id,
            "success": True
        }
```

**API 엔드포인트**: `POST /api/v1/files/`

**파라미터**:
- `process=true`: 파일 자동 처리 (파싱, 청킹, 임베딩, 벡터화)
- `process_in_background=true`: 백그라운드 처리 (응답 속도 향상)

### 3.5 전체 프로세스 흐름

**메서드**: `async def pipe(body: dict)`

```python
async def pipe(self, body: dict):
    """
    입력 body:
    {
        "files": [
            {
                "objid": "176126817626004568",
                "fileLastVerSno": 1,
                "requestUser": "user@example.com"
            }
        ],
        "user_token": "Bearer xxx"
    }
    """

    # 1. 다운로드 폴더 생성
    download_folder = self._create_download_folder()
    # → /tmp/upload/20251111_a3f2b1c4

    processed_files = []

    # 2. 각 파일 처리
    for file_info in files:
        # 2-1. EDM에서 파일 다운로드
        download_result = self._download_edm_file(
            objid=file_info["objid"],
            file_last_ver_sno=file_info["fileLastVerSno"],
            request_user=file_info["requestUser"],
            download_folder=download_folder
        )
        # → /tmp/upload/20251111_a3f2b1c4/회사생활가이드.pdf

        # 2-2. Open WebUI에 업로드
        upload_result = self._upload_to_openwebui(
            file_path=download_result["file_path"],
            file_name=download_result["file_name"],
            token=user_token
        )
        # → file_id: "uuid-1234-5678"

        # 2-3. 지식베이스에 추가 (선택)
        if self.valves.knowledge_base_id:
            self._add_to_knowledge_base(
                file_id=upload_result["file_id"],
                knowledge_base_id=self.valves.knowledge_base_id,
                token=user_token
            )

        processed_files.append({
            "objid": file_info["objid"],
            "file_name": download_result["file_name"],
            "file_id": upload_result["file_id"],
            "success": True
        })

    return {
        "success": True,
        "processed_files": processed_files,
        "download_folder": download_folder
    }
```

---

## 4. 벡터라이징 프로세스

### 4.1 Open WebUI 백엔드 자동 처리

**핵심**: EDM 파이프라인은 파일 업로드만 수행하며, 벡터라이징은 **Open WebUI 백엔드가 자동으로 처리**합니다.

### 4.2 백엔드 처리 과정

```
[파일 업로드]
    ↓
[파일 타입 감지] (PDF, DOCX, XLSX, etc.)
    ↓
[문서 파싱] (텍스트 추출)
    ↓
[청킹] (Chunking - 적절한 크기로 분할)
    ↓
[임베딩] (Embedding - 벡터 변환)
    ↓
[벡터 DB 저장] (Milvus/Chroma/etc.)
```

### 4.3 업로드 시 설정

**파라미터**:
```python
params = {
    'process': 'true',  # 파일 처리 활성화
    'process_in_background': 'true'  # 백그라운드 처리
}
```

**백그라운드 처리의 장점**:
- 즉시 응답 반환 (사용자 대기 시간 감소)
- 대용량 파일도 안정적 처리
- 여러 파일 동시 처리 가능

### 4.4 벡터화 설정

**Open WebUI 백엔드 설정 파일**: `/app/backend/open_webui/config.py`

```python
# 임베딩 모델
EMBEDDING_MODEL = "KURE-v1"  # 한국어 최적화

# 청킹 설정
CHUNK_SIZE = 1000  # 청크 크기 (문자 수)
CHUNK_OVERLAP = 200  # 청크 오버랩

# 벡터 DB
VECTOR_DB = "milvus"  # 또는 "chroma"
```

### 4.5 메타데이터 저장

**업로드 시 전달되는 메타데이터**:
```python
metadata = {
    "source": "EDM",
    "objid": "176126817626004568",
    "file_last_ver_sno": 1,
    "request_user": "user@example.com",
    "workspace": "인사총무",
    "category": "회사생활가이드"
}
```

**백엔드 저장 구조**:
```json
{
    "file_id": "uuid-1234-5678",
    "file_name": "회사생활가이드.pdf",
    "chunks": [
        {
            "chunk_id": "chunk-001",
            "content": "1.1 입사 절차 및 준비사항...",
            "vector": [0.123, 0.456, ...],  // 1536 차원
            "metadata": {
                "source": "EDM",
                "objid": "176126817626004568",
                "page": 1,
                "chunk_index": 0
            }
        },
        {
            "chunk_id": "chunk-002",
            "content": "1.2 첫 출근일 안내...",
            "vector": [0.789, 0.012, ...],
            "metadata": {
                "source": "EDM",
                "objid": "176126817626004568",
                "page": 2,
                "chunk_index": 1
            }
        }
    ]
}
```

---

## 5. 채팅 통합 프로세스

### 5.1 EDM 검색 파이프라인

**파일**: `/pipelines/edm_search_pipe.py`

### 5.2 검색 프로세스

```
[사용자 질문] → [카테고리 확인] → [벡터 검색] → [관련 문서 추출]
    → [LLM 프롬프트 생성] → [응답 생성] → [출처 표시]
```

### 5.3 카테고리별 검색

**RightSidebar.svelte에서 카테고리 선택**:
```javascript
export const DISPLAY_CATEGORIES = [
    {
        id: 'edm',
        name: 'EDM 문서활용',
        actualIds: ['edm']
    },
    {
        id: 'daesawoo',
        name: '대사우 Assistant',
        actualIds: ['guide', 'helpdesk', 'dictionary', 'etc']
    }
];
```

**Chat.svelte에서 모델 자동 선택**:
```javascript
// EDM 카테고리 선택 시
if (category.id === 'edm') {
    const edmModel = availableModels.find(m =>
        m.id === 'edm_search_pipe' || m.id?.includes('edm_search')
    );
    selectedModels = [edmModel.id];
}

// 대사우 Assistant 선택 시
if (['guide', 'helpdesk', 'dictionary', 'etc'].includes(category.id)) {
    const daesawooModel = $models.find(m =>
        m.id?.includes('daesawoo') || m.name?.includes('daesawoo')
    );
    selectedModels = [daesawooModel.id];
}
```

### 5.4 검색 파이프라인 처리

**edm_search_pipe.py**:
```python
async def pipe(self, body: dict, __event_emitter__=None):
    """EDM 문서 검색"""

    # 사용자 질문 추출
    messages = body.get("messages", [])
    user_message = messages[-1].get("content", "")

    # 카테고리 추출
    categories = body.get("categories", ["edm"])

    # N8N 웹훅 호출 (벡터 검색)
    n8n_result = self._call_n8n_webhook(
        query=user_message,
        categories=categories
    )

    # 검색 결과
    documents = n8n_result.get("documents", [])

    # LLM 프롬프트 생성
    context = self._build_context(documents)
    prompt = f"""
다음 문서를 참고하여 질문에 답변하세요:

{context}

질문: {user_message}
"""

    # LLM 호출하여 응답 생성
    response = self._call_llm(prompt)

    # 출처 표시
    sources = [
        {
            "title": doc["title"],
            "objid": doc["objid"],
            "score": doc["score"]
        }
        for doc in documents
    ]

    return {
        "response": response,
        "sources": sources
    }
```

### 5.5 사용자 인터페이스 흐름

#### 5.5.1 카테고리 선택

1. 사용자가 오른쪽 사이드바에서 **"EDM 문서활용"** 또는 **"대사우 Assistant"** 라디오 버튼 클릭
2. `selectedCategories` 스토어 업데이트: `['edm']` 또는 `['guide', 'helpdesk', 'dictionary', 'etc']`
3. Chat.svelte의 reactive statement가 자동으로 해당 모델 선택
4. 모델 선택 드롭다운이 자동으로 변경됨

#### 5.5.2 샘플 질문 클릭

```javascript
// EDM 카테고리 샘플 질문
{
    id: 'edm',
    samples: [
        '최근 사용한 문서를 요약해서 보여 줘',
        '지난 분기 생산 효율 회의록 찾아 줘'
    ]
}

// 대사우 Assistant - 지식용어 사전
{
    id: 'dictionary',
    samples: [
        'OLED 용어 설명해 줘',
        '디스플레이 전문용어 찾아 줘'
    ]
}
```

**클릭 시 동작**:
```javascript
on:click={async () => {
    // 카테고리에 맞는 모델 자동 선택
    if (category.id === 'edm') {
        displayCategory = DISPLAY_CATEGORIES[0];
        selectedCategories.set(['edm']);
    } else if (category.id === 'dictionary') {
        displayCategory = DISPLAY_CATEGORIES[1];
        selectedCategories.set(['guide', 'helpdesk', 'dictionary', 'etc']);
    }

    // 입력창에 샘플 질문 자동 입력
    prompt = sample;
    await tick();
    if (messageInput) {
        await messageInput.setText(sample);
    }
}}
```

#### 5.5.3 메시지 전송

1. 사용자가 전송 버튼 클릭 또는 Enter 키 입력
2. `submitPrompt()` 함수 호출
3. 선택된 모델(EDM 또는 대사우)로 메시지 전송
4. 파이프라인이 벡터 검색 수행
5. LLM이 검색 결과를 바탕으로 응답 생성
6. 출처(Sources) 표시

---

## 6. 설정 파일 구조

### 6.1 프로젝트 폴더 구조

```
/home/chatpro/open-webui-main/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── Chat.svelte                    # 메인 채팅 컴포넌트
│   │   │   │   ├── MessageInput.svelte            # 메시지 입력 컴포넌트
│   │   │   │   └── ModelSelector.svelte           # 모델 선택 컴포넌트
│   │   │   └── layout/
│   │   │       └── RightSidebar.svelte            # 카테고리 선택 사이드바
│   │   ├── apis/
│   │   │   ├── edm.ts                             # EDM API 클라이언트
│   │   │   └── edm-download.ts                    # EDM 다운로드 API
│   │   └── stores/
│   │       └── index.ts                           # Svelte 스토어 정의
│   └── routes/
├── pipelines/
│   ├── edm_download_pipe.py                       # EDM 다운로드 파이프라인
│   ├── edm_search_pipe.py                         # EDM 검색 파이프라인
│   ├── edm_embedding_pipe.py                      # EDM 임베딩 파이프라인
│   └── daesawoo.py                                # 대사우 Assistant 파이프라인
├── backend/
│   └── (Open WebUI 백엔드 - 표준 파일 처리)
└── .env                                           # 환경 변수
```

### 6.2 환경 변수 설정

**파일**: `.env`

```bash
# Open WebUI 백엔드
WEBUI_URL=http://localhost:8080
OPENWEBUI_API_BASE=http://localhost:8080/api/v1

# N8N 워크플로우
N8N_BASE_URL=http://192.168.122.177:5678
N8N_DOWNLOAD_WEBHOOK=/webhook/edm-download
N8N_SEARCH_WEBHOOK=/webhook/edm-search

# EDM 다운로드 디렉토리
DOWNLOAD_BASE_DIR=/tmp/upload

# 임베딩 모델
EMBEDDING_MODEL=KURE-v1

# 벡터 DB
VECTOR_DB=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 지식베이스 (선택)
KNOWLEDGE_BASE_ID=your-kb-id-here
```

### 6.3 파이프라인 설정 (Valves)

**EDM Download Pipeline** (`edm_download_pipe.py`):
```python
class Valves(BaseModel):
    priority: int = 0

    # N8N 웹훅 URL
    n8n_download_url: str = "http://192.168.122.177:5678/webhook/edm-download"

    # 다운로드 설정
    download_base_dir: str = "/tmp/upload"

    # Open WebUI 백엔드 API
    openwebui_api_base: str = "http://localhost:8080/api/v1"

    # 지식베이스 ID (선택)
    knowledge_base_id: Optional[str] = None

    # 업로드 모드
    upload_mode: str = "individual"  # 'individual' or 'folder'

    enable_debug: bool = True
```

**EDM Search Pipeline** (`edm_search_pipe.py`):
```python
class Valves(BaseModel):
    pipelines: List[str] = []
    priority: int = 0

    # N8N 워크플로우 설정
    n8n_base_url: str = "http://192.168.122.177:5678"
    n8n_webhook_path: str = "/webhook/edm-search"

    # EDM 검색 설정
    default_categories: List[str] = ["edm"]
    max_results: int = 50

    enable_debug: bool = True
```

### 6.4 Svelte 스토어 설정

**파일**: `/src/lib/stores/index.ts`

```typescript
import { writable } from 'svelte/store';

// 모델 타입 ('internal' | 'external')
export const modelType = writable<string>('internal');

// 선택된 카테고리
export const selectedCategories = writable<string[]>([]);

// 오른쪽 사이드바 표시 여부
export const showRightSidebar = writable<boolean>(true);

// 사용 가능한 모델 목록
export const models = writable<any[]>([]);
```

### 6.5 카테고리 매핑 설정

**RightSidebar.svelte**:
```javascript
export const DISPLAY_CATEGORIES = [
    {
        id: 'edm',
        name: 'EDM 문서활용',
        color: 'bg-blue-500',
        description: '전자문서관리 시스템',
        actualIds: ['edm']  // 실제 카테고리 ID
    },
    {
        id: 'daesawoo',
        name: '대사우 Assistant',
        color: 'bg-green-500',
        description: '회사생활가이드, IT Help Desk, 용어사전 등',
        actualIds: ['guide', 'helpdesk', 'dictionary', 'etc']
    }
];
```

**Chat.svelte**:
```javascript
const categories = [
    // 기본 카테고리
    { id: 'report', name: '보고서 초안 작성' },
    { id: 'code', name: 'Code 개발 지원' },

    // EDM 카테고리
    {
        id: 'edm',
        name: 'EDM 문서활용',
        collection_name: 'edm-knowledge'
    },

    // 대사우 Assistant 카테고리
    {
        id: 'dictionary',
        name: '대사우 Assistant [지식용어 사전]',
        samples: [
            'OLED 용어 설명해 줘',
            '디스플레이 전문용어 찾아 줘'
        ]
    },
    {
        id: 'guide',
        name: '대사우 Assistant [사규]',
        comingSoon: true  // 준비중
    },
    {
        id: 'helpdesk',
        name: '대사우 Assistant [IT Help Desk]',
        comingSoon: true  // 준비중
    }
];
```

---

## 7. 프로세스 흐름도

### 7.1 전체 아키텍처

```
┌─────────────────┐
│   사용자 UI     │
│  (Chat.svelte)  │
└────────┬────────┘
         │
         │ 1. 카테고리 선택 (EDM / 대사우)
         ↓
┌─────────────────┐
│  RightSidebar   │
│ selectedCategories │
│   ['edm']       │
└────────┬────────┘
         │
         │ 2. 모델 자동 선택
         ↓
┌─────────────────┐
│  ModelSelector  │
│ edm_search_pipe │
└────────┬────────┘
         │
         │ 3. 메시지 전송
         ↓
┌─────────────────┐
│ EDM Search      │
│   Pipeline      │
└────────┬────────┘
         │
         │ 4. 벡터 검색
         ↓
┌─────────────────┐
│  Vector DB      │
│   (Milvus)      │
└────────┬────────┘
         │
         │ 5. 관련 문서 추출
         ↓
┌─────────────────┐
│      LLM        │
│  (응답 생성)    │
└────────┬────────┘
         │
         │ 6. 응답 + 출처
         ↓
┌─────────────────┐
│   사용자 UI     │
│  (응답 표시)    │
└─────────────────┘
```

### 7.2 EDM 파일 다운로드 흐름

```
[사용자 요청]
    ↓
[EDM Download Pipeline 호출]
    │
    ├─ [1. 다운로드 폴더 생성]
    │   → /tmp/upload/20251111_a3f2b1c4/
    │
    ├─ [2. N8N Webhook 호출]
    │   │
    │   ├─ Payload: { objid, fileLastVerSno, requestUser }
    │   ↓
    │   [N8N Workflow]
    │   │
    │   ├─ EDM API 호출
    │   ├─ 파일 다운로드
    │   ├─ Base64 인코딩
    │   ↓
    │   Response: { file_name, file_content }
    │
    ├─ [3. 로컬 저장]
    │   → /tmp/upload/20251111_a3f2b1c4/회사생활가이드.pdf
    │
    ├─ [4. Open WebUI 업로드]
    │   │
    │   ├─ POST /api/v1/files/
    │   ├─ params: { process: true, process_in_background: true }
    │   ↓
    │   [Open WebUI Backend]
    │   │
    │   ├─ 파일 타입 감지 (PDF/DOCX/XLSX)
    │   ├─ 문서 파싱 (텍스트 추출)
    │   ├─ 청킹 (1000자 단위)
    │   ├─ 임베딩 (KURE-v1 모델)
    │   ├─ 벡터 DB 저장 (Milvus)
    │   ↓
    │   Response: { file_id }
    │
    ├─ [5. 지식베이스 추가 (선택)]
    │   → POST /api/v1/knowledge/{kb_id}/file/add
    │
    └─ [6. 완료]
        → { success: true, file_id, file_path }
```

### 7.3 벡터 검색 흐름

```
[사용자 질문: "OLED 용어 설명해 줘"]
    ↓
[1. 카테고리 확인]
    → selectedCategories: ['guide', 'helpdesk', 'dictionary', 'etc']
    ↓
[2. 모델 선택]
    → daesawoo 파이프라인
    ↓
[3. 질문 임베딩]
    → KURE-v1: [0.123, 0.456, 0.789, ...]
    ↓
[4. 벡터 검색]
    │
    ├─ Milvus 쿼리
    ├─ 유사도 계산 (Cosine Similarity)
    ├─ Top-K 추출 (예: 상위 5개)
    ↓
    결과: [
        { chunk_id: "chunk-001", score: 0.95, content: "OLED는..." },
        { chunk_id: "chunk-023", score: 0.88, content: "유기발광다이오드..." },
        { chunk_id: "chunk-045", score: 0.82, content: "디스플레이 패널..." }
    ]
    ↓
[5. 컨텍스트 구성]
    → context = "문서1: OLED는...\n문서2: 유기발광다이오드...\n문서3: 디스플레이 패널..."
    ↓
[6. LLM 프롬프트]
    prompt = f"""
다음 문서를 참고하여 질문에 답변하세요:

{context}

질문: OLED 용어 설명해 줘
"""
    ↓
[7. LLM 응답 생성]
    → "OLED(Organic Light Emitting Diode)는 유기발광다이오드로,
       전기를 통해 스스로 빛을 내는 자발광 소자입니다.
       LCD와 달리 백라이트가 필요 없어 더 얇고 가볍습니다..."
    ↓
[8. 출처 표시]
    sources: [
        { title: "디스플레이 용어사전", objid: "edm-obj-002", score: 0.95 },
        { title: "OLED 기술 가이드", objid: "edm-obj-145", score: 0.88 }
    ]
    ↓
[9. 사용자에게 응답]
```

---

## 8. 문제 해결

### 8.1 일반적인 문제

#### 문제 1: 다운로드 폴더 권한 오류

**증상**:
```
PermissionError: [Errno 13] Permission denied: '/tmp/upload'
```

**해결**:
```bash
# 폴더 권한 확인 및 수정
sudo chmod 755 /tmp/upload
sudo chown chatpro:chatpro /tmp/upload
```

**Valves 설정 수정**:
```python
download_base_dir: str = "/home/chatpro/edm-downloads"
```

#### 문제 2: N8N 웹훅 타임아웃

**증상**:
```
requests.exceptions.Timeout: HTTPConnectionPool(host='192.168.122.177', port=5678): Read timed out.
```

**해결**:
```python
# edm_download_pipe.py Valves 수정
class Valves(BaseModel):
    # N8N 웹훅 타임아웃 증가
    n8n_timeout: int = 120  # 60초 → 120초
```

**코드 수정**:
```python
response = requests.post(
    self.valves.n8n_download_url,
    json=payload,
    timeout=self.valves.n8n_timeout  # 동적 타임아웃
)
```

#### 문제 3: Open WebUI 업로드 실패

**증상**:
```
401 Unauthorized: Invalid token
```

**원인**: user_token이 누락되거나 만료됨

**해결**:
1. 프론트엔드에서 토큰 확인:
```javascript
const token = localStorage.getItem('token');
console.log('Token:', token);
```

2. 토큰 갱신:
```javascript
// 로그인 재시도
await login(username, password);
```

3. Valves에서 토큰 하드코딩 (테스트용):
```python
# 주의: 프로덕션에서는 절대 사용 금지!
user_token_override: Optional[str] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 문제 4: 벡터화가 안됨

**증상**: 파일은 업로드되었으나 검색 시 결과 없음

**확인 사항**:
1. 업로드 시 `process=true` 파라미터 확인
2. 백엔드 로그 확인:
```bash
podman logs sdc-open-webui | grep "Processing file"
```

3. 벡터 DB 연결 확인:
```bash
# Milvus 상태 확인
curl http://localhost:19530/health
```

**해결**:
```python
# 업로드 파라미터 명시적 지정
params = {
    'process': 'true',
    'process_in_background': 'true'
}

response = requests.post(
    upload_url,
    files=files,
    headers=headers,
    params=params,  # 명시적으로 전달
    timeout=300
)
```

### 8.2 디버깅 방법

#### 로그 확인

**EDM Download Pipeline**:
```python
# edm_download_pipe.py에서 enable_debug=True 설정
class Valves(BaseModel):
    enable_debug: bool = True
```

**실행 로그**:
```bash
# 파이프라인 로그 확인
podman logs sdc-open-webui | grep "EDM Download"
```

**예시 로그**:
```
[EDM Download] ================================================================================
[EDM Download] 📋 [FUNCTION] edm_download_pipe
[EDM Download] 📋 [MODE] EDM 파일 다운로드 및 업로드
[EDM Download] 📋 처리할 파일 수: 3개
[EDM Download] 📁 다운로드 폴더 생성: /tmp/upload/20251111_a3f2b1c4
[EDM Download] --- 파일 1/3 처리 시작 ---
[EDM Download] 📋 OBJID: 176126817626004568
[EDM Download] 📥 N8N 다운로드 요청: {"objid": "176126817626004568", ...}
[EDM Download] ✅ 파일 다운로드 완료: /tmp/upload/20251111_a3f2b1c4/회사생활가이드.pdf
[EDM Download] 📤 Open WebUI 업로드 시작: 회사생활가이드.pdf
[EDM Download] ✅ Open WebUI 업로드 완료: file_id=uuid-1234-5678
[EDM Download] 🔄 백엔드에서 자동으로 파싱/청킹/임베딩/벡터화 진행 중...
[EDM Download] ✅ 파일 1 처리 완료
[EDM Download] ================================================================================
[EDM Download] ✨ 처리 완료: 성공 3개, 실패 0개
[EDM Download] 📁 다운로드 폴더: /tmp/upload/20251111_a3f2b1c4
[EDM Download] ================================================================================
```

#### 수동 테스트

**1. N8N 웹훅 테스트**:
```bash
curl -X POST http://192.168.122.177:5678/webhook/edm-download \
  -H "Content-Type: application/json" \
  -d '{
    "objid": "176126817626004568",
    "fileLastVerSno": 1,
    "requestUser": "test@example.com"
  }'
```

**2. Open WebUI 업로드 테스트**:
```bash
TOKEN="your-token-here"

curl -X POST http://localhost:8080/api/v1/files/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/upload/test.pdf" \
  -F "process=true" \
  -F "process_in_background=true"
```

**3. 벡터 검색 테스트**:
```bash
curl -X POST http://localhost:8080/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "OLED 용어 설명",
    "collection_name": "edm-knowledge",
    "limit": 5
  }'
```

### 8.3 성능 최적화

#### 다운로드 최적화

**병렬 다운로드**:
```python
import asyncio

async def _download_files_parallel(self, files: List[dict], folder: str):
    """여러 파일을 병렬로 다운로드"""
    tasks = [
        self._download_edm_file_async(
            objid=file["objid"],
            file_last_ver_sno=file["fileLastVerSno"],
            request_user=file["requestUser"],
            download_folder=folder
        )
        for file in files
    ]

    results = await asyncio.gather(*tasks)
    return results
```

**사용 예시**:
```python
# 순차 처리 (느림)
for file_info in files:
    download_result = self._download_edm_file(...)

# 병렬 처리 (빠름)
download_results = await self._download_files_parallel(files, folder)
```

#### 청킹 최적화

**적절한 청크 크기 설정**:
```python
# 백엔드 설정
CHUNK_SIZE = 1000  # 기본값
CHUNK_OVERLAP = 200  # 20% 오버랩

# 문서 타입별 최적화
chunk_configs = {
    "pdf": {"size": 1000, "overlap": 200},
    "docx": {"size": 800, "overlap": 160},
    "xlsx": {"size": 500, "overlap": 100}
}
```

#### 벡터 검색 최적화

**인덱스 설정** (Milvus):
```python
# IVF_FLAT 인덱스 (정확도 우선)
index_params = {
    "metric_type": "L2",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 1024}
}

# HNSW 인덱스 (속도 우선)
index_params = {
    "metric_type": "L2",
    "index_type": "HNSW",
    "params": {
        "M": 16,
        "efConstruction": 200
    }
}
```

---

## 9. 요약

### 9.1 핵심 포인트

1. **EDM 다운로드**: N8N 웹훅 → 로컬 저장 → Open WebUI 업로드
2. **자동 벡터화**: Open WebUI 백엔드가 파일 처리 전담
3. **카테고리 관리**: RightSidebar 라디오 버튼으로 단일 선택
4. **모델 자동 선택**: 카테고리 선택 시 자동으로 적합한 모델 선택
5. **준비중 상태**: comingSoon 플래그로 비활성화 처리

### 9.2 설정 체크리스트

- [ ] N8N 웹훅 URL 설정 (`edm_download_pipe.py`)
- [ ] 다운로드 디렉토리 권한 확인 (`/tmp/upload`)
- [ ] Open WebUI API URL 설정
- [ ] 임베딩 모델 설정 (KURE-v1)
- [ ] 벡터 DB 연결 확인 (Milvus)
- [ ] 카테고리 매핑 확인 (`RightSidebar.svelte`)
- [ ] 모델 필터링 확인 (내부 모델만)
- [ ] 준비중 카테고리 설정 (`comingSoon: true`)

### 9.3 다음 단계

1. **준비중 카테고리 활성화**: 사규, IT Help Desk 기능 개발
2. **N8N 워크플로우 개선**: 에러 핸들링, 재시도 로직
3. **성능 모니터링**: 다운로드/업로드 시간 측정
4. **사용자 피드백**: 검색 정확도 개선

---

**문서 작성자**: Claude Code
**마지막 업데이트**: 2025-11-11
**버전**: 3.1
