/**
 * n8n Webhook API Integration
 * EDM 문서 검색을 위한 n8n 워크플로우 연동
 */

const N8N_BASE_URL = import.meta.env.VITE_N8N_BASE_URL || 'http://169.254.1.2:5678';
const N8N_WEBHOOK_PATH = '/webhook/edm-search';

export interface N8nSearchRequest {
	message: string;
	categories: string[];
	chat_id?: string;
	user_id?: string;
}

export interface N8nDocument {
	doc_id: string;
	title: string;
	score: number;
	url?: string;
	summary?: string;
	author?: string;
	create_date?: string;
	file_type?: string;
	file_size?: string;
}

export interface N8nSearchResponse {
	documents: N8nDocument[];
	total_count: number;
	error?: string;
}

/**
 * n8n webhook 호출하여 EDM 문서 검색
 */
export const searchEdmDocumentsViaN8n = async (
	message: string,
	categories: string[],
	chatId?: string,
	userId?: string
): Promise<N8nSearchResponse> => {
	try {
		const url = `${N8N_BASE_URL}${N8N_WEBHOOK_PATH}`;

		console.log('🔵 n8n webhook 호출:', url);

		const payload: N8nSearchRequest = {
			message,
			categories,
			chat_id: chatId,
			user_id: userId
		};

		console.log('📤 n8n payload:', payload);

		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(payload)
		});

		if (!response.ok) {
			throw new Error(`n8n webhook failed: ${response.status} ${response.statusText}`);
		}

		const result: N8nSearchResponse = await response.json();

		console.log('✅ n8n 응답:', result);

		return result;
	} catch (error) {
		console.error('❌ n8n webhook error:', error);

		// 에러 시 빈 결과 반환
		return {
			documents: [],
			total_count: 0,
			error: error instanceof Error ? error.message : 'Unknown error'
		};
	}
};

/**
 * n8n 문서를 EDM 파일 리스트 포맷으로 변환
 * n8n이 반환하는 [{key,value ...},{key,value ...},...] 형태의 배열을
 * 각 객체마다 하나의 파일 리스트 항목으로 변환
 */
export const convertN8nDocsToEdmFormat = (docs: any[]) => {
	if (!Array.isArray(docs)) {
		console.warn('⚠️ n8n 응답이 배열이 아닙니다:', docs);
		return [];
	}

	console.log(`🔄 n8n 문서 변환 시작: ${docs.length}개 문서`);

	return docs.map((doc, index) => {
		console.log(`📄 파일 ${index + 1}:`, doc);

		// n8n이 반환하는 key-value 쌍을 그대로 EDM 포맷으로 매핑
		return {
			FILE_NAME: doc.title || doc.FILE_NAME || doc.file_name || `문서_${index + 1}`,
			AUTHOR: doc.author || doc.AUTHOR || '작성자 미상',
			CREATE_DATE: doc.create_date || doc.CREATE_DATE || '',
			FILE_TYPE: doc.file_type || doc.FILE_TYPE || 'application/octet-stream',
			FILE_SIZE: doc.file_size || doc.FILE_SIZE || '',
			DOC_ID: doc.doc_id || doc.DOC_ID || `DOC${String(index + 1).padStart(3, '0')}`,
			URL: doc.url || doc.URL,
			SCORE: doc.score || doc.SCORE || 0,
			SUMMARY: doc.summary || doc.SUMMARY
		};
	});
};
