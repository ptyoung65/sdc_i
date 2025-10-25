# External LLM MCP Server - 배포 가이드

Open WebUI에서 외부 LLM (ChatGPT, Perplexity)을 사용하기 위한 MCP 서버 배포 가이드

## 📋 목차

1. [개요](#개요)
2. [배포 시나리오](#배포-시나리오)
3. [로컬 서버 설치](#로컬-서버-설치)
4. [원격 서버 배포](#원격-서버-배포)
5. [Open WebUI 연동](#open-webui-연동)
6. [오프라인 설치](#오프라인-설치)
7. [문제 해결](#문제-해결)

---

## 개요

### 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                     Open WebUI (Podman)                      │
│                        Port: 3000                            │
└────────────┬─────────────────────────┬────────────────────────┘
             │ (Local)                 │ (Remote)
             │ host.containers.        │ http://REMOTE_IP:8100
             │ internal:8100           │
             ▼                         ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│  Local MCP Server    │    │  Remote MCP Server           │
│  (Same Host)         │    │  (Different Server)          │
│  Port: 8100          │    │  Port: 8100                  │
└──────────┬───────────┘    └────────────┬─────────────────┘
           │                              │
           └──────────┬───────────────────┘
                      ▼
         ┌────────────────────────────┐
         │   External LLM APIs        │
         │   - ChatGPT (OpenAI)       │
         │   - Perplexity             │
         └────────────────────────────┘
```

### 제공 스크립트

| 스크립트 | 용도 | 실행 위치 |
|----------|------|-----------|
| `install.sh` | 독립 서버 설치 | 설치 대상 서버 |
| `deploy.sh` | 원격 서버 자동 배포 | 배포 작업 서버 |
| `configure_openwebui.sh` | Open WebUI 연동 설정 | Open WebUI 서버 |
| `prepare_offline_packages.sh` | 오프라인 패키지 준비 | 온라인 서버 |
| `start_server.sh` | 서버 시작 (개발용) | MCP 서버 |

---

## 배포 시나리오

### 시나리오 1: Local MCP Server

**구성:**
- Open WebUI: Podman 컨테이너
- MCP Server: 동일 호스트에서 실행

**장점:**
- 네트워크 지연 없음
- 방화벽 설정 불필요
- 단순한 구성

**단점:**
- Open WebUI 서버 리소스 사용
- 확장성 제한

```bash
# 설치
cd /home/chatpro/open-webui-main/mcp-external-llm-server
./start_server.sh --background

# Open WebUI 연동
./configure_openwebui.sh local
```

**Open WebUI URL:** `http://host.containers.internal:8100/mcp`

---

### 시나리오 2: Remote MCP Server

**구성:**
- Open WebUI: 서버 A
- MCP Server: 서버 B (물리적으로 분리)

**장점:**
- 리소스 분산
- 확장성 우수
- 독립적 관리

**단점:**
- 네트워크 설정 필요
- 방화벽 구성 필요
- 약간의 네트워크 지연

```bash
# 원격 서버 배포
./deploy.sh 192.168.1.100 root 22

# Open WebUI 연동
./configure_openwebui.sh remote 192.168.1.100
```

**Open WebUI URL:** `http://192.168.1.100:8100/mcp`

---

## 로컬 서버 설치

### 방법 1: 개발 모드 (빠른 테스트)

```bash
cd /home/chatpro/open-webui-main/mcp-external-llm-server

# 환경 변수 설정 (선택적)
cp .env.example .env
vi .env
# OPENAI_API_KEY=sk-...
# PERPLEXITY_API_KEY=pplx-...

# 서버 시작
./start_server.sh --background

# 상태 확인
curl http://localhost:8100/health
```

### 방법 2: Systemd 서비스 (프로덕션)

```bash
cd /home/chatpro/open-webui-main/mcp-external-llm-server

# 설치 (root 권한 필요)
sudo ./install.sh

# 서비스 관리
systemctl status external-llm-mcp
systemctl restart external-llm-mcp
journalctl -u external-llm-mcp -f
```

### Open WebUI 연동

```bash
# Local 연동 설정
./configure_openwebui.sh local

# 출력된 안내에 따라 웹 UI에서 등록
# Settings → Workspace → Tools → Tool Servers
# Server URL: http://host.containers.internal:8100/mcp
# Server Type: mcp
# Auth: none
```

---

## 원격 서버 배포

### 사전 요구사항

1. **원격 서버:**
   - Python 3.9+
   - SSH 접속 가능
   - Root 또는 sudo 권한

2. **네트워크:**
   - Open WebUI 서버 → MCP 서버 (포트 8100) 접근 가능
   - 방화벽 설정 필요

### 자동 배포 (SSH)

```bash
cd /home/chatpro/open-webui-main/mcp-external-llm-server

# 기본 배포 (root 사용자, SSH 포트 22)
./deploy.sh 192.168.1.100

# 사용자 지정
./deploy.sh 192.168.1.100 admin 2222

# 배포 과정:
# 1. 패키지 생성
# 2. 원격 서버로 전송
# 3. 자동 설치
# 4. 서비스 시작
# 5. 헬스 체크
```

### 수동 배포

```bash
# 1. 패키지 생성
./deploy.sh 192.168.1.100 root 22 manual

# 2. 수동 전송
scp external-llm-mcp-server.tar.gz root@192.168.1.100:/tmp/

# 3. 원격 서버에서 설치
ssh root@192.168.1.100
cd /tmp
tar -xzf external-llm-mcp-server.tar.gz
cd external-llm-mcp-server
sudo ./install.sh
```

### 원격 서버 방화벽 설정

**CentOS/RHEL (firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=8100/tcp
sudo firewall-cmd --reload
```

**Ubuntu (UFW):**
```bash
sudo ufw allow 8100/tcp
sudo ufw reload
```

### Open WebUI 연동

```bash
# Remote 연동 설정
./configure_openwebui.sh remote 192.168.1.100

# 웹 UI에서 등록
# Server URL: http://192.168.1.100:8100/mcp
# Server Type: mcp
# Auth: none
```

---

## Open WebUI 연동

### 웹 UI에서 등록

1. **Open WebUI 접속**
   ```
   http://localhost:3000
   ```

2. **설정 메뉴**
   ```
   Settings (⚙️) → Workspace → Tools → Tool Servers
   ```

3. **MCP 서버 추가**

   **Local 서버:**
   ```
   Server URL: http://host.containers.internal:8100/mcp
   Server Type: mcp
   Authentication: none
   Name: External LLM Server (Local)
   Description: ChatGPT, Perplexity (Local)
   ```

   **Remote 서버:**
   ```
   Server URL: http://192.168.1.100:8100/mcp
   Server Type: mcp
   Authentication: none
   Name: External LLM Server (Remote)
   Description: ChatGPT, Perplexity (Remote Server)
   ```

4. **연결 테스트**
   - "Verify" 버튼 클릭
   - 사용 가능한 도구 확인:
     - query_chatgpt
     - query_perplexity
     - get_llm_status

5. **저장**
   - "Save" 버튼 클릭

### 사용 예시

```
사용자: ChatGPT를 통해 "인공지능이란?" 질문해줘

AI: (query_chatgpt 도구 사용)
→ **ChatGPT 응답 (gpt-3.5-turbo)**

인공지능(AI)은 컴퓨터 시스템이 인간의 지능을 모방하여...

---
토큰 사용: {'prompt_tokens': 15, 'completion_tokens': 250}
```

---

## 오프라인 설치

### 1. 온라인 서버에서 패키지 준비

```bash
cd /home/chatpro/open-webui-main/mcp-external-llm-server

# Python 패키지 다운로드
./prepare_offline_packages.sh

# 전체 패키지 생성
./deploy.sh 0.0.0.0 root 22 manual
```

### 2. 오프라인 서버로 전송

```bash
# USB 또는 네트워크로 전송
# 생성된 파일:
# - external-llm-mcp-server.tar.gz (애플리케이션)
# - offline-packages/ (Python 패키지)
```

### 3. 오프라인 서버에서 설치

```bash
# 압축 해제
tar -xzf external-llm-mcp-server.tar.gz
cd external-llm-mcp-server

# 오프라인 패키지 복사 (준비한 경우)
cp -r /path/to/offline-packages ./

# 설치
sudo ./install.sh
```

---

## API 키 설정

### 환경 변수 설정

**개발 모드:**
```bash
vi .env

OPENAI_API_KEY=sk-your-openai-api-key
PERPLEXITY_API_KEY=pplx-your-perplexity-api-key
```

**Systemd 서비스:**
```bash
sudo vi /opt/external-llm-mcp-server/.env

OPENAI_API_KEY=sk-your-openai-api-key
PERPLEXITY_API_KEY=pplx-your-perplexity-api-key

# 재시작
sudo systemctl restart external-llm-mcp
```

### 도구 호출 시 전달

API 키를 환경 변수에 설정하지 않고, 도구 사용 시 파라미터로 전달 가능:

```json
{
  "question": "질문 내용",
  "api_key": "sk-your-openai-api-key"
}
```

---

## 문제 해결

### 연결 실패

**증상:**
```
Error: Failed to connect to MCP server
```

**해결:**
```bash
# 1. MCP 서버 상태 확인
systemctl status external-llm-mcp
curl http://localhost:8100/health

# 2. 방화벽 확인
sudo firewall-cmd --list-ports    # CentOS/RHEL
sudo ufw status                    # Ubuntu

# 3. 네트워크 확인
ping <MCP_SERVER_IP>
telnet <MCP_SERVER_IP> 8100
```

### API 키 오류

**증상:**
```
Error: OpenAI API 키가 설정되지 않았습니다
```

**해결:**
```bash
# 환경 변수 확인
sudo cat /opt/external-llm-mcp-server/.env

# API 키 설정
sudo vi /opt/external-llm-mcp-server/.env
sudo systemctl restart external-llm-mcp
```

### 포트 충돌

**증상:**
```
Error: Address already in use
```

**해결:**
```bash
# 포트 사용 프로세스 확인
lsof -i :8100

# 프로세스 종료
lsof -ti:8100 | xargs kill -9

# 다른 포트 사용
sudo vi /opt/external-llm-mcp-server/.env
# MCP_SERVER_PORT=8200
sudo systemctl restart external-llm-mcp
```

### 로그 확인

```bash
# Systemd 서비스 로그
journalctl -u external-llm-mcp -f

# 파일 로그
tail -f /opt/external-llm-mcp-server/logs/server.log

# 개발 모드 로그
tail -f /tmp/external-llm-mcp.log
```

---

## 관리 명령어

### Systemd 서비스

```bash
# 상태 확인
systemctl status external-llm-mcp

# 시작
systemctl start external-llm-mcp

# 중지
systemctl stop external-llm-mcp

# 재시작
systemctl restart external-llm-mcp

# 자동 시작 설정
systemctl enable external-llm-mcp

# 자동 시작 해제
systemctl disable external-llm-mcp
```

### 헬스 체크

```bash
# 로컬
curl http://localhost:8100/health

# 원격
curl http://192.168.1.100:8100/health
```

### MCP 프로토콜 테스트

```bash
# Tools List
curl -X POST http://localhost:8100/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'

# ChatGPT 호출
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
        "api_key": "sk-your-key"
      }
    }
  }'
```

---

## 보안 고려사항

### API 키 보호

1. **환경 변수 사용**
   - `.env` 파일에 저장
   - 파일 권한: `600` (소유자만 읽기/쓰기)

2. **Git 제외**
   ```bash
   echo ".env" >> .gitignore
   ```

3. **원격 전송 주의**
   - SCP 사용 시 암호화 확인
   - 전송 후 원본 삭제

### 네트워크 보안

1. **방화벽 설정**
   - 필요한 IP만 허용
   - 포트 8100만 개방

2. **HTTPS 사용 (권장)**
   - Nginx 리버스 프록시
   - Let's Encrypt 인증서

---

## 부록

### 파일 구조

```
mcp-external-llm-server/
├── external_llm_mcp_server.py      # 메인 서버
├── install.sh                      # 독립 설치 스크립트
├── deploy.sh                       # 원격 배포 스크립트
├── configure_openwebui.sh          # Open WebUI 연동
├── prepare_offline_packages.sh     # 오프라인 패키지 준비
├── start_server.sh                 # 개발 모드 시작
├── .env.example                    # 환경 변수 예시
└── README.md                       # 기본 문서
```

### 포트 정보

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Open WebUI | 3000 | 웹 인터페이스 |
| MCP Server | 8100 | MCP 프로토콜 |
| OpenAI API | 443 | ChatGPT (HTTPS) |
| Perplexity API | 443 | Perplexity (HTTPS) |

---

**최종 업데이트:** 2025-10-25
**버전:** 1.0.0
