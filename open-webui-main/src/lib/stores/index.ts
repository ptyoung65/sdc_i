import { APP_NAME } from '$lib/constants';
import { type Writable, writable } from 'svelte/store';
import type { ModelConfig } from '$lib/apis';
import type { Banner } from '$lib/types';
import type { Socket } from 'socket.io-client';

import emojiShortCodes from '$lib/emoji-shortcodes.json';

// Backend
export const WEBUI_NAME = writable(APP_NAME);
export const config: Writable<Config | undefined> = writable(undefined);
export const user: Writable<SessionUser | undefined> = writable(undefined);

// Electron App
export const isApp = writable(false);
export const appInfo = writable(null);
export const appData = writable(null);

// Frontend
export const MODEL_DOWNLOAD_POOL = writable({});

export const mobile = writable(false);

export const socket: Writable<null | Socket> = writable(null);
export const activeUserIds: Writable<null | string[]> = writable(null);
export const USAGE_POOL: Writable<null | string[]> = writable(null);

export const theme = writable('system');

export const shortCodesToEmojis = writable(
	Object.entries(emojiShortCodes).reduce((acc, [key, value]) => {
		if (typeof value === 'string') {
			acc[value] = key;
		} else {
			for (const v of value) {
				acc[v] = key;
			}
		}

		return acc;
	}, {})
);

export const TTSWorker = writable(null);

export const chatId = writable('');
export const chatTitle = writable('');

export const channels = writable([]);
export const chats = writable(null);
export const pinnedChats = writable([]);
export const tags = writable([]);
export const folders = writable([]);

export const selectedFolder = writable(null);

export const models: Writable<Model[]> = writable([]);

export const prompts: Writable<null | Prompt[]> = writable(null);
export const knowledge: Writable<null | Document[]> = writable(null);
export const tools = writable(null);
export const functions = writable(null);

export const toolServers = writable([]);

export const banners: Writable<Banner[]> = writable([]);

export const settings: Writable<Settings> = writable({});

export const showSidebar = writable(true);
export const showRightSidebar = writable(false);
export const showSearch = writable(false);
export const showSettings = writable(false);
export const showShortcuts = writable(false);
export const showArchivedChats = writable(false);
export const showChangelog = writable(false);

export const showControls = writable(true);
export const showEmbeds = writable(false);
export const showOverview = writable(false);
export const showArtifacts = writable(false);
export const showCallOverlay = writable(false);

export const embed = writable(null);
export const artifactCode = writable(null);

export const temporaryChatEnabled = writable(false);
export const scrollPaginationEnabled = writable(false);
export const currentChatPage = writable(1);

export const modelType = writable<'internal' | 'external'>('internal');

export const isLastActiveTab = writable(true);
export const playingNotificationSound = writable(false);

// ============================================================================
// [2026.01.28] 메시지 입력창 초기화 트리거 Store
// ============================================================================
// 목적: 새 세션 이동, 홈화면 이동, 사이드바 항목 클릭 시 메시지 입력창 내용을 초기화
//
// 사용 방법:
// - 초기화가 필요한 곳에서: clearMessageInput.update(n => n + 1)
// - Chat.svelte에서 구독하여 값 변경 시 messageInput?.setText("") 호출
//
// 사용 위치:
// - src/lib/components/layout/Sidebar.svelte: 새 채팅 아이콘, 홈 이동 아이콘 클릭 시
// - src/lib/components/layout/RightSidebar.svelte: 카테고리 항목 클릭 시
// - src/lib/components/chat/Chat.svelte: 트리거 구독 및 입력창 초기화 실행
// ============================================================================
export const clearMessageInput = writable(0);
// ----- [2026.01.28] 메시지 입력창 초기화 트리거 Store 종료 -----

// ============================================================================
// [2026.01.07] 도움말 이미지 뷰어 관련 Store
// ============================================================================
// 목적: 관리자가 설정한 도움말 이미지 폴더의 이미지를 순서대로 보여주는 기능
//
// 주요 기능:
// 1. 도움말 이미지 폴더 경로 관리
// 2. 도움말 모달 표시 상태 관리
// 3. 현재 보고 있는 이미지 인덱스 관리
//
// 사용 위치:
// - src/lib/components/chat/Navbar.svelte: ? 아이콘 및 모달 표시
// - src/lib/components/admin/Settings/General.svelte: 폴더 경로 설정
// ============================================================================

// ----- [2026.01.07] 도움말 폴더 경로 -----
// 관리자 설정에서 지정한 도움말 이미지 폴더 경로
export const helpImageFolder = writable('/static/help');

// ----- [2026.01.07] 도움말 모달 표시 상태 -----
export const showHelpModal = writable(false);

// ----- [2026.01.07] 도움말 이미지 목록 -----
export const helpImages: Writable<string[]> = writable([]);

// ----- [2026.01.07] 현재 이미지 인덱스 -----
export const currentHelpImageIndex = writable(0);
// ----- [2026.01.07] 도움말 이미지 뷰어 관련 Store 종료 -----

// ============================================================================
// [2025.01.05] 외부 서버 연결 상태 관리 Store
// ============================================================================
// 목적: 외부 LLM, 임베딩, 파서, 청크 서버의 연결 상태를 실시간으로 추적하여
//       네비게이션 바에 시각적으로 표시
//
// 주요 기능:
// 1. 서버 타입별 분류 (파서, 청크, 임베더, LLM)
// 2. 연결 상태 추적 (connected, connecting, timeout, error, unknown)
// 3. 응답 시간 측정 및 에러 메시지 저장
// 4. 전체 연결 상태 요약 제공
//
// 사용 위치:
// - src/routes/(app)/+layout.svelte: 서버 상태 업데이트 호출
// - src/lib/components/layout/ServerStatusIndicator.svelte: UI 표시
// - src/lib/components/chat/Navbar.svelte: 인디케이터 컴포넌트 배치
// ============================================================================

// ----- [2025.01.05] 서버 타입 정의 -----
// 외부 서버를 4가지 타입으로 분류
// - parser: 문서 파싱 서버 (PDF, DOCX 등 문서 변환)
// - chunker: 텍스트 청킹 서버 (문서를 작은 단위로 분할)
// - embedder: 임베딩 서버 (텍스트를 벡터로 변환)
// - llm: LLM 서버 (대화형 AI 모델)
export type ExternalServerType = 'parser' | 'chunker' | 'embedder' | 'llm';

// ----- [2025.01.05] 서버 상태 타입 정의 -----
// 각 외부 서버의 연결 상태 정보를 저장하는 타입
export type ExternalServerStatus = {
	name: string;           // 서버 표시 이름 (예: "Parser Server", "LLM Server")
	url: string;            // 서버 URL (고유 식별자로 사용)
	type: ExternalServerType; // 서버 타입 (파서, 청크, 임베더, LLM)
	status: 'connected' | 'connecting' | 'timeout' | 'error' | 'unknown';
	                        // 연결 상태:
	                        // - connected: 정상 연결
	                        // - connecting: 연결 시도 중
	                        // - timeout: 연결 시간 초과 (5초)
	                        // - error: 연결 에러
	                        // - unknown: 상태 불명
	lastCheck: number;      // 마지막 상태 확인 시간 (Unix timestamp)
	responseTime?: number;  // 응답 시간 (밀리초, 성공 시에만)
	errorMessage?: string;  // 에러 메시지 (실패 시에만)
};

// ----- [2025.01.05] 서버 타입별 한글 라벨 -----
// UI에 표시할 한글 라벨 매핑
export const serverTypeLabels: Record<ExternalServerType, string> = {
	parser: '파서',      // 문서 파싱
	chunker: '청크',     // 텍스트 분할
	embedder: '임베더',  // 벡터 변환
	llm: 'LLM'          // 언어 모델
};

// ----- [2025.01.05] 서버 타입별 아이콘 -----
// 네비바 및 드롭다운에 표시할 이모지 아이콘
export const serverTypeIcons: Record<ExternalServerType, string> = {
	parser: '📄',    // 문서 아이콘
	chunker: '✂️',   // 가위 아이콘 (분할)
	embedder: '🔢',  // 숫자 아이콘 (벡터)
	llm: '🤖'        // 로봇 아이콘 (AI)
};

// ----- [2025.01.05] 외부 서버 상태 Store -----
// 모든 외부 서버의 연결 상태를 배열로 관리하는 Svelte Store
// ServerStatusIndicator 컴포넌트에서 구독하여 UI에 표시
export const externalServerStatus: Writable<ExternalServerStatus[]> = writable([]);

// ----- [2025.01.05] 서버 상태 업데이트 함수 -----
// 특정 서버의 연결 상태를 업데이트하는 헬퍼 함수
// @param url - 서버 URL (고유 식별자)
// @param status - 새로운 연결 상태
// @param options - 추가 옵션 (이름, 타입, 응답시간, 에러메시지)
export const updateServerStatus = (
	url: string,
	status: ExternalServerStatus['status'],
	options?: { name?: string; type?: ExternalServerType; responseTime?: number; errorMessage?: string }
) => {
	externalServerStatus.update(servers => {
		// 기존 서버 찾기
		const existingIndex = servers.findIndex(s => s.url === url);
		const existingServer = existingIndex >= 0 ? servers[existingIndex] : null;

		// 새 상태 객체 생성 (기존 값 유지 또는 새 값 적용)
		const newStatus: ExternalServerStatus = {
			name: options?.name || existingServer?.name || url,
			url,
			type: options?.type || existingServer?.type || 'llm', // 기본값은 llm
			status,
			lastCheck: Date.now(),
			responseTime: options?.responseTime,
			errorMessage: options?.errorMessage
		};

		// 기존 서버 업데이트 또는 새 서버 추가
		if (existingIndex >= 0) {
			servers[existingIndex] = newStatus;
		} else {
			servers.push(newStatus);
		}
		return [...servers]; // 불변성 유지를 위해 새 배열 반환
	});
};

// ----- [2025.01.05] 서버 상태 제거 함수 -----
// 특정 서버를 상태 목록에서 제거
// @param url - 제거할 서버의 URL
export const removeServerStatus = (url: string) => {
	externalServerStatus.update(servers => servers.filter(s => s.url !== url));
};

// ----- [2025.01.05] 연결 상태 요약 함수 -----
// 전체 서버의 연결 상태를 요약하여 반환
// @param servers - 서버 상태 배열
// @returns { total, connected, connecting, failed } 카운트
export const getConnectionSummary = (servers: ExternalServerStatus[]) => {
	const total = servers.length;
	const connected = servers.filter(s => s.status === 'connected').length;
	const connecting = servers.filter(s => s.status === 'connecting').length;
	const failed = servers.filter(s => s.status === 'timeout' || s.status === 'error').length;

	return { total, connected, connecting, failed };
};
// ----- [2025.01.05] 외부 서버 연결 상태 관리 store 종료 -----

export type Model = OpenAIModel | OllamaModel;

type BaseModel = {
	id: string;
	name: string;
	info?: ModelConfig;
	owned_by: 'ollama' | 'openai' | 'arena';
};

export interface OpenAIModel extends BaseModel {
	owned_by: 'openai';
	external: boolean;
	source?: string;
}

export interface OllamaModel extends BaseModel {
	owned_by: 'ollama';
	details: OllamaModelDetails;
	size: number;
	description: string;
	model: string;
	modified_at: string;
	digest: string;
	ollama?: {
		name?: string;
		model?: string;
		modified_at: string;
		size?: number;
		digest?: string;
		details?: {
			parent_model?: string;
			format?: string;
			family?: string;
			families?: string[];
			parameter_size?: string;
			quantization_level?: string;
		};
		urls?: number[];
	};
}

type OllamaModelDetails = {
	parent_model: string;
	format: string;
	family: string;
	families: string[] | null;
	parameter_size: string;
	quantization_level: string;
};

type Settings = {
	pinnedModels?: never[];
	toolServers?: never[];
	detectArtifacts?: boolean;
	showUpdateToast?: boolean;
	showChangelog?: boolean;
	showEmojiInCall?: boolean;
	voiceInterruption?: boolean;
	collapseCodeBlocks?: boolean;
	expandDetails?: boolean;
	notificationSound?: boolean;
	notificationSoundAlways?: boolean;
	stylizedPdfExport?: boolean;
	notifications?: any;
	imageCompression?: boolean;
	imageCompressionSize?: any;
	widescreenMode?: null;
	largeTextAsFile?: boolean;
	promptAutocomplete?: boolean;
	hapticFeedback?: boolean;
	responseAutoCopy?: any;
	richTextInput?: boolean;
	params?: any;
	userLocation?: any;
	webSearch?: any;
	memory?: boolean;
	autoTags?: boolean;
	autoFollowUps?: boolean;
	splitLargeChunks?(body: any, splitLargeChunks: any): unknown;
	backgroundImageUrl?: null;
	landingPageMode?: string;
	iframeSandboxAllowForms?: boolean;
	iframeSandboxAllowSameOrigin?: boolean;
	scrollOnBranchChange?: boolean;
	directConnections?: null;
	chatBubble?: boolean;
	copyFormatted?: boolean;
	models?: string[];
	conversationMode?: boolean;
	speechAutoSend?: boolean;
	responseAutoPlayback?: boolean;
	audio?: AudioSettings;
	showUsername?: boolean;
	notificationEnabled?: boolean;
	highContrastMode?: boolean;
	title?: TitleSettings;
	showChatTitleInTab?: boolean;
	splitLargeDeltas?: boolean;
	chatDirection?: 'LTR' | 'RTL' | 'auto';
	ctrlEnterToSend?: boolean;
	showDetailedRating?: boolean;

	system?: string;
	seed?: number;
	temperature?: string;
	repeat_penalty?: string;
	top_k?: string;
	top_p?: string;
	num_ctx?: string;
	num_batch?: string;
	num_keep?: string;
	options?: ModelOptions;
};

type ModelOptions = {
	stop?: boolean;
};

type AudioSettings = {
	stt: any;
	tts: any;
	STTEngine?: string;
	TTSEngine?: string;
	speaker?: string;
	model?: string;
	nonLocalVoices?: boolean;
};

type TitleSettings = {
	auto?: boolean;
	model?: string;
	modelExternal?: string;
	prompt?: string;
};

type Prompt = {
	command: string;
	user_id: string;
	title: string;
	content: string;
	timestamp: number;
};

type Document = {
	collection_name: string;
	filename: string;
	name: string;
	title: string;
};

type Config = {
	license_metadata: any;
	status: boolean;
	name: string;
	version: string;
	default_locale: string;
	default_models: string;
	default_prompt_suggestions: PromptSuggestion[];
	// 기본 모델 설정 (PostgreSQL에서 로드)
	default_internal_model?: string;
	default_external_model?: string;
	features: {
		auth: boolean;
		auth_trusted_header: boolean;
		enable_api_key: boolean;
		enable_signup: boolean;
		enable_login_form: boolean;
		enable_web_search?: boolean;
		enable_google_drive_integration: boolean;
		enable_onedrive_integration: boolean;
		enable_image_generation: boolean;
		enable_admin_export: boolean;
		enable_admin_chat_access: boolean;
		enable_community_sharing: boolean;
		enable_autocomplete_generation: boolean;
		enable_direct_connections: boolean;
		enable_version_update_check: boolean;
	};
	oauth: {
		providers: {
			[key: string]: string;
		};
	};
	ui?: {
		pending_user_overlay_title?: string;
		pending_user_overlay_description?: string;
	};
};

type PromptSuggestion = {
	content: string;
	title: [string, string];
};

export type SessionUser = {
	permissions: any;
	id: string;
	email: string;
	name: string;
	role: string;
	profile_image_url: string;
};

// ============================================================================
// [2026.01.19] 모델별 색상 설정 Store
// ============================================================================
// 목적: 채팅 화면에서 모델명을 색상으로 구분하여 표시
//
// 사용 위치:
// - src/lib/components/chat/Messages/ResponseMessage.svelte: 모델명 색상 표시
// - src/lib/components/admin/Settings/Models.svelte: 모델 색상 설정 UI
// ============================================================================

// ----- [2026.01.19] 모델 색상 매핑 타입 정의 -----
export type ModelColorMapping = {
	keyword: string;        // 모델명에 포함된 키워드 (예: 'gpt', 'claude')
	color: string;          // Tailwind 색상 클래스 (예: 'emerald', 'orange')
	label: string;          // 표시 라벨 (예: 'GPT 계열', 'Claude 계열')
};

// ----- [2026.01.19] 기본 모델 색상 매핑 -----
export const DEFAULT_MODEL_COLORS: ModelColorMapping[] = [
	{ keyword: 'gpt', color: 'emerald', label: 'GPT (OpenAI)' },
	{ keyword: 'openai', color: 'emerald', label: 'OpenAI' },
	{ keyword: 'claude', color: 'orange', label: 'Claude (Anthropic)' },
	{ keyword: 'anthropic', color: 'orange', label: 'Anthropic' },
	{ keyword: 'gemini', color: 'blue', label: 'Gemini (Google)' },
	{ keyword: 'google', color: 'blue', label: 'Google' },
	{ keyword: 'llama', color: 'purple', label: 'Llama (Meta)' },
	{ keyword: 'meta', color: 'purple', label: 'Meta' },
	{ keyword: 'mistral', color: 'yellow', label: 'Mistral' },
	{ keyword: 'mixtral', color: 'yellow', label: 'Mixtral' },
	{ keyword: 'qwen', color: 'indigo', label: 'Qwen (Alibaba)' },
	{ keyword: 'deepseek', color: 'pink', label: 'DeepSeek' },
	{ keyword: 'phi', color: 'teal', label: 'Phi (Microsoft)' },
	{ keyword: 'solar', color: 'red', label: 'Solar (Upstage)' },
	{ keyword: 'ollama', color: 'cyan', label: 'Ollama' },
];

// ----- [2026.01.19] 사용 가능한 색상 목록 -----
export const AVAILABLE_COLORS = [
	{ value: 'emerald', label: '녹색 (Emerald)', light: 'text-emerald-600', dark: 'text-emerald-400' },
	{ value: 'orange', label: '주황색 (Orange)', light: 'text-orange-600', dark: 'text-orange-400' },
	{ value: 'blue', label: '파란색 (Blue)', light: 'text-blue-600', dark: 'text-blue-400' },
	{ value: 'purple', label: '보라색 (Purple)', light: 'text-purple-600', dark: 'text-purple-400' },
	{ value: 'yellow', label: '노란색 (Yellow)', light: 'text-yellow-600', dark: 'text-yellow-400' },
	{ value: 'cyan', label: '청록색 (Cyan)', light: 'text-cyan-600', dark: 'text-cyan-400' },
	{ value: 'red', label: '빨간색 (Red)', light: 'text-red-600', dark: 'text-red-400' },
	{ value: 'pink', label: '분홍색 (Pink)', light: 'text-pink-600', dark: 'text-pink-400' },
	{ value: 'indigo', label: '남색 (Indigo)', light: 'text-indigo-600', dark: 'text-indigo-400' },
	{ value: 'teal', label: '틸색 (Teal)', light: 'text-teal-600', dark: 'text-teal-400' },
	{ value: 'gray', label: '회색 (Gray)', light: 'text-gray-700', dark: 'text-gray-300' },
];

// ----- [2026.01.19] 모델 색상 설정 Store -----
export const modelColors: Writable<ModelColorMapping[]> = writable(DEFAULT_MODEL_COLORS);

// ----- [2026.01.19] 색상 클래스 변환 함수 -----
// 색상 이름을 Tailwind CSS 클래스로 변환
export const getColorClass = (colorName: string): string => {
	const colorMap = AVAILABLE_COLORS.find(c => c.value === colorName);
	if (colorMap) {
		return `${colorMap.light} dark:${colorMap.dark}`;
	}
	// 기본값: 회색
	return 'text-gray-700 dark:text-gray-300';
};

// ----- [2026.01.19] 모델명으로 색상 클래스 가져오기 -----
export const getModelColorClass = (modelName: string, colors: ModelColorMapping[]): string => {
	const name = (modelName || '').toLowerCase();

	for (const mapping of colors) {
		if (name.includes(mapping.keyword.toLowerCase())) {
			return getColorClass(mapping.color);
		}
	}

	// 매칭되지 않으면 기본 회색
	return 'text-gray-700 dark:text-gray-300';
};
// ----- [2026.01.19] 모델별 색상 설정 Store 종료 -----
