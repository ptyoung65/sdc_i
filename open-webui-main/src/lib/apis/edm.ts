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
import { env } from '$lib/config/environment';
import { logger } from '$lib/utils/logger';

// Mock 데이터 import (Mock 모드일 때만 사용)
import {
	filterMockFilesByQuery,
	getMockFilePathsByObjids,
	mockDelay
} from './mock/edm-mock-data';

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
	logger.debug('EDM', '파일 리스트 조회 요청', { query });

	// Mock 모드 체크
	if (env.ENABLE_MOCK_MODE) {
		logger.warn('EDM', 'Mock 모드로 파일 리스트 조회');
		await mockDelay(500);
		return filterMockFilesByQuery(query);
	}

	try {
		// 백엔드 API 호출 - 실제 uploads 폴더 파일 목록 조회
		const res = await fetch(`${WEBUI_API_BASE_URL}/edm/files`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				...(token && { Authorization: `Bearer ${token}` })
			},
			body: JSON.stringify({
				query: query || ''
			})
		});

		if (!res.ok) {
			throw new Error(`HTTP ${res.status}: ${res.statusText}`);
		}

		const data = await res.json();
		logger.info('EDM', '파일 리스트 조회 성공', { count: data.data?.items?.length || 0 });

		return data;
	} catch (error) {
		logger.error('EDM', '파일 리스트 조회 실패', error);
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
	if (env.ENABLE_MOCK_MODE) {
		logger.warn('EDM', 'Mock 모드로 파일 경로 조회', { objids });
		await mockDelay(300);
		return getMockFilePathsByObjids(objids);
	}

	try {
		// 환경변수 검증
		if (!env.ELASTICSEARCH_URL || !env.ELASTICSEARCH_API_TOKEN) {
			logger.warn('EDM', 'Elasticsearch 설정이 누락되었습니다. 검색이 제한될 수 있습니다.');
		}

		const res = await fetch(`${env.N8N_BASE_URL}/webhook/edm-file-path`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				...(token && { Authorization: `Bearer ${token}` })
			},
			body: JSON.stringify({
				elasticsearchUrl: env.ELASTICSEARCH_URL,
				apiToken: env.ELASTICSEARCH_API_TOKEN,
				objids
			})
		});

		if (!res.ok) {
			throw new Error(`HTTP ${res.status}: ${res.statusText}`);
		}

		const data = await res.json();
		logger.info('EDM', '파일 경로 조회 성공', { count: data.data?.items?.length || 0 });
		return data;
	} catch (error) {
		logger.error('EDM', '파일 경로 조회 실패', error);
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
	if (env.ENABLE_MOCK_MODE) {
		logger.warn('EDM', 'Mock 모드로 임베딩 요청', { files: request.files.length });
		await mockDelay(2000);

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

		logger.info('EDM', 'Mock 임베딩 성공', mockResponse);
		return mockResponse;
	}

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
		logger.info('EDM', '임베딩 요청 성공', {
			success: data.success,
			embedded: data.embedded_files?.length,
			failed: data.failed_files?.length
		});
		return data;
	} catch (error) {
		logger.error('EDM', '임베딩 요청 실패', error);
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
	logger.info('EDM', '워크플로우 시작', { query, selectedCount: selectedObjids.length });

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

		logger.info('EDM', '워크플로우 완료', { success: embedResponse.success });
		return embedResponse;
	} catch (error) {
		logger.error('EDM', '워크플로우 실패', error);
		throw error;
	}
};
