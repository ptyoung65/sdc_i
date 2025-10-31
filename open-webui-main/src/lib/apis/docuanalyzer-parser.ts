/**
 * Synap Docuanalyzer Parser Integration
 *
 * Synap의 docuanalyzer를 Open WebUI 파이프라인의 파서로 사용하기 위한 통합 모듈
 *
 * 사용 흐름:
 * 1. edmdownload 파이프라인으로 파일 다운로드 (/tmp/downloads/)
 * 2. docuanalyzer로 문서 파싱 (이 모듈)
 * 3. 파싱된 텍스트를 청킹
 * 4. 임베딩 생성
 * 5. Milvus에 벡터 저장
 */

const BACKEND_BASE_URL = '/api/v1';

// Synap Docuanalyzer API 설정 (환경변수 또는 설정 파일에서 가져오기)
const DOCUANALYZER_BASE_URL = import.meta.env.VITE_DOCUANALYZER_URL || 'http://localhost:8200';
const DOCUANALYZER_API_KEY = import.meta.env.VITE_DOCUANALYZER_API_KEY || '';

/**
 * Docuanalyzer 파싱 요청 인터페이스
 */
export interface DocuAnalyzerRequest {
	file_path: string;          // 로컬 파일 경로 (예: /tmp/downloads/document.pdf)
	file_name: string;          // 파일명
	options?: {
		extract_tables?: boolean;     // 표 추출 여부
		extract_images?: boolean;     // 이미지 추출 여부
		ocr_enabled?: boolean;        // OCR 사용 여부
		language?: string;            // 문서 언어 (ko, en 등)
		output_format?: 'markdown' | 'json' | 'text';  // 출력 형식
	};
}

/**
 * Docuanalyzer 파싱 응답 인터페이스
 */
export interface DocuAnalyzerResponse {
	success: boolean;
	file_name: string;
	content: {
		text: string;              // 추출된 전체 텍스트
		sections?: Array<{         // 섹션별 텍스트 (있는 경우)
			title: string;
			content: string;
			page?: number;
		}>;
		tables?: Array<{           // 추출된 표 데이터
			page: number;
			data: string[][];      // 2D 배열 형식의 표 데이터
			markdown?: string;     // 마크다운 형식 표
		}>;
		images?: Array<{           // 추출된 이미지 정보
			page: number;
			path: string;          // 이미지 저장 경로
			caption?: string;
		}>;
		metadata?: {
			total_pages?: number;
			author?: string;
			created_date?: string;
			file_type?: string;
		};
	};
	processing_time?: number;     // 처리 시간 (초)
	error?: string;
}

/**
 * Synap Docuanalyzer를 사용하여 문서 파싱
 *
 * @param request - 파싱 요청 정보
 * @returns 파싱된 문서 내용
 *
 * @example
 * ```typescript
 * const result = await parseDocumentWithDocuAnalyzer({
 *   file_path: '/tmp/downloads/report.pdf',
 *   file_name: 'report.pdf',
 *   options: {
 *     extract_tables: true,
 *     ocr_enabled: true,
 *     language: 'ko',
 *     output_format: 'markdown'
 *   }
 * });
 *
 * if (result.success) {
 *   console.log('파싱된 텍스트:', result.content.text);
 *   console.log('추출된 표:', result.content.tables);
 * }
 * ```
 */
export const parseDocumentWithDocuAnalyzer = async (
	request: DocuAnalyzerRequest
): Promise<DocuAnalyzerResponse> => {
	try {
		console.log(`📄 Docuanalyzer 파싱 시작: ${request.file_name}`);
		console.log(`📁 파일 경로: ${request.file_path}`);

		// Docuanalyzer API 호출
		const response = await fetch(`${DOCUANALYZER_BASE_URL}/api/parse`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				...(DOCUANALYZER_API_KEY && { 'Authorization': `Bearer ${DOCUANALYZER_API_KEY}` })
			},
			body: JSON.stringify({
				file_path: request.file_path,
				file_name: request.file_name,
				...request.options
			})
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
			throw new Error(`Docuanalyzer parsing failed: ${errorData.error || response.statusText}`);
		}

		const result: DocuAnalyzerResponse = await response.json();

		console.log(`✅ Docuanalyzer 파싱 완료`);
		console.log(`📊 추출된 텍스트 길이: ${result.content.text.length} 문자`);
		if (result.content.sections) {
			console.log(`📑 섹션 수: ${result.content.sections.length}개`);
		}
		if (result.content.tables) {
			console.log(`📈 추출된 표: ${result.content.tables.length}개`);
		}

		return result;
	} catch (error) {
		console.error('❌ Docuanalyzer 파싱 실패:', error);
		return {
			success: false,
			file_name: request.file_name,
			content: {
				text: ''
			},
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};

/**
 * Docuanalyzer로 파싱한 후 청킹 및 벡터화까지 완전한 파이프라인 실행
 *
 * @param filePath - 로컬 파일 경로
 * @param fileName - 파일명
 * @param fileId - 파일 ID
 * @param parsingOptions - Docuanalyzer 파싱 옵션
 * @returns 벡터화 결과
 *
 * @example
 * ```typescript
 * // EDM 파일 다운로드 후 완전한 파이프라인 실행
 * const vectorizeResult = await parseAndVectorizeWithDocuAnalyzer(
 *   '/tmp/downloads/document.pdf',
 *   'document.pdf',
 *   'DOC001',
 *   {
 *     extract_tables: true,
 *     ocr_enabled: true,
 *     language: 'ko',
 *     output_format: 'markdown'
 *   }
 * );
 *
 * if (vectorizeResult.success) {
 *   console.log(`벡터화 완료: ${vectorizeResult.chunks_count}개 청크`);
 * }
 * ```
 */
export const parseAndVectorizeWithDocuAnalyzer = async (
	filePath: string,
	fileName: string,
	fileId: string,
	parsingOptions?: DocuAnalyzerRequest['options']
): Promise<{
	success: boolean;
	message: string;
	doc_id?: string;
	chunks_count?: number;
	embeddings_count?: number;
	error?: string;
}> => {
	try {
		console.log(`🔄 Docuanalyzer 파싱 + 벡터화 파이프라인 시작: ${fileName}`);

		// 1단계: Docuanalyzer로 문서 파싱
		const parseResult = await parseDocumentWithDocuAnalyzer({
			file_path: filePath,
			file_name: fileName,
			options: parsingOptions || {
				extract_tables: true,
				ocr_enabled: true,
				language: 'ko',
				output_format: 'markdown'
			}
		});

		if (!parseResult.success || !parseResult.content.text) {
			throw new Error(parseResult.error || '문서 파싱 실패');
		}

		console.log(`📝 파싱된 텍스트 길이: ${parseResult.content.text.length} 문자`);

		// 2단계: 파싱된 텍스트를 청킹 및 벡터화
		// Backend API에 파싱된 텍스트와 메타데이터 전달
		const vectorizeResponse = await fetch(`${BACKEND_BASE_URL}/vectorization/process-parsed-content`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				file_id: fileId,
				file_name: fileName,
				parsed_content: {
					text: parseResult.content.text,
					sections: parseResult.content.sections,
					tables: parseResult.content.tables,
					metadata: parseResult.content.metadata
				},
				parser_info: {
					parser: 'synap-docuanalyzer',
					version: '1.0',
					processing_time: parseResult.processing_time
				}
			})
		});

		if (!vectorizeResponse.ok) {
			const errorData = await vectorizeResponse.json().catch(() => ({ error: 'Unknown error' }));
			throw new Error(errorData.error || `Vectorization failed: ${vectorizeResponse.status}`);
		}

		const vectorizeResult = await vectorizeResponse.json();
		console.log(`✅ 벡터화 완료: ${vectorizeResult.chunks_count}개 청크`);

		return {
			success: true,
			message: 'Docuanalyzer 파싱 및 벡터화 완료',
			doc_id: vectorizeResult.doc_id,
			chunks_count: vectorizeResult.chunks_count,
			embeddings_count: vectorizeResult.embeddings_count
		};
	} catch (error) {
		console.error('❌ Docuanalyzer 파이프라인 실패:', error);
		return {
			success: false,
			message: 'Docuanalyzer 파싱 및 벡터화 실패',
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};

/**
 * Docuanalyzer 서비스 상태 확인
 *
 * @returns 서비스 상태 정보
 */
export const checkDocuAnalyzerHealth = async (): Promise<{
	available: boolean;
	version?: string;
	message: string;
}> => {
	try {
		const response = await fetch(`${DOCUANALYZER_BASE_URL}/health`, {
			method: 'GET',
			headers: {
				...(DOCUANALYZER_API_KEY && { 'Authorization': `Bearer ${DOCUANALYZER_API_KEY}` })
			}
		});

		if (!response.ok) {
			throw new Error(`Health check failed: ${response.status}`);
		}

		const healthData = await response.json();

		return {
			available: true,
			version: healthData.version,
			message: 'Docuanalyzer 서비스 정상'
		};
	} catch (error) {
		console.warn('⚠️ Docuanalyzer 서비스 접근 불가:', error);
		return {
			available: false,
			message: error instanceof Error ? error.message : 'Service unavailable'
		};
	}
};
