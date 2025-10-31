/**
 * RAG Search System 통합 유틸리티
 * Open WebUI 채팅과 RAG 시스템 연동
 */

import { searchRAG, enhanceMessageWithRAG, checkRAGHealth, type SearchResult } from '$lib/apis/rag-search';

/**
 * RAG 시스템 사용 가능 여부 확인
 */
let ragAvailable = false;
let lastHealthCheck = 0;
const HEALTH_CHECK_INTERVAL = 60000; // 1분

export const isRAGAvailable = async (): Promise<boolean> => {
	const now = Date.now();

	// 최근에 체크했으면 캐시된 값 반환
	if (now - lastHealthCheck < HEALTH_CHECK_INTERVAL) {
		return ragAvailable;
	}

	try {
		await checkRAGHealth();
		ragAvailable = true;
		lastHealthCheck = now;
		return true;
	} catch (err) {
		console.warn('RAG System not available:', err);
		ragAvailable = false;
		lastHealthCheck = now;
		return false;
	}
};

/**
 * 채팅 메시지에 RAG 검색 결과 추가
 * @param message 사용자 메시지
 * @param options 검색 옵션
 * @returns 향상된 메시지와 출처
 */
export interface RAGEnhancementOptions {
	enabled?: boolean; // RAG 사용 여부 (기본: true)
	level?: 1 | 2 | 3; // 검색 레벨 (기본: 2)
	topK?: number; // 검색 결과 수 (기본: 5)
	dataType?: 'term' | 'policy' | 'ithelp' | 'edm' | null;
	includeInMessage?: boolean; // 메시지에 직접 포함 여부 (기본: true)
}

export interface EnhancedChatMessage {
	originalMessage: string;
	enhancedMessage: string;
	sources: SearchResult[];
	ragUsed: boolean;
}

export const enhanceChatMessage = async (
	message: string,
	options: RAGEnhancementOptions = {}
): Promise<EnhancedChatMessage> => {
	const {
		enabled = true,
		level = 2,
		topK = 5,
		dataType = null,
		includeInMessage = true
	} = options;

	// RAG 비활성화 또는 사용 불가능
	if (!enabled || !(await isRAGAvailable())) {
		return {
			originalMessage: message,
			enhancedMessage: message,
			sources: [],
			ragUsed: false
		};
	}

	try {
		const result = await enhanceMessageWithRAG(message, level, topK);

		return {
			originalMessage: message,
			enhancedMessage: includeInMessage ? result.enhancedMessage : message,
			sources: result.sources,
			ragUsed: result.sources.length > 0
		};
	} catch (err) {
		console.error('RAG Enhancement failed:', err);
		return {
			originalMessage: message,
			enhancedMessage: message,
			sources: [],
			ragUsed: false
		};
	}
};

/**
 * 출처 정보를 포맷팅
 * @param sources 검색 결과
 * @returns 포맷된 출처 목록
 */
export const formatSources = (sources: SearchResult[]): string => {
	if (sources.length === 0) {
		return '';
	}

	return sources
		.map((source, idx) => {
			const score = source.final_score || source.score;
			return `${idx + 1}. [${source.doc_id}] (관련도: ${(score * 100).toFixed(1)}%)
   ${source.text.substring(0, 150)}${source.text.length > 150 ? '...' : ''}`;
		})
		.join('\n\n');
};

/**
 * RAG 검색 레벨별 설명
 */
export const RAG_LEVEL_DESCRIPTIONS = {
	1: {
		name: '빠른 검색',
		description: '기본 벡터 검색 (정확도: 70%, 속도: ~50ms)',
		icon: '⚡'
	},
	2: {
		name: '균형 검색',
		description: '하이브리드 검색 (정확도: 80%, 속도: ~200ms)',
		icon: '⚖️'
	},
	3: {
		name: '정밀 검색',
		description: '고급 RAG 검색 (정확도: 90-95%, 속도: ~1초)',
		icon: '🎯'
	}
} as const;

/**
 * 데이터 타입별 설명
 */
export const DATA_TYPE_DESCRIPTIONS = {
	term: {
		name: '용어사전',
		description: '기술 용어, 약어, 정의',
		icon: '📖'
	},
	policy: {
		name: '회사사규',
		description: '규정, 정책, 절차',
		icon: '📋'
	},
	ithelp: {
		name: 'IT Help Desk',
		description: '기술 지원, 문제 해결',
		icon: '🛠️'
	},
	edm: {
		name: 'EDM 문서',
		description: '특허, 기술 문서',
		icon: '📄'
	}
} as const;

/**
 * RAG 설정을 로컬 스토리지에 저장/로드
 */
export const saveRAGSettings = (settings: RAGEnhancementOptions): void => {
	try {
		localStorage.setItem('rag_settings', JSON.stringify(settings));
	} catch (err) {
		console.error('Failed to save RAG settings:', err);
	}
};

export const loadRAGSettings = (): RAGEnhancementOptions => {
	try {
		const saved = localStorage.getItem('rag_settings');
		if (saved) {
			return JSON.parse(saved);
		}
	} catch (err) {
		console.error('Failed to load RAG settings:', err);
	}

	// 기본값
	return {
		enabled: true,
		level: 2,
		topK: 5,
		dataType: null,
		includeInMessage: true
	};
};

/**
 * 간단한 RAG 검색 (UI에서 직접 사용)
 * @param query 검색 쿼리
 * @param level 검색 레벨
 * @returns 검색 결과
 */
export const quickRAGSearch = async (
	query: string,
	level: 1 | 2 | 3 = 2
): Promise<SearchResult[]> => {
	try {
		const response = await searchRAG({
			query,
			level,
			top_k: 10
		});
		return response.results;
	} catch (err) {
		console.error('Quick RAG search failed:', err);
		return [];
	}
};
