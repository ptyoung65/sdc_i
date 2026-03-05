import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
import type { Banner } from '$lib/types';

export const importConfig = async (token: string, config) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/import`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			config: config
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// ----- [2026-03-02] updateConfigPartial MAX_POPUP_COUNT 저장 확인 시작 -----
// ■ 확인: exportConfig(token)로 현재 설정 조회 → partialConfig 병합 → importConfig로 저장
// ■ importConfig → POST /configs/import → get_admin_user (관리자만 저장 가능)
// ■ Notification.svelte savePopupCount()에서 { MAX_POPUP_COUNT: N } 전달
// ----- [2026-03-02] updateConfigPartial MAX_POPUP_COUNT 저장 확인 종료 -----
export const updateConfigPartial = async (token: string, partialConfig: object) => {
	let error = null;

	// First get current config
	const currentConfig = await exportConfig(token);

	// ----- [2026-02-02] 설정 초기화 방지: exportConfig 실패 시 저장 중단 -----
	// exportConfig가 실패하면 (401 에러 등) currentConfig가 null이 되어
	// 기존 설정이 모두 초기화되는 문제 방지
	if (!currentConfig) {
		console.error('[updateConfigPartial] Failed to get current config, aborting save to prevent data loss');
		throw 'Failed to get current config. Please refresh the page and try again.';
	}
	// ----- [2026-02-02] 설정 초기화 방지 종료 -----

	// Merge with partial config
	const newConfig = {
		...currentConfig,
		...partialConfig
	};

	// Save using import endpoint
	const res = await importConfig(token, newConfig);

	if (!res) {
		error = 'Failed to update config';
	}

	if (error) {
		throw error;
	}

	return res;
};

// ----- [2026-03-02] exportConfig 팝업 개수 조회 확인 시작 -----
// ■ 확인: GET /configs/export → 백엔드 get_verified_user → 관리자/일반사용자 모두 접근 가능
// ■ 반환값에 MAX_POPUP_COUNT 포함 → +layout.svelte loadPopupAnnouncements()에서 사용
// ■ API 테스트: 관리자(200), 일반사용자(200) 동일 결과 확인 완료
// ----- [2026-03-02] exportConfig 팝업 개수 조회 확인 종료 -----
export const exportConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/export`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// ============================================================================================================
// ----- [2026-01-31] 사용자용 모델 설정 조회 API 추가 시작 -----
// 보안 이슈 대응: exportConfig가 관리자 전용으로 변경됨에 따라
// 일반 사용자를 위한 새 API 함수 추가
// ============================================================================================================
// 관리자 전용 exportConfig, getModelsConfig 대신 일반 사용자는 이 API를 사용
// 반환 정보:
// - default_internal_model: 내부 기본 모델
// - default_external_model: 외부 기본 모델
// - MODEL_SESSION_LIMITS: 모델별 세션 제한 (턴/토큰 수)
// - DEFAULT_MODELS: 기본 모델 설정
// - MODEL_ORDER_LIST: 모델 표시 순서
export const getDefaultModelsConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/default-models`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
// ----- [2026-01-31] 사용자용 모델 설정 조회 API 추가 종료 -----
// ============================================================================================================

export const getConnectionsConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/connections`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setConnectionsConfig = async (token: string, config: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/connections`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...config
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getToolServerConnections = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/tool_servers`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setToolServerConnections = async (token: string, connections: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/tool_servers`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...connections
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const verifyToolServerConnection = async (token: string, connection: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/tool_servers/verify`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...connection
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type RegisterOAuthClientForm = {
	url: string;
	client_id: string;
	client_name?: string;
};

export const registerOAuthClient = async (
	token: string,
	formData: RegisterOAuthClientForm,
	type: null | string = null
) => {
	let error = null;

	const searchParams = type ? `?type=${type}` : '';
	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/oauth/clients/register${searchParams}`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...formData
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOAuthClientAuthorizationUrl = (clientId: string, type: null | string = null) => {
	const oauthClientId = type ? `${type}:${clientId}` : clientId;
	return `${WEBUI_BASE_URL}/oauth/clients/${oauthClientId}/authorize`;
};

export const getCodeExecutionConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/code_execution`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setCodeExecutionConfig = async (token: string, config: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/code_execution`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...config
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getJupyterPresets = () => {
	// 현재 접속 중인 서버 호스트명 (브라우저에서 자동 감지)
	// Open WebUI와 Jupyter가 동일한 서버에서 실행되므로 현재 호스트 사용
	const currentHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';

	return [
		{
			name: `⭐ Jupyter (${currentHost}) - 권장`,
			env: 'current',
			url: `http://${currentHost}:8888`,
			token: 'jupyter-dev-token-2025',
			auth: 'token',
			timeout: 60,
			description: 'Open WebUI와 동일한 서버 (자동 감지)',
			recommended: true
		},
		{
			name: 'Jupyter (localhost)',
			env: 'local',
			url: 'http://localhost:8888',
			token: 'jupyter-dev-token-2025',
			auth: 'token',
			timeout: 60,
			description: '로컬 개발 환경'
		}
	];
};

// ============================================================================================================
// [2025.01.05] 세션 제한 설정 조회 API 함수
// ============================================================================================================
//
// ■ 기능: config DB에서 모델 관련 설정(MODEL_SESSION_LIMITS 포함) 조회
//
// ■ 호출 흐름:
//   1. Models.svelte의 loadSessionLimits() 함수에서 호출
//   2. GET /api/v1/configs/models 엔드포인트로 요청
//   3. 백엔드 configs.py의 get_models_config() 함수 실행
//   4. config.py의 get_config()로 config 테이블에서 data 컬럼 조회
//   5. 응답으로 MODEL_SESSION_LIMITS 포함한 전체 설정 반환
//
// ■ 응답 데이터 구조:
//   {
//     "MODEL_SESSION_LIMITS": {
//       "모델ID": { maxTurns: 10, maxTokens: 50000, maxInputTokens: 4000, warningTurns: 2 }
//     },
//     "DEFAULT_MODELS": "...",
//     "MODEL_ORDER_LIST": [...]
//   }
//
// ■ DB 저장 위치: PostgreSQL config 테이블의 data 컬럼 (JSONB 타입)
//
// ----- [2025.01.05] 세션 제한 설정 조회 API 함수 시작 -----
export const getModelsConfig = async (token: string) => {
	let error = null;

	// GET /api/v1/configs/models → 백엔드 configs.py → config.py get_config()
	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/models`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`  // 관리자 인증 토큰 필수
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();  // MODEL_SESSION_LIMITS 포함된 설정 반환
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
// ----- [2025.01.05] 세션 제한 설정 조회 API 함수 종료 -----

// ============================================================================================================
// [2025.01.05] 세션 제한 설정 저장 API 함수
// ============================================================================================================
//
// ■ 기능: config DB에 모델 관련 설정(MODEL_SESSION_LIMITS 포함) 저장
//
// ■ 호출 흐름:
//   1. Models.svelte의 saveSessionLimits() 함수에서 호출
//   2. POST /api/v1/configs/models 엔드포인트로 요청
//   3. 백엔드 configs.py의 set_models_config() 함수 실행
//   4. config.py의 get_config()로 기존 설정 조회
//   5. MODEL_SESSION_LIMITS 키에 새 값 병합
//   6. config.py의 save_config() → save_to_db()로 DB 저장
//   7. PostgreSQL config 테이블의 data 컬럼 UPDATE
//
// ■ 요청 데이터 구조:
//   {
//     "MODEL_SESSION_LIMITS": {
//       "모델ID": { maxTurns: 10, maxTokens: 50000, maxInputTokens: 4000, warningTurns: 2 }
//     }
//   }
//
// ■ DB 저장 과정:
//   save_config() → save_to_db() → SQLAlchemy ORM → PostgreSQL UPDATE
//
// ■ 컨테이너 재시작: 불필요 (즉시 적용)
//
// ----- [2025.01.05] 세션 제한 설정 저장 API 함수 시작 -----
export const setModelsConfig = async (token: string, config: object) => {
	let error = null;

	// POST /api/v1/configs/models → 백엔드 configs.py → config.py save_config()
	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/models`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`  // 관리자 인증 토큰 필수
		},
		body: JSON.stringify({
			...config  // MODEL_SESSION_LIMITS 포함된 설정 객체
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();  // 저장 후 업데이트된 설정 반환
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
// ----- [2025.01.05] 세션 제한 설정 저장 API 함수 종료 -----

export const setDefaultPromptSuggestions = async (token: string, promptSuggestions: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/suggestions`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			suggestions: promptSuggestions
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getBanners = async (token: string): Promise<Banner[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/banners`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setBanners = async (token: string, banners: Banner[]) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/banners`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			banners: banners
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// ----- [2026.01.19] 클라이언트 IP 조회 API 함수 시작 -----
export const getClientIP = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/client-ip`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
// ----- [2026.01.19] 클라이언트 IP 조회 API 함수 종료 -----

// ============================================================================================================
// [2026.01.19] 모델 색상 설정 조회 API 함수
// ============================================================================================================
//
// ■ 기능: config DB에서 MODEL_COLORS 설정 조회
//
// ■ 사용 위치:
//   - src/routes/(app)/+layout.svelte: 앱 초기 로드 시 색상 설정 로드
//   - src/lib/components/admin/Settings/Models.svelte: 관리자 설정 UI
//
// ----- [2026.01.19] 모델 색상 설정 조회 API 함수 시작 -----
export const getModelColors = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/model-colors`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
// ----- [2026.01.19] 모델 색상 설정 조회 API 함수 종료 -----

// ============================================================================================================
// [2026.01.19] 모델 색상 설정 저장 API 함수
// ============================================================================================================
//
// ■ 기능: config DB에 MODEL_COLORS 설정 저장
//
// ■ 요청 데이터 구조:
//   {
//     "colors": [
//       { "keyword": "gpt", "color": "emerald", "label": "GPT (OpenAI)" },
//       { "keyword": "claude", "color": "orange", "label": "Claude" }
//     ]
//   }
//
// ----- [2026.01.19] 모델 색상 설정 저장 API 함수 시작 -----
export const setModelColors = async (token: string, colors: any[]) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/model-colors`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ colors })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
// ----- [2026.01.19] 모델 색상 설정 저장 API 함수 종료 -----

// ============================================================================================================
// [2026-01-31] Active-Active 캐시 동기화 API 함수
// ============================================================================================================
//
// ■ 기능: Active-Active 환경에서 설정 변경 후 모든 서버의 캐시 동기화
//
// ■ 사용 위치:
//   - src/lib/components/admin/Settings/Models.svelte: 세션 제한 저장 후 자동 호출
//
// ■ 환경변수 설정 필요:
//   CLUSTER_SERVER_URLS=http://192.168.122.178:8080,http://192.168.122.177:8080
//
// ----- [2026-01-31] 캐시 동기화 API 함수 시작 -----

/**
 * 현재 서버의 설정 캐시를 DB에서 다시 로드
 */
export const refreshConfigCache = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/refresh-cache`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * 모든 클러스터 서버의 설정 캐시를 동기화
 */
export const syncConfigToAllServers = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/sync-servers`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * 설정된 클러스터 서버 목록 조회
 */
export const getClusterServers = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/cluster-servers`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// ----- [2026-01-31] 캐시 동기화 API 함수 종료 -----
// ============================================================================================================
