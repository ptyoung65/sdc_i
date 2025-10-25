# External LLM MCP Server

Open WebUI에서 외부 LLM (ChatGPT, Perplexity)을 MCP 프로토콜로 호출하는 서버입니다.

## 🎯 개요

이 MCP 서버는 Open WebUI와 외부 LLM API 사이의 **통신 채널** 역할을 합니다.

### 데이터 플로우

```
Open WebUI
  ↓ (외부검색 클릭 → 챗 입력)
MCP Server (Port 8100)
  ↓ (외부 LLM API 호출)
  ├→ ChatGPT API (OpenAI)
  └→ Perplexity API (웹 검색)
  ↓ (응답 수신)
MCP Server
  ↓ (응답 포맷팅)
Open WebUI (답변 표시)
```

## 🚀 빠른 시작

### 1. 서버 시작

```bash
cd /home/chatpro/open-webui-main/mcp-external-llm-server

# 백그라운드로 시작 (권장)
./start_server.sh --background

# 또는 포그라운드로 시작 (디버깅용)
./start_server.sh
```

### 2. 서버 상태 확인

```bash
# 헬스 체크
curl http://localhost:8100/health

# 출력:
# {
#   "status": "healthy",
#   "server": "External LLM MCP Server",
#   "supported_llms": ["ChatGPT", "Perplexity"],
#   "api_keys_configured": {
#     "openai": true,
#     "perplexity": false
#   }
# }
```

### 3. Open WebUI에 등록

**웹 UI에서 등록:**

1. http://localhost:3000 접속
2. **Settings** → **Workspace** → **Tools** → **Tool Servers**
3. "Add" 클릭 후 다음 입력:

```
Server URL: http://host.containers.internal:8100/mcp
Server Type: mcp
Authentication: none
Name: External LLM Server
Description: ChatGPT, Perplexity 외부 LLM 호출
```

4. **Verify** → **Save**

## 🛠 제공 도구

### 1. query_chatgpt

ChatGPT API를 호출하여 질문에 답변합니다.

**파라미터:**
```json
{
  "model": "gpt-3.5-turbo",           // 모델 선택 (gpt-4, gpt-3.5-turbo)
  "api_key": "sk-...",                // OpenAI API 키 (선택적)
  "user_info": "username",            // 사용자 정보 (선택적)
  "question": "파이썬이란?",           // 질문 (필수)
  "temperature": 0.7,                 // 창의성 (0.0~2.0)
  "max_tokens": 1000                  // 최대 토큰 수
}
```

**Open WebUI 사용 예시:**
```
사용자: ChatGPT를 통해 "인공지능의 미래"에 대해 알려줘

AI: (query_chatgpt 도구 호출)
→ ChatGPT 응답 (gpt-3.5-turbo)

인공지능의 미래는 매우 밝습니다...

---
토큰 사용: {'prompt_tokens': 12, 'completion_tokens': 245}
```

### 2. query_perplexity

Perplexity API를 호출하여 웹 검색 기반 답변을 받습니다.

**파라미터:**
```json
{
  "model": "pplx-7b-online",          // 모델 선택
  "api_key": "pplx-...",              // Perplexity API 키 (선택적)
  "user_info": "username",            // 사용자 정보 (선택적)
  "question": "최신 AI 뉴스는?",       // 질문 (필수)
  "search_domain_filter": ["..."]     // 도메인 필터 (선택적)
}
```

**Open WebUI 사용 예시:**
```
사용자: Perplexity로 "2025년 AI 트렌드" 검색해줘

AI: (query_perplexity 도구 호출)
→ Perplexity 응답 (pplx-7b-online)

2025년 AI 트렌드는...

**출처:**
- https://example.com/ai-trends
- https://techcrunch.com/ai-2025
```

### 3. get_llm_status

외부 LLM API 연결 상태를 확인합니다.

**파라미터:** (없음)

**응답:**
```json
{
  "openai_api_configured": true,
  "perplexity_api_configured": false,
  "server_status": "running",
  "supported_models": {
    "chatgpt": ["gpt-4", "gpt-3.5-turbo"],
    "perplexity": ["pplx-7b-online", "pplx-70b-online"]
  }
}
```

## 🔑 API 키 설정

### 방법 1: 환경 변수 (권장)

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
vi .env
```

`.env` 내용:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
PERPLEXITY_API_KEY=pplx-your-perplexity-api-key-here
```

### 방법 2: 도구 호출 시 전달

Open WebUI에서 도구 사용 시 `api_key` 파라미터로 직접 전달:

```json
{
  "question": "질문",
  "api_key": "sk-your-api-key"
}
```

## 📊 전송 데이터

MCP 서버가 외부 LLM API에 전송하는 데이터:

| 데이터 | 설명 | 필수 여부 |
|--------|------|-----------|
| **model** | LLM 모델명 | 선택 (기본값 사용) |
| **api_key** | API 인증 키 | 필수 (환경변수/파라미터) |
| **user_info** | 사용자 정보 | 선택 |
| **question** | 질문 내용 | 필수 |
| **temperature** | 응답 창의성 | 선택 (ChatGPT) |
| **max_tokens** | 최대 토큰 수 | 선택 (ChatGPT) |
| **search_domain_filter** | 검색 필터 | 선택 (Perplexity) |

## 🔧 관리

### 서버 상태 확인

```bash
# 프로세스 확인
ps aux | grep external_llm_mcp_server

# 로그 확인
tail -f /tmp/external-llm-mcp.log

# 헬스 체크
curl http://localhost:8100/health
```

### 서버 중지

```bash
# PID로 중지
kill $(cat /home/chatpro/open-webui-main/mcp-external-llm-server/server.pid)

# 또는 포트로 중지
lsof -ti:8100 | xargs kill -9
```

### 서버 재시작

```bash
# 중지
lsof -ti:8100 | xargs kill -9

# 시작
cd /home/chatpro/open-webui-main/mcp-external-llm-server
./start_server.sh --background
```

## 🧪 테스트

### MCP 프로토콜 테스트

**1. Tools List:**
```bash
curl -X POST http://localhost:8100/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

**2. ChatGPT 호출 (API 키 필요):**
```bash
curl -X POST http://localhost:8100/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "query_chatgpt",
      "arguments": {
        "question": "안녕하세요",
        "api_key": "sk-your-api-key"
      }
    }
  }'
```

**3. 상태 확인:**
```bash
curl -X POST http://localhost:8100/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "get_llm_status",
      "arguments": {}
    }
  }'
```

## 🚨 문제 해결

### API 키 오류
```
Error: OpenAI API 키가 설정되지 않았습니다
```

**해결:** `.env` 파일에 API 키 설정 또는 파라미터로 전달

### 연결 실패
```
Error: Failed to connect to api.openai.com
```

**해결:**
1. 네트워크 연결 확인
2. API 키 유효성 확인
3. 방화벽 설정 확인

### 타임아웃
```
Error: API 요청 타임아웃 (60초)
```

**해결:** LLM API 서버 상태 확인 (OpenAI/Perplexity 장애 여부)

## 📖 사용 시나리오

### 시나리오 1: Open WebUI에서 ChatGPT 사용

1. Open WebUI 채팅에서 입력:
   ```
   "인공지능의 역사를 ChatGPT를 통해 알려줘"
   ```

2. AI가 `query_chatgpt` 도구 사용:
   ```json
   {
     "question": "인공지능의 역사",
     "model": "gpt-3.5-turbo"
   }
   ```

3. MCP 서버 → ChatGPT API 호출 → 응답 반환

4. Open WebUI에 ChatGPT 응답 표시

### 시나리오 2: Perplexity 웹 검색

1. 채팅 입력:
   ```
   "Perplexity로 최신 AI 뉴스 검색해줘"
   ```

2. AI가 `query_perplexity` 도구 사용

3. MCP 서버 → Perplexity API (웹 검색) → 응답 + 출처 반환

4. Open WebUI에 검색 결과 및 출처 표시

## 🏗 아키텍처

```
┌────────────────────────────────────┐
│     Open WebUI (Podman)            │
│       Port: 3000                   │
│                                    │
│  ┌──────────────────────────────┐ │
│  │   MCP Client                 │ │
│  │   (utils/mcp/client.py)      │ │
│  └────────┬─────────────────────┘ │
└───────────┼────────────────────────┘
            │ MCP Protocol
            ▼
┌────────────────────────────────────┐
│  External LLM MCP Server (Host)    │
│       Port: 8100                   │
│                                    │
│  Tools:                            │
│  - query_chatgpt                   │
│  - query_perplexity                │
│  - get_llm_status                  │
│                                    │
│  ┌──────────┐    ┌──────────────┐ │
│  │ ChatGPT  │    │ Perplexity   │ │
│  │ Handler  │    │ Handler      │ │
│  └────┬─────┘    └─────┬────────┘ │
└───────┼────────────────┼───────────┘
        │                │
        ▼                ▼
┌────────────────┐  ┌────────────────┐
│ OpenAI API     │  │ Perplexity API │
│ api.openai.com │  │ api.perplexity.│
└────────────────┘  └────────────────┘
```

## 📚 참고 자료

- **MCP 공식 문서**: https://modelcontextprotocol.io
- **OpenAI API**: https://platform.openai.com/docs/api-reference
- **Perplexity API**: https://docs.perplexity.ai

## 📝 라이선스

Open WebUI 프로젝트와 동일

---

**최종 업데이트**: 2025-10-25
**버전**: 1.0.0
**포트**: 8100
