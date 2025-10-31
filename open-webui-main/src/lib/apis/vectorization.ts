/**
 * EDM Document Vectorization API
 *
 * 파일 다운로드, 벡터화, 유사도 검색 기능 제공
 */

const BACKEND_BASE_URL = '/api/v1';
const MILVUS_BASE_URL = import.meta.env.VITE_MILVUS_BASE_URL || 'http://localhost:19530';

/**
 * 벡터화 요청 인터페이스
 */
export interface VectorizationRequest {
	file_id: string;
	file_name: string;
	file_url?: string;
	file_content?: string;
	file_type: string;
	user_id?: string;
	chat_id?: string;
}

/**
 * 벡터화 응답 인터페이스
 */
export interface VectorizationResponse {
	success: boolean;
	message: string;
	doc_id?: string;
	chunks_count?: number;
	embeddings_count?: number;
	error?: string;
}

/**
 * 유사도 검색 요청 인터페이스
 */
export interface SimilaritySearchRequest {
	query: string;
	top_k?: number;
	similarity_threshold?: number;
	file_ids?: string[];
	user_id?: string;
}

/**
 * 검색 결과 인터페이스
 */
export interface SearchResult {
	chunk_id: string;
	doc_id: string;
	file_name: string;
	content: string;
	similarity: number;
	metadata?: Record<string, any>;
}

/**
 * 유사도 검색 응답 인터페이스
 */
export interface SimilaritySearchResponse {
	success: boolean;
	results: SearchResult[];
	total_count: number;
	error?: string;
}

/**
 * EDM 파일 다운로드
 *
 * @param docId - 문서 ID
 * @param fileUrl - 파일 URL (EDM 서버)
 * @returns File blob
 */
export const downloadEdmFile = async (docId: string, fileUrl: string): Promise<Blob> => {
	try {
		console.log(`📥 EDM 파일 다운로드 시작: ${docId}`);

		// EDM 서버에서 파일 다운로드 (실제 구현에서는 EDM API 사용)
		const response = await fetch(fileUrl, {
			method: 'GET',
			headers: {
				'Authorization': `Bearer ${import.meta.env.VITE_EDM_API_KEY || ''}`
			}
		});

		if (!response.ok) {
			throw new Error(`Failed to download file: ${response.status}`);
		}

		const blob = await response.blob();
		console.log(`✅ 파일 다운로드 완료: ${blob.size} bytes`);

		return blob;
	} catch (error) {
		console.error('❌ 파일 다운로드 실패:', error);
		throw error;
	}
};

/**
 * 문서 벡터화 (Parsing → Chunking → Embedding → Milvus 저장)
 *
 * @param request - 벡터화 요청 정보
 * @returns 벡터화 결과
 */
export const vectorizeDocument = async (
	request: VectorizationRequest
): Promise<VectorizationResponse> => {
	try {
		console.log('🔄 문서 벡터화 시작:', request.file_name);

		// Backend API를 통한 벡터화 처리
		const response = await fetch(`${BACKEND_BASE_URL}/vectorization/process`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(request)
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
			throw new Error(errorData.error || `Vectorization failed: ${response.status}`);
		}

		const result: VectorizationResponse = await response.json();
		console.log(`✅ 벡터화 완료: ${result.chunks_count}개 청크, ${result.embeddings_count}개 임베딩`);

		return result;
	} catch (error) {
		console.error('❌ 벡터화 실패:', error);
		return {
			success: false,
			message: '벡터화 처리 중 오류가 발생했습니다.',
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};

/**
 * File 객체를 통한 문서 벡터화 (파일 첨부 시)
 *
 * @param file - File 객체
 * @param userId - 사용자 ID
 * @param chatId - 채팅 ID
 * @returns 벡터화 결과
 */
export const vectorizeUploadedFile = async (
	file: File,
	userId?: string,
	chatId?: string
): Promise<VectorizationResponse> => {
	try {
		console.log('📤 첨부 파일 벡터화 시작:', file.name);

		// FormData로 파일 전송
		const formData = new FormData();
		formData.append('file', file);
		if (userId) formData.append('user_id', userId);
		if (chatId) formData.append('chat_id', chatId);

		const response = await fetch(`${BACKEND_BASE_URL}/vectorization/upload`, {
			method: 'POST',
			body: formData
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
			throw new Error(errorData.error || `Upload vectorization failed: ${response.status}`);
		}

		const result: VectorizationResponse = await response.json();
		console.log(`✅ 첨부 파일 벡터화 완료: ${result.doc_id}`);

		return result;
	} catch (error) {
		console.error('❌ 첨부 파일 벡터화 실패:', error);
		return {
			success: false,
			message: '첨부 파일 벡터화 중 오류가 발생했습니다.',
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};

/**
 * Milvus에서 유사 문서 검색
 *
 * @param request - 검색 요청 정보
 * @returns 검색 결과
 */
export const searchSimilarDocuments = async (
	request: SimilaritySearchRequest
): Promise<SimilaritySearchResponse> => {
	try {
		console.log('🔍 유사도 검색 시작:', request.query);

		const response = await fetch(`${BACKEND_BASE_URL}/vectorization/search`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				query: request.query,
				top_k: request.top_k || 5,
				similarity_threshold: request.similarity_threshold || 0.7,
				file_ids: request.file_ids,
				user_id: request.user_id
			})
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
			throw new Error(errorData.error || `Search failed: ${response.status}`);
		}

		const result: SimilaritySearchResponse = await response.json();
		console.log(`✅ 검색 완료: ${result.total_count}개 결과`);

		return result;
	} catch (error) {
		console.error('❌ 유사도 검색 실패:', error);
		return {
			success: false,
			results: [],
			total_count: 0,
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};

/**
 * 벡터화 진행 상황 조회
 *
 * @param docId - 문서 ID
 * @returns 진행 상황 정보
 */
export const getVectorizationProgress = async (docId: string): Promise<{
	status: 'pending' | 'processing' | 'completed' | 'failed';
	progress: number;
	message: string;
}> => {
	try {
		const response = await fetch(`${BACKEND_BASE_URL}/vectorization/progress/${docId}`);

		if (!response.ok) {
			throw new Error(`Failed to get progress: ${response.status}`);
		}

		return await response.json();
	} catch (error) {
		console.error('❌ 진행 상황 조회 실패:', error);
		return {
			status: 'failed',
			progress: 0,
			message: '진행 상황 조회 실패'
		};
	}
};

/**
 * 벡터화된 문서 삭제
 *
 * @param docId - 문서 ID
 * @returns 삭제 결과
 */
export const deleteVectorizedDocument = async (docId: string): Promise<{
	success: boolean;
	message: string;
}> => {
	try {
		const response = await fetch(`${BACKEND_BASE_URL}/vectorization/document/${docId}`, {
			method: 'DELETE'
		});

		if (!response.ok) {
			throw new Error(`Failed to delete: ${response.status}`);
		}

		return await response.json();
	} catch (error) {
		console.error('❌ 문서 삭제 실패:', error);
		return {
			success: false,
			message: error instanceof Error ? error.message : '문서 삭제 실패'
		};
	}
};

/**
 * 배치 벡터화 (여러 파일 동시 처리)
 *
 * @param requests - 벡터화 요청 배열
 * @returns 각 파일의 벡터화 결과
 */
export const batchVectorizeDocuments = async (
	requests: VectorizationRequest[]
): Promise<VectorizationResponse[]> => {
	try {
		console.log(`📦 배치 벡터화 시작: ${requests.length}개 파일`);

		const response = await fetch(`${BACKEND_BASE_URL}/vectorization/batch`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ documents: requests })
		});

		if (!response.ok) {
			throw new Error(`Batch vectorization failed: ${response.status}`);
		}

		const results = await response.json();
		console.log(`✅ 배치 벡터화 완료`);

		return results;
	} catch (error) {
		console.error('❌ 배치 벡터화 실패:', error);
		return requests.map(() => ({
			success: false,
			message: '배치 처리 실패',
			error: error instanceof Error ? error.message : 'Unknown error'
		}));
	}
};
