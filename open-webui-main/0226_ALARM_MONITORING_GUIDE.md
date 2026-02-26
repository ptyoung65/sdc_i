# [2026-02-26] SDC 알람 모니터링 체계 운영 가이드

## 1. 전체 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SDC 알람 모니터링 체계 구성도                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [호스트 서버]                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  cron (매 1분)                                               │   │
│  │  ├── podman_metrics.sh  → podman_containers.prom            │   │
│  │  ├── alert_logger.sh    → podman_alerts.prom                │   │
│  │  │                      → logs/alert.log (누적)              │   │
│  │  │                      → logs/alert_active.log (활성만)     │   │
│  │  └── (매 30초) podman_metrics.sh                             │   │
│  │                                                              │   │
│  │  cron (매 2분)                                               │   │
│  │  └── podman_watchdog.sh → podman_watchdog.prom              │   │
│  │                         → logs/watchdog.log                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       ↓ .prom 파일                                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  sdc-node-exporter (포트 9100)                               │   │
│  │  textfile collector: /home/chatpro/monitoring/               │   │
│  │                      node-exporter/textfile/*.prom           │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                              ↓ HTTP scrape (15초)                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  sdc-prometheus (포트 9090)                                  │   │
│  │  - 메트릭 수집 (TSDB, 30일 보관)                              │   │
│  │  - 알림 규칙 평가 (container_alert_rules.yml, alert_rules.yml)│   │
│  │  - Alertmanager 연동 (이메일 알림)                            │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                              ↓ 데이터소스                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  sdc-grafana (포트 3030)                                     │   │
│  │  - 컨테이너 모니터링 대시보드                                   │   │
│  │  - 서버 리소스 대시보드                                        │   │
│  │  - 알람 상태 시각화                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  모니터링 백엔드 (포트 8085)                                   │   │
│  │  services/monitoring-backend/main.py                         │   │
│  │  - FastAPI 기반 모니터링 API 서버                              │   │
│  │  - 사용자 활동, 채팅 이력, 세션 통계                            │   │
│  │  - Open WebUI 관리자 대시보드 데이터 제공                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [원격 서버 모니터링 (192.168.122.177)]                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  cron (매 5분)                                               │   │
│  │  └── remote_health_check.sh → remote_health.prom            │   │
│  │                              → logs/remote_health.log        │   │
│  │  로컬 watchdog 실패 시:                                       │   │
│  │  └── remote_restart.sh → SSH로 원격 컨테이너 재시작            │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 프로그램 목록 및 기능 설명

### 2.1 데이터 수집 스크립트

#### `podman_metrics.sh` — 컨테이너 상태 메트릭 수집
| 항목 | 내용 |
|------|------|
| **경로** | `/home/chatpro/monitoring/podman_metrics.sh` |
| **실행 주기** | cron 매 1분 (30초 간격 2회) |
| **기능** | `podman ps -a`로 전체 컨테이너 상태를 Prometheus textfile 형식으로 기록 |
| **출력 파일** | `node-exporter/textfile/podman_containers.prom` |
| **생성 메트릭** | `podman_container_running{name="..."} 1/0` (컨테이너별 running 여부) |
|               | `podman_container_count{state="total/running/stopped"}` (컨테이너 수) |
|               | `podman_metrics_last_update_timestamp` (마지막 수집 시각) |
| **작성일** | 2026-02-07 |

#### `alert_logger.sh` — 컨테이너 알람 감지 및 로그 기록 ⭐ 신규
| 항목 | 내용 |
|------|------|
| **경로** | `/home/chatpro/monitoring/alert_logger.sh` |
| **실행 주기** | cron 매 1분 |
| **기능** | 컨테이너 상태 변화 감지 → 알람 로그 + Prometheus 메트릭 생성 |
| **감시 대상** | `watchdog.conf`에 등록된 컨테이너 (기존 설정 재사용) |
| **상태 비교** | `logs/alert_state/*.state` 파일에 이전 상태 저장, 현재 상태와 비교 |
| **출력 파일** | 아래 3개 파일 동시 생성 |
| **작성일** | 2026-02-26 |

**alert_logger.sh 출력 파일 상세:**

| 파일 | 경로 | 역할 | 삭제 여부 |
|------|------|------|-----------|
| **알람 이력 (누적)** | `logs/alert.log` | 모든 FIRING/RESOLVED 이벤트 누적 기록 | 삭제 안됨 (10000줄 초과 시 로테이션) |
| **활성 알람 (미해소)** | `logs/alert_active.log` | 현재 firing 중인 알람만 표시 | 해소 시 자동 삭제 |
| **Grafana 메트릭** | `node-exporter/textfile/podman_alerts.prom` | Prometheus → Grafana 실시간 상태 | 매 실행 시 갱신 |

**alert_logger.sh 동작 흐름:**
```
cron 실행 → watchdog.conf에서 감시 대상 로드
    ↓
각 컨테이너: podman inspect → 현재 상태 확인
    ↓
logs/alert_state/컨테이너명.state (이전 상태)와 비교
    ↓
상태 변화 감지 시:
  running → exited/dead : [FIRING]  → alert.log에 기록 + alert_active.log에 추가
  exited  → running     : [RESOLVED] → alert.log에 기록 + alert_active.log에서 제거
    ↓
podman_alerts.prom 갱신 → Node Exporter → Prometheus → Grafana
```

**alert_logger.sh 생성 메트릭:**
| 메트릭 | 설명 |
|--------|------|
| `podman_alert_firing{name="..."}` | 컨테이너별 알람 상태 (1=firing, 0=ok) |
| `podman_alert_firing_total` | 현재 firing 중인 전체 알람 수 |
| `podman_alert_last_fired_timestamp{name="..."}` | 컨테이너별 마지막 알람 발생 시각 |
| `podman_alert_events_in_last_run{type="firing/resolved"}` | 직전 실행의 이벤트 수 |
| `podman_alert_logger_last_run_timestamp` | 마지막 실행 시각 |

**alert.log 로그 형식:**
```
[2026-02-26 19:29:42] [FIRING] [critical] sdc-guardrails - 컨테이너 중지 감지 (running → exited)
[2026-02-26 19:29:55] [RESOLVED] [info] sdc-guardrails - 컨테이너 복구됨 (exited → running)
[2026-02-26 19:36:06] [FIRING] [critical] sdc-pipelines - 컨테이너 중지 감지 (stopping → exited)
[2026-02-26 19:36:18] [RESOLVED] [info] sdc-pipelines - 컨테이너 복구됨 (exited → running)
```

**alert_active.log 로그 형식 (미해소 알람만):**
```
[2026-02-26 19:36:06] [FIRING] [critical] sdc-pipelines - 상태: exited (미해소)
```
→ 컨테이너 복구 시 해당 줄이 자동으로 사라짐 (파일이 비어있으면 모든 알람 해소)

---

### 2.2 자동 복구 스크립트

#### `podman_watchdog.sh` — 컨테이너 자동 재시작
| 항목 | 내용 |
|------|------|
| **경로** | `/home/chatpro/monitoring/podman_watchdog.sh` |
| **실행 주기** | cron 매 2분 |
| **기능** | 중지된 컨테이너 감지 → 자동 재시작 (쿨다운/suppress 보호) |
| **감시 대상** | `watchdog.conf`에 등록된 컨테이너 |
| **출력 파일** | `logs/watchdog.log`, `node-exporter/textfile/podman_watchdog.prom` |
| **보호 기능** | 5분 쿨다운, 시간당 최대 5회 제한, suppress(수동 중지 보호) |
| **작성일** | 2026-02-07, 수정 2026-02-10 |

**생성 메트릭:**
| 메트릭 | 설명 |
|--------|------|
| `podman_watchdog_restart_total{result="success/fail"}` | 재시작 성공/실패 누적 |
| `podman_watchdog_last_run_timestamp` | 마지막 실행 시각 |
| `podman_watchdog_restart_in_last_run` | 직전 실행의 재시작 횟수 |

#### `remote_health_check.sh` — 원격 서버 헬스체크
| 항목 | 내용 |
|------|------|
| **경로** | `/home/chatpro/monitoring/remote_health_check.sh` |
| **실행 주기** | cron 매 5분 |
| **기능** | SSH로 대상 서버(192.168.122.177) 컨테이너 상태 확인, 로컬 watchdog 실패 시 원격 재시작 |
| **출력 파일** | `logs/remote_health.log`, `node-exporter/textfile/remote_health.prom` |
| **작성일** | 2026-02-22 |

#### `remote_restart.sh` — 원격 컨테이너 재시작
| 항목 | 내용 |
|------|------|
| **경로** | `/home/chatpro/monitoring/remote_restart.sh` |
| **기능** | SSH를 통해 대상 서버의 개별 컨테이너 재시작 (쿨다운 보호) |
| **호출 방법** | `remote_health_check.sh`에서 자동 호출, 또는 수동 실행 |
| **사용법** | `./remote_restart.sh 192.168.122.177 sdc-open-webui` |
| **작성일** | 2026-02-22 |

---

### 2.3 설치/관리 스크립트

#### `setup-watchdog-cron.sh` — cron 등록 및 관리 ⭐ 수정
| 항목 | 내용 |
|------|------|
| **경로** | `/home/chatpro/monitoring/setup-watchdog-cron.sh` |
| **기능** | Watchdog, Metrics, Alert Logger cron 등록/제거/상태확인 |
| **수정일** | 2026-02-26 (alert_logger 지원 추가) |

**명령어 목록:**
| 명령 | 설명 |
|------|------|
| `./setup-watchdog-cron.sh install` | 전체 설치 (Metrics + Watchdog + Alert Logger cron 등록) |
| `./setup-watchdog-cron.sh install --interval 3` | Watchdog 3분 간격으로 설치 |
| `./setup-watchdog-cron.sh status` | 전체 상태 확인 (cron, 로그, 컨테이너) |
| `./setup-watchdog-cron.sh remove` | 전체 cron 제거 |
| `./setup-watchdog-cron.sh interval 5` | Watchdog 간격을 5분으로 변경 |
| `./setup-watchdog-cron.sh list` | 감시 대상 컨테이너 목록 + 상태 |
| `./setup-watchdog-cron.sh add <이름>` | 감시 대상 컨테이너 추가 |
| `./setup-watchdog-cron.sh del <이름>` | 감시 대상 컨테이너 제거 |
| `./setup-watchdog-cron.sh suppress <이름>` | 자동 재시작 방지 (수동 중지 보호) |
| `./setup-watchdog-cron.sh unsuppress <이름>` | 자동 재시작 방지 해제 |

**[2026-02-26] 수정 사항:**
- `alert_logger.sh` cron 등록/제거/상태확인 로직 추가
- 기존 cron이 동일 설정으로 등록되어 있으면 건너뜀 (불필요한 재등록 방지)
- `alert_logger.sh` 파일이 없어도 다른 설치가 중단되지 않음 (선택 스크립트)

#### `install_monitoring.sh` — 모니터링 통합 설치
| 항목 | 내용 |
|------|------|
| **경로** | `/home/chatpro/monitoring/install_monitoring.sh` |
| **기능** | 모니터링 서버 + 대상 서버 전체 자동 설치 |
| **주요 기능** | SSH 키 설정, 스크립트 배포, Node Exporter 설치, cron 등록, Alertmanager 설치 |
| **작성일** | 2026-02-22 |

**명령어:**
| 명령 | 설명 |
|------|------|
| `./install_monitoring.sh install` | 전체 설치 |
| `./install_monitoring.sh ssh-setup` | SSH 키만 설정 |
| `./install_monitoring.sh deploy` | 대상 서버에 스크립트 배포 |
| `./install_monitoring.sh deploy-local` | 모니터링 서버 자체 설정 |
| `./install_monitoring.sh cron` | cron만 등록 |
| `./install_monitoring.sh status` | 전체 상태 확인 |
| `./install_monitoring.sh file-map` | 전체 파일 배치 경로 출력 |

---

### 2.4 설정 파일

#### `watchdog.conf` — 감시 대상 컨테이너 목록
| 항목 | 내용 |
|------|------|
| **경로** | `/home/chatpro/monitoring/watchdog.conf` |
| **역할** | `podman_watchdog.sh`, `alert_logger.sh` 공통으로 사용하는 감시 대상 목록 |
| **수정 방법** | 직접 편집 또는 `./setup-watchdog-cron.sh add/del` 명령 사용 |
| **반영 시점** | 다음 cron 실행 시 자동 반영 (재시작 불필요) |

**현재 등록된 컨테이너:**
```
sdc-open-webui
sdc-redis-dev
sdc-pipelines
sdc-guardrails
sdc-monitoring
```

---

### 2.5 컨테이너 서비스

#### Prometheus (`sdc-prometheus`)
| 항목 | 내용 |
|------|------|
| **포트** | 9090 |
| **시작 스크립트** | `podman-run-monitoring.sh` |
| **설정 파일** | `prometheus/prometheus.yml` |
| **알림 규칙** | `prometheus/container_alert_rules.yml`, `prometheus/alert_rules.yml` |
| **데이터 보관** | 30일 (`--storage.tsdb.retention.time=30d`) |
| **수집 간격** | 15초 (`scrape_interval: 15s`) |

**수집 대상 (Scrape Targets):**
| Job | 대상 | 포트 | 수집 내용 |
|-----|------|------|-----------|
| `prometheus` | localhost | 9090 | 자체 메트릭 |
| `app-after` | 192.168.122.178 | 9100 | 서버 리소스 |
| `app-before` | 192.168.122.177 | 9100 | 서버 리소스 |
| `db-main` | 192.168.122.85 | 9100 | 서버 리소스 |
| `db-sub` | 192.168.122.154 | 9100 | 서버 리소스 |
| `node-exporter` | 178, 177 | 9100 | textfile 메트릭 (컨테이너 상태) |
| `cadvisor` | 192.168.122.178 | 8085 | 컨테이너 CPU/메모리/네트워크 |
| `redis-exporter` | 192.168.122.178 | 9121 | Redis 메트릭 |

**알림 규칙 (container_alert_rules.yml):**
| 알림 이름 | 조건 | 심각도 | 대기 시간 |
|-----------|------|--------|-----------|
| ExporterDown | cAdvisor/Redis exporter 무응답 | critical | 2분 |
| ContainerHighCpu | CPU > 80% | warning | 5분 |
| ContainerCpuCritical | CPU > 95% | critical | 3분 |
| ContainerHighMemory | 메모리 > 2GB | warning | 5분 |
| ContainerMemoryCritical | 메모리 > 4GB | critical | 3분 |
| ContainerNetworkErrors | 네트워크 에러 > 5/초 | warning | 5분 |
| ContainerRestarted | 10분 내 재시작 감지 | warning | 즉시 |
| RedisDown | Redis 무응답 | critical | 1분 |
| RedisHighMemory | Redis 메모리 > 1GB | warning | 5분 |
| RedisHighConnections | Redis 연결 > 100 | warning | 5분 |

**알림 규칙 (alert_rules.yml) - textfile 메트릭 기반:**
| 알림 이름 | 조건 | 심각도 | 대기 시간 |
|-----------|------|--------|-----------|
| PodmanContainerDown | `podman_container_running == 0` | critical | 1분 |
| CriticalContainerDown | 핵심 5개 컨테이너 중지 | critical | 30초 |
| StoppedContainersExist | 중지된 컨테이너 존재 | warning | 2분 |
| WatchdogStale | Watchdog 5분 이상 미실행 | warning | 1분 |
| MetricsCollectionStale | 메트릭 수집 2분 이상 중단 | warning | 1분 |
| NodeExporterDown | Node Exporter 무응답 | critical | 1분 |

#### Grafana (`sdc-grafana`)
| 항목 | 내용 |
|------|------|
| **포트** | 3030 |
| **접속 URL** | http://192.168.122.178:3030 |
| **로그인** | admin / sdc_monitor_2025 |
| **데이터소스** | Prometheus (localhost:9090) |

**대시보드 목록:**
| 파일 | 내용 |
|------|------|
| `container-monitoring.json` | cAdvisor 기반 컨테이너 모니터링 (CPU, 메모리, 네트워크, 알람) |
| `multi-server-container-monitoring.json` | textfile 기반 멀티서버 컨테이너 상태 |
| `node-exporter-full.json` | 서버 리소스 상세 (CPU, 메모리, 디스크, 네트워크) |
| `vm-monitoring.json` | 가상머신 모니터링 |
| `docker-containers.json` | Docker 컨테이너 모니터링 |

#### Alertmanager (`alertmanager`)
| 항목 | 내용 |
|------|------|
| **포트** | 13084 |
| **설정 파일** | `alertmanager/alertmanager.yml` |
| **기능** | Prometheus 알림 수신 → 이메일 발송 |
| **이메일 수신자** | ptyoung@naver.com |
| **그룹핑** | alertname + server_ip 조합, 5분 그룹 간격 |
| **critical 알림** | 10초 대기 후 즉시 발송, 30분 반복 |

#### 모니터링 백엔드 (`sdc-monitoring`)
| 항목 | 내용 |
|------|------|
| **경로** | `/home/chatpro/open-webui-main/services/monitoring-backend/main.py` |
| **포트** | 8085 |
| **기능** | FastAPI 기반 모니터링 API 서버 |
| **데이터** | PostgreSQL 직접 조회 (사용자 활동, 채팅 이력, 세션 통계) |
| **용도** | Open WebUI 관리자 대시보드(monitoring2)에 데이터 제공 |

---

## 3. 파일 구조

```
/home/chatpro/monitoring/
│
├── [스크립트]
│   ├── podman_metrics.sh             # 컨테이너 상태 메트릭 수집 (cron 1분)
│   ├── alert_logger.sh               # ⭐ 알람 감지 + 로그 기록 (cron 1분) [신규]
│   ├── podman_watchdog.sh            # 컨테이너 자동 재시작 (cron 2분)
│   ├── remote_health_check.sh        # 원격 서버 헬스체크 (cron 5분)
│   ├── remote_restart.sh             # 원격 컨테이너 재시작
│   ├── setup-watchdog-cron.sh        # ⭐ cron 설치/관리 스크립트 [수정]
│   └── install_monitoring.sh         # 모니터링 통합 설치 스크립트
│
├── [설정 파일]
│   ├── watchdog.conf                 # 감시 대상 컨테이너 목록
│   └── alertmanager/
│       └── alertmanager.yml          # Alertmanager 이메일 알림 설정
│
├── [Prometheus 설정]
│   ├── prometheus.yml                # Prometheus 메인 설정 (루트)
│   └── prometheus/
│       ├── prometheus.yml            # Prometheus 메인 설정 (배포용)
│       ├── container_alert_rules.yml # cAdvisor/Redis 기반 알림 규칙
│       └── alert_rules.yml           # textfile 기반 알림 규칙
│
├── [Grafana 설정]
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/prometheus.yml   # 데이터소스 설정
│       │   └── dashboards/dashboards.yml    # 대시보드 자동 로드
│       └── dashboards/
│           ├── container-monitoring.json     # 컨테이너 모니터링
│           ├── multi-server-container-monitoring.json  # 멀티서버 컨테이너
│           ├── node-exporter-full.json       # 서버 리소스 상세
│           └── vm-monitoring.json            # VM 모니터링
│
├── [Node Exporter textfile (Prometheus 메트릭)]
│   └── node-exporter/textfile/
│       ├── podman_containers.prom    # 컨테이너 상태 (podman_metrics.sh)
│       ├── podman_alerts.prom        # ⭐ 알람 상태 (alert_logger.sh) [신규]
│       ├── podman_watchdog.prom      # 워치독 재시작 이벤트 (podman_watchdog.sh)
│       └── remote_health.prom        # 원격 헬스체크 (remote_health_check.sh)
│
├── [로그 파일]
│   └── logs/
│       ├── alert.log                 # ⭐ 알람 이력 - 모든 FIRING/RESOLVED 누적 [신규]
│       ├── alert_active.log          # ⭐ 활성 알람 - 미해소 알람만 (해소 시 삭제) [신규]
│       ├── alert_state/              # ⭐ 컨테이너별 상태 추적 [신규]
│       │   ├── sdc-open-webui.state
│       │   ├── sdc-redis-dev.state
│       │   ├── sdc-pipelines.state
│       │   ├── sdc-guardrails.state
│       │   └── sdc-monitoring.state
│       ├── watchdog.log              # 워치독 재시작 이력
│       ├── remote_health.log         # 원격 헬스체크 이력
│       ├── remote_restart.log        # 원격 재시작 이력
│       ├── cooldown/                 # 재시작 쿨다운 추적
│       └── suppress/                 # 자동 재시작 방지 설정
│
├── [시작/종료 스크립트]
│   ├── podman-run-monitoring.sh      # Prometheus + Grafana 시작 (Podman)
│   ├── podman-stop-monitoring.sh     # Prometheus + Grafana 종료
│   ├── start-monitoring.sh           # docker-compose 시작
│   └── stop-monitoring.sh            # docker-compose 종료
│
├── [데이터 (볼륨)]
│   ├── prometheus-data/              # Prometheus TSDB 데이터
│   └── grafana-data/                 # Grafana 데이터 + 플러그인
│
└── [문서]
    ├── README.md                     # 모니터링 개요
    ├── WATCHDOG_GUIDE.md             # 워치독 운영 가이드
    └── MONITORING_SETUP_GUIDE.md     # 설치 가이드
```

---

## 4. cron 등록 현황

```bash
# 현재 등록된 cron 항목 확인
crontab -l
```

| 스크립트 | 스케줄 | 주기 |
|---------|--------|------|
| `podman_metrics.sh` | `* * * * *` | 매 1분 |
| `podman_metrics.sh` (30초 오프셋) | `* * * * * sleep 30 &&` | 매 1분 (30초 뒤) |
| `alert_logger.sh` | `* * * * *` | 매 1분 |
| `podman_watchdog.sh` | `*/2 * * * *` | 매 2분 |
| `remote_health_check.sh` | `*/5 * * * *` | 매 5분 |

---

## 5. 알람 발생 ~ 해소 전체 흐름

### 5.1 컨테이너 중지 시 (알람 발생)

```
① 컨테이너 중지 (예: sdc-pipelines exited)
    ↓
② podman_metrics.sh (1분 이내)
   → podman_containers.prom: podman_container_running{name="sdc-pipelines"} 0
    ↓
③ alert_logger.sh (1분 이내)
   → alert.log:        [FIRING] [critical] sdc-pipelines - 컨테이너 중지 감지
   → alert_active.log: [FIRING] [critical] sdc-pipelines - 상태: exited (미해소)
   → podman_alerts.prom: podman_alert_firing{name="sdc-pipelines"} 1
    ↓
④ Node Exporter → Prometheus 수집 (15초)
   → Grafana 대시보드에 알람 표시
    ↓
⑤ Prometheus 알림 규칙 평가 (15초)
   → PodmanContainerDown 알림 firing (1분 대기 후)
   → CriticalContainerDown 알림 firing (30초 대기 후, 핵심 컨테이너인 경우)
    ↓
⑥ Alertmanager → 이메일 발송 (설정된 경우)
    ↓
⑦ podman_watchdog.sh (2분 이내)
   → 자동 재시작 시도 (suppress 아닌 경우)
   → watchdog.log: AUTO-RESTART: sdc-pipelines 재시작 성공
```

### 5.2 컨테이너 복구 시 (알람 해소)

```
① 컨테이너 재시작 (watchdog 자동 또는 수동)
    ↓
② alert_logger.sh (1분 이내)
   → alert.log:        [RESOLVED] [info] sdc-pipelines - 컨테이너 복구됨
   → alert_active.log: (해당 줄 삭제 → 파일이 비어있으면 모든 알람 해소)
   → podman_alerts.prom: podman_alert_firing{name="sdc-pipelines"} 0
    ↓
③ Grafana 대시보드에서 알람 사라짐
④ Alertmanager → 해소 이메일 발송 (send_resolved: true)
```

---

## 6. 운영자 확인 명령어

### 6.1 알람 확인
```bash
# 현재 활성(미해소) 알람 확인
cat /home/chatpro/monitoring/logs/alert_active.log

# 전체 알람 이력 확인 (최근 20건)
tail -20 /home/chatpro/monitoring/logs/alert.log

# Prometheus 메트릭으로 알람 상태 확인
cat /home/chatpro/monitoring/node-exporter/textfile/podman_alerts.prom | grep firing
```

### 6.2 컨테이너 상태 확인
```bash
# 전체 감시 대상 컨테이너 상태
/home/chatpro/monitoring/setup-watchdog-cron.sh list

# 전체 시스템 상태 (cron, 로그, 컨테이너)
/home/chatpro/monitoring/setup-watchdog-cron.sh status

# 현재 컨테이너 메트릭 확인
cat /home/chatpro/monitoring/node-exporter/textfile/podman_containers.prom
```

### 6.3 로그 확인
```bash
# 워치독 자동 재시작 이력
tail -20 /home/chatpro/monitoring/logs/watchdog.log

# 원격 헬스체크 이력
tail -20 /home/chatpro/monitoring/logs/remote_health.log
```

### 6.4 서비스 관리
```bash
# 모니터링 서비스 시작
/home/chatpro/monitoring/podman-run-monitoring.sh

# 모니터링 서비스 중지
/home/chatpro/monitoring/podman-stop-monitoring.sh

# cron 전체 설치
/home/chatpro/monitoring/setup-watchdog-cron.sh install

# 감시 대상 컨테이너 추가
/home/chatpro/monitoring/setup-watchdog-cron.sh add dify-api

# 자동 재시작 방지 (수동 점검 시)
/home/chatpro/monitoring/setup-watchdog-cron.sh suppress sdc-pipelines

# 자동 재시작 방지 해제
/home/chatpro/monitoring/setup-watchdog-cron.sh unsuppress sdc-pipelines
```

---

## 7. [2026-02-26] 이번 변경 사항 요약

### 7.1 신규 생성 파일
| 파일 | 설명 |
|------|------|
| `alert_logger.sh` | 컨테이너 알람 감지 + 로그 기록 + Prometheus 메트릭 생성 |

### 7.2 수정 파일
| 파일 | 수정 내용 |
|------|-----------|
| `setup-watchdog-cron.sh` | alert_logger cron 등록/상태확인/제거 추가, 동일 설정 재등록 방지 |

### 7.3 신규 생성 로그/메트릭 파일
| 파일 | 설명 |
|------|------|
| `logs/alert.log` | 알람 이력 (FIRING/RESOLVED 누적) |
| `logs/alert_active.log` | 활성 알람만 (미해소 알람, 해소 시 삭제) |
| `logs/alert_state/*.state` | 컨테이너별 이전 상태 추적 |
| `node-exporter/textfile/podman_alerts.prom` | 알람 Prometheus 메트릭 |

---

## 8. 패키지 파일 목록

```
0226.alarm.tar.gz
├── 0226_ALARM_MONITORING_GUIDE.md              # 본 운영 가이드
├── monitoring/alert_logger.sh                  # ⭐ 알람 로그 스크립트 (신규)
└── monitoring/setup-watchdog-cron.sh           # ⭐ cron 관리 스크립트 (수정)
```

---

## 9. 배포 순서

### Step 1: 파일 배포
```bash
cd /home/chatpro
tar xzf 0226.alarm.tar.gz
```

### Step 2: 실행 권한 부여
```bash
chmod +x /home/chatpro/monitoring/alert_logger.sh
```

### Step 3: cron 등록
```bash
/home/chatpro/monitoring/setup-watchdog-cron.sh install
```

### Step 4: 검증
```bash
# 수동 실행 테스트
/home/chatpro/monitoring/alert_logger.sh

# 로그 확인
cat /home/chatpro/monitoring/logs/alert_active.log
cat /home/chatpro/monitoring/node-exporter/textfile/podman_alerts.prom

# 상태 확인
/home/chatpro/monitoring/setup-watchdog-cron.sh status
```
