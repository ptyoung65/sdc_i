/**
 * EDM (Enterprise Document Management) API Service
 *
 * Open WebUI → n8n → Elasticsearch 연동
 *
 * 주요 기능:
 * 1. getEdmFileList: EDM 파일 리스트 조회
 * 2. getEdmFilePaths: 선택한 파일들의 경로 조회
 * 3. embedEdmFiles: 파일 임베딩 요청
 */

import { WEBUI_API_BASE_URL } from '$lib/constants';

// ==================== MOCK MODE CONFIGURATION ====================
// TODO: 실제 배포 시 MOCK_MODE를 false로 변경하세요
// Mock 모드에서는 실제 n8n, Elasticsearch 없이 테스트 가능합니다
const MOCK_MODE = true; // true: Mock 데이터 사용, false: 실제 API 사용

// TODO: Mock 데이터는 실제 API 연동 후 제거하세요
// Mock 데이터 import (MOCK_MODE = true일 때만 사용)
import {
	filterMockFilesByQuery,
	getMockFilePathsByObjids,
	mockDelay
} from './mock/edm-mock-data';
// ==================== END MOCK MODE CONFIGURATION ====================

// ==================== CONFIGURATION ====================
// TODO: 실제 n8n 서버 URL (현재: 11.93.33.10:9060)
const N8N_BASE_URL = 'http://11.93.33.10:9060';

// TODO: 실제 Elasticsearch API 엔드포인트로 교체 필요
const ELASTICSEARCH_URL = '[API1_ENDPOINT]';

// TODO: 실제 Elasticsearch API 토큰으로 교체 필요
const API_TOKEN = '[ELASTICSEARCH_API_TOKEN]';
// ==================== END CONFIGURATION ====================


// ==================== TYPE DEFINITIONS ====================

export interface EdmFile {
	objid: string; // 오브젝트 ID
	objtNm: string; // 파일명
	fileExtNm: string; // 파일 확장자
	filesize: number; // 파일 크기 (bytes)
	filePOwnerid: string; // 파일 소유자 ID
	filePOwerNm: string; // 파일 소유자명
	fileVerNm: string; // 파일 버전명
	flieLasVerSno: number; // 파일 마지막 버전 순번
	objtRegDtm: number; // 등록일시 (timestamp)
	objtStatChgDtm: number; // 수정일시 (timestamp)
	workspaceNm: string; // 워크스페이스명
	prsrvTermExpireYn: string; // 파일 만료 여부 (Y/N)
	maxObjtSharePolicyId: string | null; // 최대 권한값 (null인 경우 권한 없음)
}

export interface EdmFileListResponse {
	message: string;
	data: {
		totalCount: number;
		items: EdmFile[];
	};
	resultCode: number;
}

export interface EdmFilePath {
	objid: string;
	filePath: string; // 실제 파일 경로 (네트워크 공유 또는 URL)
}

export interface EdmFilePathResponse {
	message: string;
	data: {
		items: EdmFilePath[];
	};
	resultCode: number;
}

export interface EdmEmbedRequest {
	files: Array<{
		objid: string;
		filePath: string;
		fileName: string;
	}>;
	collection_name?: string;
}

export interface EdmEmbedResponse {
	success: boolean;
	message: string;
	embedded_files: Array<{
		edm_objid: string;
		file_id: string;
		filename: string;
		status: string;
	}>;
	failed_files: Array<{
		edm_objid: string;
		filename: string;
		error: string;
	}>;
}

// ==================== API FUNCTIONS ====================

/**
 * EDM 파일 리스트 조회
 *
 * @param query - 검색 쿼리
 * @param userId - 사용자 ID
 * @param workspaceId - 워크스페이스 ID (optional)
 * @param token - 인증 토큰
 * @returns EDM 파일 리스트
 */
export const getEdmFileList = async (
	query: string,
	userId: string,
	workspaceId?: string,
	token: string = ''
): Promise<EdmFileListResponse> => {
	// ==================== MOCK MODE ====================
	// TODO: MOCK_MODE를 false로 변경하면 실제 API 호출로 전환됩니다
	if (MOCK_MODE) {
		console.log('[MOCK] EDM 파일 리스트 조회 - Backend API 호출 - query:', query);
		// Mock 모드에서도 Backend API를 호출 (Backend에서 Mock 데이터 반환)
		try {
			const res = await fetch(`/api/v1/edm/search`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...(token && { Authorization: `Bearer ${token}` })
				},
				body: JSON.stringify({
					query,
					page: 1,
					pageSize: 20
				})
			});

			if (!res.ok) {
				throw new Error(`HTTP ${res.status}: ${res.statusText}`);
			}

			const data = await res.json();
			console.log('[MOCK] Backend API 응답:', data);
			return data;
		} catch (error) {
			console.error('[MOCK] Backend API 호출 실패, Frontend Mock 사용:', error);
			await mockDelay(500);
			return filterMockFilesByQuery(query);
		}
	}
	// ==================== END MOCK MODE ====================

	try {
		const res = await fetch(`${N8N_BASE_URL}/webhook/edm-file-list`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				...(token && { Authorization: `Bearer ${token}` })
			},
			body: JSON.stringify({
				elasticsearchUrl: ELASTICSEARCH_URL,
				apiToken: API_TOKEN,
				query,
				userId,
				workspaceId
			})
		});

		if (!res.ok) {
			throw new Error(`HTTP ${res.status}: ${res.statusText}`);
		}

		const data = await res.json();
		return data;
	} catch (error) {
		console.error('[EDM API] 파일 리스트 조회 실패:', error);
		throw error;
	}
};

/**
 * EDM 파일 경로 조회 (다중)
 *
 * @param objids - 오브젝트 ID 배열
 * @param token - 인증 토큰
 * @returns 파일 경로 리스트
 */
export const getEdmFilePaths = async (
	objids: string[],
	token: string = ''
): Promise<EdmFilePathResponse> => {
	// ==================== MOCK MODE ====================
	// TODO: MOCK_MODE를 false로 변경하면 실제 API 호출로 전환됩니다
	if (MOCK_MODE) {
		console.log('[MOCK] EDM 파일 경로 조회 - objids:', objids);
		await mockDelay(300); // 네트워크 지연 시뮬레이션
		return getMockFilePathsByObjids(objids);
	}
	// ==================== END MOCK MODE ====================

	try {
		const res = await fetch(`${N8N_BASE_URL}/webhook/edm-file-path`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				...(token && { Authorization: `Bearer ${token}` })
			},
			body: JSON.stringify({
				elasticsearchUrl: ELASTICSEARCH_URL,
				apiToken: API_TOKEN,
				objids
			})
		});

		if (!res.ok) {
			throw new Error(`HTTP ${res.status}: ${res.statusText}`);
		}

		const data = await res.json();
		return data;
	} catch (error) {
		console.error('[EDM API] 파일 경로 조회 실패:', error);
		throw error;
	}
};

/**
 * EDM 파일 임베딩 요청
 *
 * Open WebUI 백엔드를 통해 파일을 다운로드하고
 * 파싱, 청킹, 임베딩, 벡터 저장을 수행
 *
 * @param request - 임베딩 요청 데이터
 * @param token - 인증 토큰
 * @returns 임베딩 결과
 */
export const embedEdmFiles = async (
	request: EdmEmbedRequest,
	token: string = ''
): Promise<EdmEmbedResponse> => {
	// ==================== MOCK MODE ====================
	// TODO: MOCK_MODE를 false로 변경하면 실제 API 호출로 전환됩니다
	if (MOCK_MODE) {
		console.log('[MOCK] EDM 파일 임베딩 요청 - files:', request.files.length);
		await mockDelay(2000); // 임베딩 처리 시뮬레이션 (2초)

		// Mock 임베딩 성공 응답
		const mockResponse: EdmEmbedResponse = {
			success: true,
			message: `[MOCK] ${request.files.length}개 파일 임베딩 완료`,
			embedded_files: request.files.map((file) => ({
				edm_objid: file.objid,
				file_id: `mock-file-${file.objid}`,
				filename: file.fileName,
				status: 'success'
			})),
			failed_files: []
		};

		console.log('[MOCK] 임베딩 성공:', mockResponse);
		return mockResponse;
	}
	// ==================== END MOCK MODE ====================

	try {
		// Open WebUI 백엔드 API 호출
		const res = await fetch(`${WEBUI_API_BASE_URL}/rag/edm/embed`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				...(token && { Authorization: `Bearer ${token}` })
			},
			body: JSON.stringify(request)
		});

		if (!res.ok) {
			throw new Error(`HTTP ${res.status}: ${res.statusText}`);
		}

		const data = await res.json();
		return data;
	} catch (error) {
		console.error('[EDM API] 임베딩 요청 실패:', error);
		throw error;
	}
};

/**
 * EDM 통합 워크플로우
 *
 * 1. 파일 리스트 조회
 * 2. 사용자 선택
 * 3. 파일 경로 조회
 * 4. 임베딩 요청
 *
 * @param query - 검색 쿼리
 * @param userId - 사용자 ID
 * @param selectedObjids - 선택한 파일 objid 리스트
 * @param token - 인증 토큰
 * @returns 임베딩 결과
 */
export const edmWorkflow = async (
	query: string,
	userId: string,
	selectedObjids: string[],
	token: string = ''
): Promise<EdmEmbedResponse> => {
	try {
		// Step 1: 파일 리스트 조회
		const fileListResponse = await getEdmFileList(query, userId, undefined, token);

		if (fileListResponse.resultCode !== 60200) {
			throw new Error(`파일 리스트 조회 실패: ${fileListResponse.message}`);
		}

		// Step 2: 선택한 파일만 필터링
		const selectedFiles = fileListResponse.data.items.filter((file) =>
			selectedObjids.includes(file.objid)
		);

		if (selectedFiles.length === 0) {
			throw new Error('선택한 파일이 없습니다.');
		}

		// Step 3: 파일 경로 조회
		const filePathResponse = await getEdmFilePaths(selectedObjids, token);

		if (filePathResponse.resultCode !== 60200) {
			throw new Error(`파일 경로 조회 실패: ${filePathResponse.message}`);
		}

		// Step 4: 임베딩 요청 데이터 구성
		const embedRequest: EdmEmbedRequest = {
			files: filePathResponse.data.items.map((pathItem) => {
				const file = selectedFiles.find((f) => f.objid === pathItem.objid);
				return {
					objid: pathItem.objid,
					filePath: pathItem.filePath,
					fileName: file?.objtNm || 'unknown'
				};
			}),
			collection_name: `edm-${userId}`
		};

		// Step 5: 임베딩 실행
		const embedResponse = await embedEdmFiles(embedRequest, token);

		return embedResponse;
	} catch (error) {
		console.error('[EDM Workflow] 실행 실패:', error);
		throw error;
	}
};
