/**
 * RAG Search System API
 * Milvus + PostgreSQL 기반 3단계 검색 시스템 연동
 */

// RAG Search System API Base URL
const RAG_SEARCH_API_BASE_URL = 'http://localhost:8013/api/v1';

export interface SearchRequest {
	query: string;
	level?: 1 | 2 | 3; // 검색 레벨 (기본: 2)
	top_k?: number; // 반환할 결과 수 (기본: 10)
	data_type?: 'term' | 'policy' | 'ithelp' | 'edm' | null;
	doc_ids?: string[] | null;
	filters?: Record<string, any> | null;
}

export interface SearchResult {
	doc_id: string;
	chunk_id: string;
	text: string;
	score: number;
	metadata?: Record<string, any>;
	rerank_score?: number;
	final_score?: number;
}

export interface SearchResponse {
	results: SearchResult[];
	total: number;
	level: number;
	query: string;
	processing_time_ms: number;
}

/**
 * RAG 검색 실행
 * @param request 검색 요청
 * @returns 검색 결과
 */
export const searchRAG = async (request: SearchRequest): Promise<SearchResponse> => {
	try {
		const res = await fetch(`${RAG_SEARCH_API_BASE_URL}/search`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				query: request.query,
				level: request.level || 2,
				top_k: request.top_k || 10,
				data_type: request.data_type || null,
				doc_ids: request.doc_ids || null,
				filters: request.filters || null
			})
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(error.detail || 'RAG 검색 실패');
		}

		return await res.json();
	} catch (err) {
		console.error('RAG Search Error:', err);
		throw err;
	}
};

/**
 * RAG 시스템 헬스 체크
 * @returns 시스템 상태
 */
export const checkRAGHealth = async (): Promise<{
	status: string;
	milvus: boolean;
	postgresql: boolean;
	timestamp: string;
}> => {
	try {
		const res = await fetch(`${RAG_SEARCH_API_BASE_URL.replace('/api/v1', '')}/health`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json'
			}
		});

		if (!res.ok) {
			throw new Error('RAG 시스템 연결 실패');
		}

		return await res.json();
	} catch (err) {
		console.error('RAG Health Check Error:', err);
		throw err;
	}
};

/**
 * RAG 설정 조회
 * @returns RAG 설정 정보
 */
export const getRAGSearchConfig = async (): Promise<{
	search_levels: number[];
	data_types: string[];
	default_level: number;
	default_top_k: number;
}> => {
	try {
		const res = await fetch(`${RAG_SEARCH_API_BASE_URL}/config`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json'
			}
		});

		if (!res.ok) {
			throw new Error('RAG 설정 조회 실패');
		}

		return await res.json();
	} catch (err) {
		console.error('RAG Config Error:', err);
		throw err;
	}
};

/**
 * 채팅 메시지에 RAG 컨텍스트 추가
 * @param userMessage 사용자 메시지
 * @param level 검색 레벨 (기본: 2)
 * @param topK 검색 결과 수 (기본: 5)
 * @returns RAG 컨텍스트가 추가된 메시지
 */
export const enhanceMessageWithRAG = async (
	userMessage: string,
	level: 1 | 2 | 3 = 2,
	topK: number = 5
): Promise<{
	enhancedMessage: string;
	sources: SearchResult[];
}> => {
	try {
		// RAG 검색 실행
		const searchResponse = await searchRAG({
			query: userMessage,
			level: level,
			top_k: topK
		});

		if (searchResponse.results.length === 0) {
			return {
				enhancedMessage: userMessage,
				sources: []
			};
		}

		// 검색 결과를 컨텍스트로 변환
		const context = searchResponse.results
			.map(
				(result, idx) =>
					`[출처 ${idx + 1}] (점수: ${result.score.toFixed(3)})\n${result.text}\n`
			)
			.join('\n---\n\n');

		// 메시지에 컨텍스트 추가
		const enhancedMessage = `다음은 관련 문서 검색 결과입니다. 이 정보를 참고하여 답변해주세요:

${context}

---

사용자 질문: ${userMessage}`;

		return {
			enhancedMessage,
			sources: searchResponse.results
		};
	} catch (err) {
		console.error('RAG Enhancement Error:', err);
		// 에러 발생 시 원본 메시지 반환
		return {
			enhancedMessage: userMessage,
			sources: []
		};
	}
};

/**
 * 데이터 타입별 검색
 * @param query 검색 쿼리
 * @param dataType 데이터 타입
 * @param level 검색 레벨
 * @returns 검색 결과
 */
export const searchByDataType = async (
	query: string,
	dataType: 'term' | 'policy' | 'ithelp' | 'edm',
	level: 1 | 2 | 3 = 2
): Promise<SearchResponse> => {
	return await searchRAG({
		query,
		level,
		data_type: dataType,
		top_k: 10
	});
};
