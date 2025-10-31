/**
 * EDM Mock Data
 *
 * ⚠️ 주의: 이 파일은 개발/테스트용 Mock 데이터입니다.
 *
 * TODO: 실제 EDM API 연동 후에는 이 파일을 사용하지 않습니다.
 *
 * Mock 모드 비활성화 방법:
 * - src/lib/apis/edm.ts 파일에서 MOCK_MODE = false로 변경
 */

import type { EdmFileListResponse, EdmFilePathResponse } from '../edm';

// ==================== MOCK FILE LIST (10개 파일) ====================
// Elasticsearch에서 반환하는 파일 리스트 Mock 데이터
// 권한 있음: 7개, 권한 없음: 3개

export const MOCK_FILE_LIST: EdmFileListResponse = {
	message: 'IOFFICE_SUCCESS',
	data: {
		totalCount: 13,
		items: [
			{
				objid: '163755716000001',
				objtNm: 'AI_챗봇_프로젝트_제안서.txt',
				fileExtNm: 'txt',
				filesize: 549,
				filePOwnerid: '153060212733400449',
				filePOwerNm: '김철수',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1705728000000, // 2024-01-20 10:00:00
				objtStatChgDtm: 1705814400000, // 2024-01-21 10:00:00
				workspaceNm: '기획팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000' // ✅ 읽기/쓰기 권한
			},
			{
				objid: '163755716000002',
				objtNm: '2024년_사업계획서_최종.txt',
				fileExtNm: 'txt',
				filesize: 459,
				filePOwnerid: '153060212733400450',
				filePOwerNm: '이영희',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1705641600000, // 2024-01-19 10:00:00
				objtStatChgDtm: 1705900800000, // 2024-01-22 10:00:00
				workspaceNm: '경영지원팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000' // ✅ 읽기/쓰기 권한
			},
			{
				objid: '163755716000003',
				objtNm: '고객_만족도_분석_데이터.txt',
				fileExtNm: 'txt',
				filesize: 550,
				filePOwnerid: '153060212733400451',
				filePOwerNm: '박민수',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1705555200000, // 2024-01-18 10:00:00
				objtStatChgDtm: 1705987200000, // 2024-01-23 10:00:00
				workspaceNm: '데이터분석팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000' // ✅ 읽기/쓰기 권한
			},
			{
				objid: '163755716000004',
				objtNm: 'RAG_시스템_기술_사양서.txt',
				fileExtNm: 'txt',
				filesize: 528,
				filePOwnerid: '153060212733400452',
				filePOwerNm: '최개발',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1705468800000, // 2024-01-17 10:00:00
				objtStatChgDtm: 1706073600000, // 2024-01-24 10:00:00
				workspaceNm: '개발팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000' // ✅ 읽기/쓰기 권한
			},
			{
				objid: '163755716000005',
				objtNm: 'Q1_매출_분석_보고서.txt',
				fileExtNm: 'txt',
				filesize: 488,
				filePOwnerid: '153060212733400450',
				filePOwerNm: '이영희',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1705209600000, // 2024-01-14 10:00:00
				objtStatChgDtm: 1706332800000, // 2024-01-27 10:00:00
				workspaceNm: '경영지원팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000' // ✅ 읽기/쓰기 권한
			},
			// 추가 파일 (AI 관련)
			{
				objid: '163755716000006',
				objtNm: 'AI_모델_성능_평가_보고서.txt',
				fileExtNm: 'txt',
				filesize: 612,
				filePOwnerid: '153060212733400452',
				filePOwerNm: '최개발',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1706160000000,
				objtStatChgDtm: 1706246400000,
				workspaceNm: '개발팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000'
			},
			{
				objid: '163755716000007',
				objtNm: '자연어처리_AI_연구_자료.txt',
				fileExtNm: 'txt',
				filesize: 738,
				filePOwnerid: '153060212733400453',
				filePOwerNm: '정연구',
				fileVerNm: '2.0',
				flieLasVerSno: 2,
				objtRegDtm: 1706332800000,
				objtStatChgDtm: 1706419200000,
				workspaceNm: 'AI연구소',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000'
			},
			// 추가 파일 (분석 관련)
			{
				objid: '163755716000008',
				objtNm: '시장_트렌드_분석_리포트.txt',
				fileExtNm: 'txt',
				filesize: 595,
				filePOwnerid: '153060212733400451',
				filePOwerNm: '박민수',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1706505600000,
				objtStatChgDtm: 1706592000000,
				workspaceNm: '데이터분석팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000'
			},
			{
				objid: '163755716000009',
				objtNm: '경쟁사_분석_자료.txt',
				fileExtNm: 'txt',
				filesize: 521,
				filePOwnerid: '153060212733400454',
				filePOwerNm: '강분석',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1706678400000,
				objtStatChgDtm: 1706764800000,
				workspaceNm: '데이터분석팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000'
			},
			// 추가 파일 (2024 관련)
			{
				objid: '163755716000010',
				objtNm: '2024년_마케팅_전략.txt',
				fileExtNm: 'txt',
				filesize: 643,
				filePOwnerid: '153060212733400455',
				filePOwerNm: '송마케',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1706851200000,
				objtStatChgDtm: 1706937600000,
				workspaceNm: '마케팅팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000'
			},
			{
				objid: '163755716000011',
				objtNm: '2024년_기술_로드맵.txt',
				fileExtNm: 'txt',
				filesize: 687,
				filePOwnerid: '153060212733400452',
				filePOwerNm: '최개발',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1707024000000,
				objtStatChgDtm: 1707110400000,
				workspaceNm: '개발팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: '1113000000'
			},
			// 권한 없는 파일 예시
			{
				objid: '163755716000012',
				objtNm: '임원_회의록_기밀.txt',
				fileExtNm: 'txt',
				filesize: 423,
				filePOwnerid: '153060212733400456',
				filePOwerNm: '임임원',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1707196800000,
				objtStatChgDtm: 1707283200000,
				workspaceNm: '경영진',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: null // ❌ 권한 없음
			},
			{
				objid: '163755716000013',
				objtNm: '인사_평가_데이터.txt',
				fileExtNm: 'txt',
				filesize: 512,
				filePOwnerid: '153060212733400457',
				filePOwerNm: '홍인사',
				fileVerNm: '1.0',
				flieLasVerSno: 1,
				objtRegDtm: 1707369600000,
				objtStatChgDtm: 1707456000000,
				workspaceNm: '인사팀',
				prsrvTermExpireYn: 'N',
				maxObjtSharePolicyId: null // ❌ 권한 없음
			}
		]
	},
	resultCode: 60200
};

// ==================== MOCK FILE PATHS ====================
// Elasticsearch에서 반환하는 파일 경로 Mock 데이터

export const MOCK_FILE_PATHS: EdmFilePathResponse = {
	message: 'IOFFICE_SUCCESS',
	data: {
		items: [
			{
				objid: '163755716000001',
				filePath: '/static/mock/AI_챗봇_프로젝트_제안서.txt'
			},
			{
				objid: '163755716000002',
				filePath: '/static/mock/2024년_사업계획서_최종.txt'
			},
			{
				objid: '163755716000003',
				filePath: '/static/mock/고객_만족도_분석_데이터.txt'
			},
			{
				objid: '163755716000004',
				filePath: '/static/mock/RAG_시스템_기술_사양서.txt'
			},
			{
				objid: '163755716000005',
				filePath: '/static/mock/Q1_매출_분석_보고서.txt'
			}
		]
	},
	resultCode: 60200
};

// ==================== HELPER FUNCTIONS ====================

/**
 * 검색 쿼리로 Mock 파일 필터링
 *
 * @param query - 검색어
 * @returns 필터링된 파일 리스트
 */
export function filterMockFilesByQuery(query: string): EdmFileListResponse {
	if (!query || query.trim() === '') {
		return MOCK_FILE_LIST;
	}

	const lowerQuery = query.toLowerCase();
	const filteredItems = MOCK_FILE_LIST.data.items.filter((file) => {
		return (
			file.objtNm.toLowerCase().includes(lowerQuery) ||
			file.workspaceNm.toLowerCase().includes(lowerQuery) ||
			file.filePOwerNm.toLowerCase().includes(lowerQuery)
		);
	});

	return {
		...MOCK_FILE_LIST,
		data: {
			totalCount: filteredItems.length,
			items: filteredItems
		}
	};
}

/**
 * objid 배열로 Mock 파일 경로 조회
 *
 * @param objids - 오브젝트 ID 배열
 * @returns 파일 경로 리스트
 */
export function getMockFilePathsByObjids(objids: string[]): EdmFilePathResponse {
	const filteredItems = MOCK_FILE_PATHS.data.items.filter((item) =>
		objids.includes(item.objid)
	);

	return {
		...MOCK_FILE_PATHS,
		data: {
			items: filteredItems
		}
	};
}

/**
 * Mock 지연 시뮬레이션
 *
 * @param ms - 지연 시간 (밀리초)
 * @returns Promise
 */
export function mockDelay(ms: number = 500): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}
