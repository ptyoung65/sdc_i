<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import EdmFileListModal from './EdmFileListModal.svelte';
	import { getEdmFileList, getEdmFilePaths, embedEdmFiles } from '$lib/apis/edm';
	import { user } from '$lib/stores';

	// EDM 검색 활성화 상태
	export let edmSearchEnabled: boolean = false;
	export let query: string = '';

	let showModal = false;
	let fileList: any[] = [];
	let loading = false;

	// EDM 파일 리스트 조회
	async function fetchEdmFiles() {
		if (!query || query.trim() === '') {
			toast.error('검색어를 입력해주세요.');
			return;
		}

		loading = true;
		try {
			const token = localStorage.getItem('token') || '';
			const userId = $user?.id || '';

			const response = await getEdmFileList(query, userId, undefined, token);

			if (response.resultCode === 60200) {
				fileList = response.data.items || [];
				if (fileList.length > 0) {
					showModal = true;
				} else {
					toast.info('검색 결과가 없습니다.');
				}
			} else {
				toast.error(`파일 리스트 조회 실패: ${response.message}`);
			}
		} catch (error) {
			console.error('[EDM Integration] 파일 리스트 조회 오류:', error);
			toast.error('파일 리스트 조회 중 오류가 발생했습니다.');
		} finally {
			loading = false;
		}
	}

	// 파일 임베딩 처리
	async function handleEmbed(event: CustomEvent) {
		const selectedFiles = event.detail.files;

		if (!selectedFiles || selectedFiles.length === 0) {
			toast.error('선택한 파일이 없습니다.');
			return;
		}

		loading = true;
		toast.info(`${selectedFiles.length}개 파일 임베딩 시작...`);

		try {
			const token = localStorage.getItem('token') || '';
			const objids = selectedFiles.map((f: any) => f.objid);

			// Step 1: 파일 경로 조회
			const pathResponse = await getEdmFilePaths(objids, token);

			if (pathResponse.resultCode !== 60200) {
				throw new Error(`파일 경로 조회 실패: ${pathResponse.message}`);
			}

			// Step 2: 임베딩 요청
			const embedRequest = {
				files: pathResponse.data.items.map((pathItem: any) => {
					const file = selectedFiles.find((f: any) => f.objid === pathItem.objid);
					return {
						objid: pathItem.objid,
						filePath: pathItem.filePath,
						fileName: file?.objtNm || 'unknown'
					};
				}),
				collection_name: `edm-${$user?.id || 'default'}`
			};

			const embedResponse = await embedEdmFiles(embedRequest, token);

			if (embedResponse.success) {
				toast.success(embedResponse.message);

				// 임베딩 성공한 파일 정보 출력
				if (embedResponse.embedded_files.length > 0) {
					console.log('[EDM Integration] 임베딩 완료된 파일:', embedResponse.embedded_files);
				}

				// 실패한 파일 정보 출력
				if (embedResponse.failed_files.length > 0) {
					console.error('[EDM Integration] 임베딩 실패한 파일:', embedResponse.failed_files);
					toast.error(`${embedResponse.failed_files.length}개 파일 임베딩 실패`);
				}
			} else {
				toast.error(embedResponse.message);
			}
		} catch (error) {
			console.error('[EDM Integration] 임베딩 오류:', error);
			toast.error('임베딩 중 오류가 발생했습니다.');
		} finally {
			loading = false;
			showModal = false;
		}
	}

	// 쿼리 변경 감지
	$: if (edmSearchEnabled && query && query.trim() !== '') {
		// EDM 검색이 활성화되어 있고 쿼리가 있으면 자동으로 파일 리스트 조회
		fetchEdmFiles();
	}
</script>

<!-- EDM 파일 리스트 모달 -->
<EdmFileListModal bind:show={showModal} files={fileList} on:embed={handleEmbed} on:close={() => (showModal = false)} />

<!-- 로딩 인디케이터 -->
{#if loading}
	<div class="fixed top-4 right-4 z-50 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
		<svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
			<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
		</svg>
		<span>EDM 파일 처리 중...</span>
	</div>
{/if}
