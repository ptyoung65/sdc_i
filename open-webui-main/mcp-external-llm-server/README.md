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

## 🐳 Docker/Podman 컨테이너 실행

### 이미지 로드

```bash
# SSL 버전
docker load -i perplexity-mcp-server-3.0.tar

# No-SSL 버전 (경량)
docker load -i no-ssl/perplexity-mcp-server-3.0-nossl.tar
```

### HTTP 모드 (No-SSL)

```bash
docker run -d --name perplexity-mcp-nossl \
  -p 8200:8200 \
  -e PERPLEXITY_API_KEY="your-api-key" \
  perplexity-mcp-server:3.0-nossl
```

### HTTPS 모드 (SSL 인증서 볼륨 마운트)

#### PEM 파일 유형별 설정

**1. server.pem (인증서 + 개인키 통합)**

```bash
docker run -d --name perplexity-mcp-ssl \
  -p 8200:8200 \
  -e PERPLEXITY_API_KEY="your-api-key" \
  -e SSL_ENABLED="true" \
  -e SSL_CERT_FILE="/app/ssl/server.pem" \
  -e SSL_KEY_FILE="/app/ssl/server.pem" \
  -v /etc/ssl/mcpstore/server.pem:/app/ssl/server.pem:ro \
  -v /etc/ssl/download:/app/download:rw \
  perplexity-mcp-server:3.0
```

**2. cert.pem + key.pem (분리형)**

```bash
docker run -d --name perplexity-mcp-ssl \
  -p 8200:8200 \
  -e PERPLEXITY_API_KEY="your-api-key" \
  -e SSL_ENABLED="true" \
  -e SSL_CERT_FILE="/app/ssl/cert.pem" \
  -e SSL_KEY_FILE="/app/ssl/key.pem" \
  -v /etc/ssl/mcpstore/cert.pem:/app/ssl/cert.pem:ro \
  -v /etc/ssl/mcpstore/key.pem:/app/ssl/key.pem:ro \
  -v /etc/ssl/download:/app/download:rw \
  perplexity-mcp-server:3.0
```

**3. fullchain.pem + privkey.pem (Let's Encrypt 스타일)**

```bash
docker run -d --name perplexity-mcp-ssl \
  -p 8200:8200 \
  -e PERPLEXITY_API_KEY="your-api-key" \
  -e SSL_ENABLED="true" \
  -e SSL_CERT_FILE="/app/ssl/fullchain.pem" \
  -e SSL_KEY_FILE="/app/ssl/privkey.pem" \
  -v /etc/ssl/mcpstore/fullchain.pem:/app/ssl/fullchain.pem:ro \
  -v /etc/ssl/mcpstore/privkey.pem:/app/ssl/privkey.pem:ro \
  -v /etc/ssl/download:/app/download:rw \
  perplexity-mcp-server:3.0
```

### PEM 파일 구조 참고

| 파일명 | 내용 | 용도 |
|--------|------|------|
| `server.pem` | 인증서 + 개인키 통합 | SSL_CERT_FILE, SSL_KEY_FILE 동일 |
| `cert.pem` | 인증서만 | SSL_CERT_FILE |
| `key.pem` / `privkey.pem` | 개인키만 | SSL_KEY_FILE |
| `fullchain.pem` | 인증서 + 중간 인증서 체인 | SSL_CERT_FILE |

### PEM 파일 내용 확인

```bash
# 인증서 정보 확인
openssl x509 -in /etc/ssl/mcpstore/cert.pem -text -noout

# 개인키 포함 여부 확인
grep -c "PRIVATE KEY" /etc/ssl/mcpstore/server.pem
# 결과가 1이면 개인키 포함
```

### 환경 변수 목록

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `PERPLEXITY_API_KEY` | ✅ | - | Perplexity API 키 |
| `SSL_ENABLED` | ❌ | false | HTTPS 활성화 |
| `SSL_CERT_FILE` | SSL시 | /app/ssl/server.crt | 인증서 파일 경로 |
| `SSL_KEY_FILE` | SSL시 | /app/ssl/server.key | 개인키 파일 경로 |
| `SSL_KEY_PASSWORD` | ❌ | (빈값) | 개인키 비밀번호 (암호화된 키 파일용) |
| `MCP_SERVER_PORT` | ❌ | 8200 | 서버 포트 |

### 컨테이너 관리

```bash
# Bash 접속
docker exec -it perplexity-mcp-ssl bash

# 인증서 확인
docker exec perplexity-mcp-ssl ls -la /app/ssl/

# 로그 확인
docker logs -f perplexity-mcp-ssl

# 헬스 체크 (HTTPS)
curl -k https://localhost:8200/health

# 헬스 체크 (HTTP)
curl http://localhost:8200/health

# 컨테이너 중지/삭제
docker stop perplexity-mcp-ssl && docker rm perplexity-mcp-ssl
```

### 볼륨 마운트 경로

| 호스트 경로 | 컨테이너 경로 | 용도 |
|------------|--------------|------|
| `/etc/ssl/mcpstore/*.pem` | `/app/ssl/*.pem` | SSL 인증서 |
| `/etc/ssl/download` | `/app/download` | 다운로드 폴더 |

## 🔐 SSL 인증서 설정 가이드 (발급된 PEM 인증서 사용)

이미 발급된 PEM 인증서를 MCP 서버와 Dify 서버에 적용하는 방법입니다.

### 📋 전체 작업 순서 요약

```
[사전 준비] ─────────────────────────────────────────────────────────────
  │
  └─ 발급된 인증서 파일 준비: cert.pem (인증서), key.pem (개인키)
          │
          ▼
[MCP 서버] ──────────────────────────────────────────────────────────────
  │
  ├─ Step 1. 인증서 파일 배치
  ├─ Step 2. 인증서 검증
  ├─ Step 3. MCP 컨테이너 실행 (볼륨 마운트)
  └─ Step 4. HTTPS 연결 테스트
          │
          ▼
[Dify 서버] ─────────────────────────────────────────────────────────────
  │
  ├─ Step 5. 인증서 복사 (MCP → Dify)
  ├─ Step 6. Dify 컨테이너 설정 (환경변수 + 볼륨 마운트)
  ├─ Step 7. Dify HTTP Request 노드 설정
  └─ Step 8. 연결 테스트
```

---

## 📁 사전 준비: 인증서 파일 확인

### 인증서 파일 종류

| 파일 | 설명 | 용도 |
|------|------|------|
| `cert.pem` | 서버 인증서 | SSL_CERT_FILE |
| `key.pem` | 개인키 | SSL_KEY_FILE |
| `fullchain.pem` | 인증서 + 중간 인증서 체인 | SSL_CERT_FILE (권장) |
| `ca.pem` | CA 인증서 | 클라이언트 신뢰 설정 |

### 인증서 파일 내용 확인

```bash
# 인증서 정보 확인
openssl x509 -in cert.pem -noout -subject -dates -issuer

# 개인키 포함 여부 확인
grep -c "PRIVATE KEY" key.pem
# 결과가 1이면 개인키 포함

# 인증서-개인키 일치 확인 (두 해시값이 동일해야 함)
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5

# 개인키 비밀번호 여부 확인
openssl rsa -in key.pem -check -noout
# → "RSA key ok" 출력: 비밀번호 없음
# → "Enter pass phrase" 프롬프트: 비밀번호 있음 (SSL_KEY_PASSWORD 필요)
```

---

## 🖥️ Part 1: MCP 서버 설정

### Step 1. 인증서 파일 배치

```bash
# 1-1. 인증서 디렉토리 생성
sudo mkdir -p /etc/ssl/mcpstore

# 1-2. 인증서 파일 복사 (발급받은 파일 위치에서)
sudo cp /path/to/cert.pem /etc/ssl/mcpstore/
sudo cp /path/to/key.pem /etc/ssl/mcpstore/

# 1-3. 권한 설정
sudo chmod 644 /etc/ssl/mcpstore/cert.pem
sudo chmod 600 /etc/ssl/mcpstore/key.pem

# 1-4. 파일 확인
ls -la /etc/ssl/mcpstore/
```

### Step 2. 인증서 검증

```bash
# 2-1. 인증서 정보 확인
openssl x509 -in /etc/ssl/mcpstore/cert.pem -noout -subject -dates

# 2-2. 인증서 만료일 확인
openssl x509 -in /etc/ssl/mcpstore/cert.pem -noout -enddate

# 2-3. 인증서-개인키 일치 확인
openssl x509 -noout -modulus -in /etc/ssl/mcpstore/cert.pem | openssl md5
openssl rsa -noout -modulus -in /etc/ssl/mcpstore/key.pem | openssl md5
# ⚠️ 두 해시값이 반드시 동일해야 함

# 2-4. SAN (Subject Alternative Name) 확인
openssl x509 -in /etc/ssl/mcpstore/cert.pem -noout -text | grep -A1 "Subject Alternative Name"
```

### Step 3. MCP 컨테이너 실행 (볼륨 마운트)

```bash
# 3-1. 이미지 로드
podman load -i perplexity-mcp-server-3.0.tar

# 3-2. 기존 컨테이너 정리 (있는 경우)
podman stop perplexity-mcp-ssl 2>/dev/null
podman rm perplexity-mcp-ssl 2>/dev/null

# 3-3. MCP 컨테이너 실행 (인증서 폴더 볼륨 마운트)
# ✅ 비밀번호 없는 키 파일
podman run -d --name perplexity-mcp-ssl \
  -p 8200:8200 \
  -e PERPLEXITY_API_KEY="your-api-key" \
  -e SSL_ENABLED="true" \
  -e SSL_CERT_FILE="/app/ssl/cert.pem" \
  -e SSL_KEY_FILE="/app/ssl/key.pem" \
  -v /etc/ssl/mcpstore:/app/ssl:ro \
  perplexity-mcp-server:3.0

# ✅ 비밀번호 있는 키 파일 (암호화된 개인키)
podman run -d --name perplexity-mcp-ssl \
  -p 8200:8200 \
  -e PERPLEXITY_API_KEY="your-api-key" \
  -e SSL_ENABLED="true" \
  -e SSL_CERT_FILE="/app/ssl/cert.pem" \
  -e SSL_KEY_FILE="/app/ssl/key.pem" \
  -e SSL_KEY_PASSWORD="your-key-password" \
  -v /etc/ssl/mcpstore:/app/ssl:ro \
  perplexity-mcp-server:3.0
```

> 💡 **볼륨 마운트 설명**:
> - `-v /etc/ssl/mcpstore:/app/ssl:ro` : 호스트의 `/etc/ssl/mcpstore` 폴더 전체를 컨테이너의 `/app/ssl`에 읽기전용(ro)으로 마운트
> - 인증서 파일 변경 시 컨테이너 재시작만 하면 됨

### Step 4. HTTPS 연결 테스트

```bash
# 4-1. 컨테이너 상태 확인
podman ps | grep perplexity-mcp-ssl

# 4-2. 컨테이너 로그 확인
podman logs perplexity-mcp-ssl

# 4-3. HTTPS 헬스체크 (-k: 인증서 검증 스킵)
curl -k https://localhost:8200/health

# 4-4. 인증서 지정 테스트
curl --cacert /etc/ssl/mcpstore/cert.pem https://localhost:8200/health

# 4-5. SSL 상세 정보 확인
openssl s_client -connect localhost:8200 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -subject -dates
```

---

## 🌐 Part 2: Dify 서버 설정

### Step 5. 인증서 복사 (MCP → Dify)

```bash
# 5-1. Dify 서버에서 인증서 디렉토리 생성
sudo mkdir -p /etc/ssl/mcp-certs

# 5-2. MCP 서버에서 인증서 복사 (scp 사용)
scp user@MCP서버IP:/etc/ssl/mcpstore/cert.pem /etc/ssl/mcp-certs/mcp-ca.crt

# 5-3. 권한 설정
sudo chmod 644 /etc/ssl/mcp-certs/mcp-ca.crt

# 5-4. 파일 확인
ls -la /etc/ssl/mcp-certs/
```

### Step 6. Dify 컨테이너 설정 (podman run 수정)

#### 방법 A: podman run 명령어에 환경변수 및 볼륨 추가

```bash
# 기존 Dify API 컨테이너 중지/삭제
podman stop dify-api
podman rm dify-api

# 수정된 명령어로 재실행
podman run -d --name dify-api \
  -e SSL_CERT_FILE=/etc/ssl/certs/mcp-ca.crt \
  -e REQUESTS_CA_BUNDLE=/etc/ssl/certs/mcp-ca.crt \
  -e CURL_CA_BUNDLE=/etc/ssl/certs/mcp-ca.crt \
  -v /etc/ssl/mcp-certs/mcp-ca.crt:/etc/ssl/certs/mcp-ca.crt:ro \
  ... (기존 옵션들)
```

#### 방법 B: docker-compose.yml 수정

```yaml
services:
  api:
    image: langgenius/dify-api:latest
    environment:
      # 기존 환경변수들...
      - SSL_CERT_FILE=/etc/ssl/certs/mcp-ca.crt
      - REQUESTS_CA_BUNDLE=/etc/ssl/certs/mcp-ca.crt
      - CURL_CA_BUNDLE=/etc/ssl/certs/mcp-ca.crt
    volumes:
      # 기존 볼륨들...
      - /etc/ssl/mcp-certs/mcp-ca.crt:/etc/ssl/certs/mcp-ca.crt:ro
```

#### 방법 C: podman-compose 사용 시

```bash
# 7-1. docker-compose.yml 수정 (위 방법 B 참조)

# 7-2. 컨테이너 재시작
cd /path/to/dify
podman-compose down
podman-compose up -d
```

### Step 7. Dify HTTP Request 노드 설정

Dify 워크플로우에서 HTTP Request 노드 추가:

```yaml
# HTTP Request 노드 설정
URL: https://MCP서버IP:8200/search
Method: POST
Headers:
  Content-Type: application/json
Body (JSON):
  {
    "query": "{{#input.query#}}"
  }
Timeout: 30
```

### Step 8. 연결 테스트

```bash
# 8-1. Dify 컨테이너 내부에서 MCP 서버 연결 테스트
podman exec -it dify-api curl https://MCP서버IP:8200/health

# 8-2. MCP 도구 호출 테스트
podman exec -it dify-api curl -X POST https://MCP서버IP:8200/search \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트 검색"}'
```

---

## 🚨 트러블슈팅

### 오류 1: SSL: CERTIFICATE_VERIFY_FAILED

```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**원인**: Dify 컨테이너에서 MCP 서버 인증서를 신뢰하지 않음

**해결 방법**:
```bash
# 방법 1: Dify 컨테이너 환경변수 확인 (Step 6 참조)
# 아래 설정이 있는지 확인
# -e SSL_CERT_FILE=/etc/ssl/certs/mcp-ca.crt
# -e REQUESTS_CA_BUNDLE=/etc/ssl/certs/mcp-ca.crt
# -v /etc/ssl/mcp-certs/mcp-ca.crt:/etc/ssl/certs/mcp-ca.crt:ro

# 방법 2: 인증서 파일이 올바르게 복사되었는지 확인
ls -la /etc/ssl/mcp-certs/mcp-ca.crt

# 방법 3: curl에서 인증서 직접 지정하여 테스트
curl --cacert /etc/ssl/mcp-certs/mcp-ca.crt https://MCP서버IP:8200/health
```

### 오류 2: self signed certificate

```
curl: (60) SSL certificate problem: self signed certificate
```

**원인**: 자체서명 인증서가 신뢰되지 않음

**해결 방법**:
```bash
# 방법 1: Dify 컨테이너에 환경변수 설정 확인 (Step 6 참조)
# SSL_CERT_FILE, REQUESTS_CA_BUNDLE 환경변수와 볼륨 마운트 확인

# 방법 2: curl -k 옵션 사용 (테스트용)
curl -k https://MCP서버IP:8200/health

# 방법 3: curl에서 인증서 직접 지정
curl --cacert /etc/ssl/mcp-certs/mcp-ca.crt https://MCP서버IP:8200/health
```

### 오류 3: hostname doesn't match / IP address mismatch

```
ssl.CertificateError: hostname 'x.x.x.x' doesn't match
```

**원인**: 인증서의 CN/SAN에 접속하는 호스트명/IP가 포함되지 않음

**확인 방법**:
```bash
# 인증서의 SAN 확인
openssl x509 -in /etc/ssl/mcpstore/cert.pem -noout -text | grep -A1 "Subject Alternative Name"
```

**해결 방법**:
```bash
# 방법 1: 인증서에 포함된 호스트명으로 접속
# 예: 인증서 SAN에 DNS:mcp-server가 있으면
curl https://mcp-server:8200/health

# 방법 2: /etc/hosts에 호스트명 추가
echo "MCP서버IP mcp-server" | sudo tee -a /etc/hosts

# 방법 3: 새 인증서 발급 요청 (SAN에 IP 추가)
```

### 오류 4: certificate has expired

```
curl: (60) SSL certificate problem: certificate has expired
```

**원인**: 인증서 만료

**확인 방법**:
```bash
openssl x509 -in /etc/ssl/mcpstore/cert.pem -noout -dates
```

**해결 방법**:
- 새 인증서 발급 후 Part 1 Step 1부터 다시 진행

### 오류 5: unable to get local issuer certificate

```
curl: (60) SSL certificate problem: unable to get local issuer certificate
```

**원인**: 중간 인증서(Intermediate CA)가 누락됨

**해결 방법**:
```bash
# 방법 1: fullchain.pem 사용 (인증서 + 중간 인증서 포함)
sudo cp /path/to/fullchain.pem /etc/ssl/mcpstore/cert.pem

# 방법 2: 수동으로 체인 생성
cat cert.pem intermediate.pem > /etc/ssl/mcpstore/fullchain.pem
# 이후 SSL_CERT_FILE을 fullchain.pem으로 변경
```

### 오류 6: Permission denied (인증서 파일)

```
[Errno 13] Permission denied: '/etc/ssl/mcpstore/key.pem'
```

**원인**: 인증서 파일 권한 문제

**해결 방법**:
```bash
# 권한 확인
ls -la /etc/ssl/mcpstore/

# 권한 수정
sudo chmod 644 /etc/ssl/mcpstore/cert.pem
sudo chmod 600 /etc/ssl/mcpstore/key.pem
sudo chown root:root /etc/ssl/mcpstore/*
```

### 오류 7: Connection refused

```
curl: (7) Failed to connect to MCP서버IP port 8200: Connection refused
```

**원인**: MCP 컨테이너가 실행되지 않음 또는 포트 문제

**해결 방법**:
```bash
# 컨테이너 상태 확인
podman ps -a | grep perplexity-mcp

# 컨테이너 로그 확인
podman logs perplexity-mcp-ssl

# 포트 확인
ss -tlnp | grep 8200

# 방화벽 확인 (RHEL/CentOS)
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=8200/tcp --permanent
sudo firewall-cmd --reload
```

### 오류 8: 인증서-개인키 불일치

```
SSL_CTX_use_PrivateKey_file error
```

**원인**: cert.pem과 key.pem이 서로 맞지 않음

**확인 방법**:
```bash
# 두 해시값이 동일해야 함
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
```

**해결 방법**:
- 올바른 인증서-개인키 쌍으로 교체

---

## 📋 빠른 참조: 주요 명령어 요약

### MCP 서버 명령어

```bash
# 컨테이너 실행
podman run -d --name perplexity-mcp-ssl \
  -p 8200:8200 \
  -e PERPLEXITY_API_KEY="your-api-key" \
  -e SSL_ENABLED="true" \
  -e SSL_CERT_FILE="/app/ssl/cert.pem" \
  -e SSL_KEY_FILE="/app/ssl/key.pem" \
  -v /etc/ssl/mcpstore:/app/ssl:ro \
  perplexity-mcp-server:3.0

# 컨테이너 재시작
podman restart perplexity-mcp-ssl

# 로그 확인
podman logs -f perplexity-mcp-ssl

# 컨테이너 내부 접속
podman exec -it perplexity-mcp-ssl bash
```

### Dify 서버 명령어

```bash
# 인증서 복사
scp user@MCP서버IP:/etc/ssl/mcpstore/cert.pem /etc/ssl/mcp-certs/mcp-ca.crt

# 컨테이너 내부에서 테스트
podman exec -it dify-api curl https://MCP서버IP:8200/health

# MCP 도구 호출 테스트
podman exec -it dify-api curl -X POST https://MCP서버IP:8200/search \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트"}'
```

### 인증서 확인 명령어

```bash
# 인증서 정보
openssl x509 -in cert.pem -noout -subject -dates -issuer

# SAN 확인
openssl x509 -in cert.pem -noout -text | grep -A1 "Subject Alternative Name"

# 인증서-키 일치 확인
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5

# SSL 연결 테스트
openssl s_client -connect MCP서버IP:8200 -showcerts
```

---

## 📖 참고: 자체 CA 구축 (엔터프라이즈)

```bash
# === 1단계: 자체 CA 생성 ===
sudo mkdir -p /etc/ssl/myca
cd /etc/ssl/myca

# CA 개인키 생성
sudo openssl genrsa -out ca.key 4096

# CA 인증서 생성 (유효기간 10년)
sudo openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -out ca.crt \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=MyCompany/OU=CA/CN=MyCompany Root CA"

# === 2단계: 서버 인증서 생성 ===
cd /etc/ssl/mcpstore

# 서버 개인키 생성
sudo openssl genrsa -out server.key 2048

# CSR (인증서 서명 요청) 생성
sudo openssl req -new -key server.key -out server.csr \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=MyCompany/OU=IT/CN=mcp-server"

# SAN 확장 파일 생성
cat << 'EOF' | sudo tee server_ext.cnf
subjectAltName = DNS:mcp-server,DNS:localhost,IP:127.0.0.1,IP:192.168.1.100
EOF

# CA로 서버 인증서 서명
sudo openssl x509 -req -in server.csr \
  -CA /etc/ssl/myca/ca.crt \
  -CAkey /etc/ssl/myca/ca.key \
  -CAcreateserial \
  -out server.crt \
  -days 365 \
  -sha256 \
  -extfile server_ext.cnf

# 권한 설정
sudo chmod 644 server.crt
sudo chmod 600 server.key
```

### 2. 생성된 인증서 확인

```bash
# 인증서 정보 확인
openssl x509 -in /etc/ssl/mcpstore/server.crt -text -noout

# SAN 확인
openssl x509 -in /etc/ssl/mcpstore/server.crt -noout -text | grep -A1 "Subject Alternative Name"

# 유효기간 확인
openssl x509 -in /etc/ssl/mcpstore/server.crt -noout -dates

# 인증서-키 일치 확인
openssl x509 -noout -modulus -in /etc/ssl/mcpstore/server.crt | openssl md5
openssl rsa -noout -modulus -in /etc/ssl/mcpstore/server.key | openssl md5
```

### 3. MCP 서버에 사설 인증서 적용

```bash
# 컨테이너 실행
docker run -d --name perplexity-mcp-ssl \
  -p 8200:8200 \
  -e PERPLEXITY_API_KEY="your-api-key" \
  -e SSL_ENABLED="true" \
  -e SSL_CERT_FILE="/app/ssl/server.crt" \
  -e SSL_KEY_FILE="/app/ssl/server.key" \
  -v /etc/ssl/mcpstore/server.crt:/app/ssl/server.crt:ro \
  -v /etc/ssl/mcpstore/server.key:/app/ssl/server.key:ro \
  perplexity-mcp-server:3.0

# 테스트 (자체서명이므로 -k 옵션 필요)
curl -k https://localhost:8200/health
```

### 4. 클라이언트에 사설 인증서 신뢰 설정

사설 인증서는 기본적으로 신뢰되지 않으므로 클라이언트에 CA를 등록해야 합니다.

#### RHEL/CentOS/Rocky Linux

```bash
# 자체서명 인증서의 경우: server.crt 복사
sudo cp /etc/ssl/mcpstore/server.crt /etc/pki/ca-trust/source/anchors/mcp-server.crt

# 자체 CA 사용 시: ca.crt 복사
sudo cp /etc/ssl/myca/ca.crt /etc/pki/ca-trust/source/anchors/mycompany-ca.crt

# CA 저장소 업데이트
sudo update-ca-trust

# 확인
curl https://mcp-server:8200/health
```

#### Ubuntu/Debian

```bash
# 자체서명 인증서의 경우
sudo cp /etc/ssl/mcpstore/server.crt /usr/local/share/ca-certificates/mcp-server.crt

# 자체 CA 사용 시
sudo cp /etc/ssl/myca/ca.crt /usr/local/share/ca-certificates/mycompany-ca.crt

# CA 저장소 업데이트
sudo update-ca-certificates

# 확인
curl https://mcp-server:8200/health
```

#### Python/pip 환경

```bash
# 환경변수로 인증서 지정
export SSL_CERT_FILE=/etc/ssl/mcpstore/server.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/mcpstore/server.crt

# 또는 .env 파일에 추가
echo "SSL_CERT_FILE=/etc/ssl/mcpstore/server.crt" >> .env
echo "REQUESTS_CA_BUNDLE=/etc/ssl/mcpstore/server.crt" >> .env

# Python 코드에서 직접 지정
import requests
resp = requests.get('https://mcp-server:8200/health',
                    verify='/etc/ssl/mcpstore/server.crt')
```

#### Docker 컨테이너 (Dify, Open-WebUI)

```bash
# docker-compose.yml에 볼륨 및 환경변수 추가
services:
  your-service:
    environment:
      - SSL_CERT_FILE=/etc/ssl/certs/mcp-server.crt
      - REQUESTS_CA_BUNDLE=/etc/ssl/certs/mcp-server.crt
      - NODE_EXTRA_CA_CERTS=/etc/ssl/certs/mcp-server.crt  # Node.js용
    volumes:
      - /etc/ssl/mcpstore/server.crt:/etc/ssl/certs/mcp-server.crt:ro
```

### 5. 사설 인증서 갱신 절차

```bash
# 1. 새 인증서 생성 (기존 키 재사용 가능)
cd /etc/ssl/mcpstore
sudo openssl req -x509 -nodes -days 365 -key server.key \
  -out server.crt.new \
  -config openssl.cnf

# 2. 기존 인증서 백업
sudo mv server.crt server.crt.backup.$(date +%Y%m%d)

# 3. 새 인증서 적용
sudo mv server.crt.new server.crt

# 4. MCP 컨테이너 재시작
docker restart perplexity-mcp-ssl

# 5. 클라이언트 CA 저장소 업데이트 (모든 클라이언트 서버에서)
sudo cp /etc/ssl/mcpstore/server.crt /etc/pki/ca-trust/source/anchors/mcp-server.crt
sudo update-ca-trust

# 6. 연결 테스트
curl https://mcp-server:8200/health
```

### 6. 자주 발생하는 사설 인증서 오류

#### 오류: self signed certificate

```bash
# 원인: 자체서명 인증서가 신뢰되지 않음
# 해결 1: CA 저장소에 추가
sudo cp server.crt /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust

# 해결 2: curl에서 인증서 지정
curl --cacert /etc/ssl/mcpstore/server.crt https://mcp-server:8200/health

# 해결 3: 검증 스킵 (테스트용)
curl -k https://mcp-server:8200/health
```

#### 오류: certificate has expired

```bash
# 원인: 인증서 만료
# 확인:
openssl x509 -in server.crt -noout -dates

# 해결: 새 인증서 생성 (위 갱신 절차 참조)
```

#### 오류: IP address mismatch

```bash
# 원인: 인증서 SAN에 접속 IP가 없음
# 확인:
openssl x509 -in server.crt -noout -text | grep -A1 "Subject Alternative Name"

# 해결: SAN에 IP 추가하여 인증서 재생성
# openssl.cnf의 [alt_names] 섹션에 IP.x = 실제IP 추가
```

## 📚 참고 자료

- **MCP 공식 문서**: https://modelcontextprotocol.io
- **OpenAI API**: https://platform.openai.com/docs/api-reference
- **Perplexity API**: https://docs.perplexity.ai

## 📝 라이선스

Open WebUI 프로젝트와 동일

---

**최종 업데이트**: 2026-01-13
**버전**: 3.0.0
**포트**: 8200 (컨테이너), 8100 (로컬)
