<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	onMount(() => {
		console.log('🔵 [EdmFileListModal 팝업 표시]', {
			timestamp: new Date().toISOString(),
			action: 'modal_opened',
			filesCount: files.length,
			files: files.map(f => ({
				objid: f.objid,
				objtNm: f.objtNm,
				hasPermission: f.maxObjtSharePolicyId !== null
			}))
		});
	});

	export let files: any[] = [];
	export let show: boolean = false;

	const dispatch = createEventDispatcher();

	let selectedFiles: string[] = [];
	let previewFile: any = null;
	let showPreview: boolean = false;
	let previewContent: string = '';
	let isLoadingPreview: boolean = false;

	// 권한이 있는 파일만 선택 가능
	function hasPermission(file: any): boolean {
		return file.maxObjtSharePolicyId !== null && file.maxObjtSharePolicyId !== undefined;
	}

	// 문서 미리보기
	async function viewDocument(file: any) {
		if (!hasPermission(file)) {
			toast.error('이 파일에 대한 권한이 없습니다.');
			return;
		}

		previewFile = file;
		showPreview = true;
		isLoadingPreview = true;
		previewContent = '';

		try {
			// EDM API를 통해 문서 내용을 가져와야 함
			// 현재는 파일 정보만 표시
			previewContent = `파일 정보:
파일명: ${file.objtNm}
워크스페이스: ${file.workspaceNm || '-'}
소유자: ${file.filePOwerNm || '-'}
크기: ${formatFileSize(file.filesize || 0)}
확장자: ${file.fileExtNm || '-'}
버전: ${file.fileVerNm || '-'}
등록일: ${formatDate(file.objtRegDtm)}

※ 실제 문서 내용은 EDM 다운로드 API를 통해 표시됩니다.`;

			isLoadingPreview = false;
		} catch (error) {
			console.error('❌ 문서 미리보기 실패:', error);
			toast.error(`문서 미리보기 실패: ${error.message}`);
			isLoadingPreview = false;
			closePreview();
		}
	}

	// 미리보기 닫기
	function closePreview() {
		showPreview = false;
		previewFile = null;
		previewContent = '';
	}

	// 파일 선택/해제
	function toggleFileSelection(objid: string, file: any) {
		const action = selectedFiles.includes(objid) ? 'deselect' : 'select';
		console.log('🔵 [파일 선택/해제]', {
			timestamp: new Date().toISOString(),
			action: action,
			objid: objid,
			fileName: file.objtNm,
			hasPermission: hasPermission(file),
			selectedCount: action === 'select' ? selectedFiles.length + 1 : selectedFiles.length - 1
		});

		if (!hasPermission(file)) {
			toast.error('이 파일에 대한 권한이 없습니다.');
			return;
		}

		if (selectedFiles.includes(objid)) {
			selectedFiles = selectedFiles.filter((id) => id !== objid);
		} else {
			// 최대 3개까지만 선택 가능
			if (selectedFiles.length >= 3) {
				toast.error('문서는 최대 3개까지만 선택 가능합니다.');
				return;
			}
			selectedFiles = [...selectedFiles, objid];
		}
	}

	// 전체 선택 (최대 3개까지)
	function selectAll() {
		const selectableFiles = files.filter(hasPermission);
		selectedFiles = selectableFiles.slice(0, 3).map((f) => f.objid);
		if (selectableFiles.length > 3) {
			toast.info('최대 3개 파일만 선택되었습니다.');
		}
	}

	// 전체 해제
	function deselectAll() {
		selectedFiles = [];
	}

	// 파일 지식화 (CustomEvent 방식으로 Chat.svelte에 위임)
	async function handleApply() {
		console.log('🔵 [지식화 버튼 클릭]', {
			timestamp: new Date().toISOString(),
			action: 'knowledge_button_clicked',
			selectedFilesCount: selectedFiles.length,
			selectedFiles: selectedFiles
		});

		if (selectedFiles.length === 0) {
			toast.error('최소 1개 이상의 파일을 선택해주세요.');
			return;
		}

		const selectedFileObjects = files.filter((f) => selectedFiles.includes(f.objid));

		// 📋 선택된 파일 리스트 상세 로그
		console.log("=" + "=".repeat(79));
		console.log('📋 [COMPONENT] EdmFileListModal.svelte');
		console.log('📋 [ACTION] 사용자가 지식화할 파일 선택 완료');
		console.log(`📋 [SELECTED_FILES_COUNT] ${selectedFileObjects.length}개 파일`);
		selectedFileObjects.forEach((file, idx) => {
			console.log(`📄 [SELECTED_FILE_${idx + 1}] objid=${file.objid}, name=${file.objtNm}, workspace=${file.workspaceNm}`);
		});
		console.log("=" + "=".repeat(79));

		try {
			// 다운로드 요청 데이터 구성
			const edmFiles = selectedFileObjects.map((file) => ({
				objid: file.objid,
				fileLastVerSno: file.fileLastVerSno || file.flieLasVerSno || 1,
				requestUser: file.requestUser || 'system',
				fileName: file.objtNm
			}));

			console.log('🔵 [CustomEvent 발생] edm-knowledge-request', {
				timestamp: new Date().toISOString(),
				filesCount: edmFiles.length,
				files: edmFiles
			});

			// CustomEvent를 발생시켜 Chat.svelte로 전달
			const event = new CustomEvent('edm-knowledge-request', {
				detail: {
					files: edmFiles,
					message: `EDM 파일 ${edmFiles.length}개를 지식화합니다.`
				}
			});
			window.dispatchEvent(event);

			// 모달 닫기
			close();

			toast.success(`${edmFiles.length}개 파일 지식화를 시작합니다. 채팅 화면을 확인하세요.`);
		} catch (error) {
			console.error('❌ 파일 지식화 실패:', error);
			toast.error(`파일 지식화 중 오류: ${error.message}`);
		}
	}

	// 모달 닫기
	function close() {
		show = false;
		selectedFiles = [];
		dispatch('close');
	}

	// ESC 키로 닫기
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	// 파일 크기 포맷
	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
	}

	// 날짜 포맷
	function formatDate(timestamp: number): string {
		if (!timestamp) return '-';
		const date = new Date(timestamp);
		return date.toLocaleDateString('ko-KR', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	onMount(() => {
		if (show) {
			document.addEventListener('keydown', handleKeydown);
		}
		return () => {
			document.removeEventListener('keydown', handleKeydown);
		};
	});
</script>

{#if show}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
		on:click={close}
		on:keydown={(e) => e.key === 'Escape' && close()}
		role="dialog"
		aria-modal="true"
		aria-labelledby="edm-file-modal-title"
	>
		<div
			class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-7xl w-full mx-4 max-h-[92vh] flex flex-col border border-gray-200 dark:border-gray-700"
			role="document"
			on:click|stopPropagation
			on:keydown|stopPropagation
		>
			<!-- Header -->
			<div class="flex items-center justify-between p-6 pb-4 border-b dark:border-gray-800">
				<div>
					<h2 id="edm-file-modal-title" class="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
						<svg
							class="w-7 h-7 text-blue-600 dark:text-blue-500"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
							/>
						</svg>
						EDM 파일 검색 결과
					</h2>
					<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
						지식화할 파일을 선택하세요 • 총 <span class="font-semibold"
							>{files.length}</span
						>개 파일
					</p>
				</div>
				<button
					on:click={close}
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
					aria-label="닫기"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

		<!-- Toolbar -->
		<div
			class="flex items-center justify-between px-6 py-3 bg-gray-50 dark:bg-gray-800/50 border-b dark:border-gray-800 gap-4"
		>
			<div class="flex gap-2">
				<button
					on:click={selectAll}
					class="px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-gray-700/50 rounded-lg transition-all duration-200 border border-blue-200 dark:border-blue-900/30"
				>
					<span class="flex items-center gap-1.5">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						전체 선택
					</span>
				</button>
				<button
					on:click={deselectAll}
					class="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700/50 rounded-lg transition-all duration-200 border border-gray-300 dark:border-gray-700"
				>
					선택 해제
				</button>
			</div>
			<div class="flex-1"></div>
			<div class="flex items-center gap-4">
				<p class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
					문서는 총 <span class="font-semibold text-blue-600 dark:text-blue-400">3개까지</span> 선택 가능합니다.
					<span class="text-gray-400 dark:text-gray-500">(파일용량 제한 : 20MB)</span>
				</p>
				<div
					class="flex items-center gap-2 text-sm px-4 py-1.5 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700"
				>
					<span class="text-gray-600 dark:text-gray-400">선택됨:</span>
					<span class="font-bold text-blue-600 dark:text-blue-400">{selectedFiles.length}</span>
					<span class="text-gray-400">/ {files.length}개</span>
				</div>
			</div>
		</div>

			<!-- File List -->
			<div class="flex-1 overflow-y-auto p-6 bg-gray-50/50 dark:bg-gray-900/30">
				{#if files.length === 0}
					<div class="text-center py-20">
						<svg
							class="mx-auto w-16 h-16 text-gray-400 dark:text-gray-600 mb-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<p class="text-lg font-medium text-gray-500 dark:text-gray-400">
							검색 결과가 없습니다
						</p>
						<p class="text-sm text-gray-400 dark:text-gray-500 mt-2">
							다른 검색어로 시도해보세요
						</p>
					</div>
				{:else}
					<div class="space-y-3">
						{#each files as file (file.objid)}
							{@const permitted = hasPermission(file)}
							{@const selected = selectedFiles.includes(file.objid)}
							<div
								class="flex items-start gap-4 p-5 rounded-xl border-2 transition-all duration-200 {permitted
									? 'hover:bg-white dark:hover:bg-gray-800 cursor-pointer border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-md'
									: 'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600 opacity-60 cursor-not-allowed'} {selected
									? 'ring-2 ring-blue-500 dark:ring-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-600 shadow-lg'
									: 'bg-white dark:bg-gray-900'}"
								on:click={() => toggleFileSelection(file.objid, file)}
								role="button"
								tabindex="0"
								on:keydown={(e) => {
									if (e.key === 'Enter' || e.key === ' ') {
										toggleFileSelection(file.objid, file);
									}
								}}
							>
								<!-- Checkbox -->
								<div class="flex items-center pt-1">
									<input
										type="checkbox"
										checked={selected}
										disabled={!permitted}
										class="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600 dark:focus:ring-blue-400"
										on:click|stopPropagation={() => toggleFileSelection(file.objid, file)}
									/>
								</div>

								<!-- File Icon -->
								<div class="flex-shrink-0 pt-1">
									<svg
										class="w-8 h-8 {permitted
											? 'text-blue-500 dark:text-blue-400'
											: 'text-gray-400 dark:text-gray-600'}"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
										/>
									</svg>
								</div>

								<!-- File Info -->
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<h3
											class="font-semibold text-gray-900 dark:text-white truncate {!permitted
												? 'line-through'
												: ''}"
										>
											{file.objtNm}
										</h3>
										<span
											class="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded {permitted
												? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
												: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}"
										>
											{permitted ? '권한 있음' : '권한 없음'}
										</span>
									</div>

									<div class="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1 text-sm">
										<div>
											<span class="text-gray-500 dark:text-gray-400">워크스페이스:</span>
											<span class="ml-1 text-gray-900 dark:text-white"
												>{file.workspaceNm || '-'}</span
											>
										</div>
										<div>
											<span class="text-gray-500 dark:text-gray-400">소유자:</span>
											<span class="ml-1 text-gray-900 dark:text-white"
												>{file.filePOwerNm || '-'}</span
											>
										</div>
										<div>
											<span class="text-gray-500 dark:text-gray-400">크기:</span>
											<span class="ml-1 text-gray-900 dark:text-white"
												>{formatFileSize(file.filesize || 0)}</span
											>
										</div>
										<div>
											<span class="text-gray-500 dark:text-gray-400">확장자:</span>
											<span class="ml-1 text-gray-900 dark:text-white"
												>{file.fileExtNm || '-'}</span
											>
										</div>
										<div>
											<span class="text-gray-500 dark:text-gray-400">버전:</span>
											<span class="ml-1 text-gray-900 dark:text-white"
												>{file.fileVerNm || '-'}</span
											>
										</div>
										<div>
											<span class="text-gray-500 dark:text-gray-400">등록일:</span>
											<span class="ml-1 text-gray-900 dark:text-white"
												>{formatDate(file.objtRegDtm)}</span
											>
										</div>
										<div>
											<span class="text-gray-500 dark:text-gray-400">수정일:</span>
											<span class="ml-1 text-gray-900 dark:text-white"
												>{formatDate(file.objtStatChgDtm)}</span
											>
										</div>
										<div>
											<span class="text-gray-500 dark:text-gray-400">만료:</span>
											<span class="ml-1 text-gray-900 dark:text-white"
												>{file.prsrvTermExpireYn === 'Y' ? '만료됨' : '유효'}</span
											>
										</div>
									</div>
								</div>
								<!-- View Document Button -->
								<div class="flex-shrink-0 pt-1">
									<button
										on:click|stopPropagation={() => viewDocument(file)}
										disabled={!permitted}
										class="px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/30 rounded-lg transition-all duration-200 border border-blue-200 dark:border-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
										type="button"
										title="문서 미리보기"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
										</svg>
										문서보기
									</button>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div
				class="flex items-center justify-between px-6 py-5 border-t dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50"
			>
				<div class="text-sm text-gray-600 dark:text-gray-400">
					{#if selectedFiles.length > 0}
						<span class="flex items-center gap-2">
							<svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							<div class="flex flex-col">
								<span class="font-medium">{selectedFiles.length}개 파일 선택됨</span>
								<span class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
									파싱 → 청킹 → 임베딩 → 벡터 DB 저장
								</span>
							</div>
						</span>
					{:else}
						<div class="flex flex-col">
							<span class="text-gray-500 dark:text-gray-400">파일을 선택해주세요</span>
							<span class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
								지식화 시 자동으로 벡터화 파이프라인 처리 (파싱 → 청킹 → 임베딩 → Milvus 저장)
							</span>
						</div>
					{/if}
				</div>
				<div class="flex items-center gap-3">
					<button
						on:click={close}
						class="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700 transition-all duration-200 hover:shadow-sm"
					>
						취소
					</button>
					<button
						on:click={handleApply}
						disabled={selectedFiles.length === 0}
						class="px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed dark:from-blue-500 dark:to-blue-600 dark:hover:from-blue-600 dark:hover:to-blue-700 transition-all duration-200 shadow-md hover:shadow-lg transform hover:scale-105 active:scale-95 flex items-center gap-2"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M5 13l4 4L19 7"
							/>
						</svg>
						지식화 ({selectedFiles.length}개)
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Document Preview Modal -->
{#if showPreview}
	<div
		class="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm"
		on:click={closePreview}
		on:keydown={(e) => e.key === 'Escape' && closePreview()}
		role="dialog"
		aria-modal="true"
	>
		<div
			class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-4xl w-full mx-4 max-h-[85vh] flex flex-col border border-gray-200 dark:border-gray-700"
			on:click|stopPropagation
			on:keydown|stopPropagation
		>
			<!-- Preview Header -->
			<div class="flex items-center justify-between p-6 pb-4 border-b dark:border-gray-800">
				<div>
					<h2 class="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
						<svg class="w-6 h-6 text-blue-600 dark:text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						문서 미리보기
					</h2>
					{#if previewFile}
						<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
							{previewFile.objtNm}
						</p>
					{/if}
				</div>
				<button
					on:click={closePreview}
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Preview Content -->
			<div class="flex-1 overflow-y-auto p-6 bg-gray-50/50 dark:bg-gray-900/30">
				{#if isLoadingPreview}
					<div class="flex items-center justify-center h-full">
						<div class="text-center">
							<svg class="animate-spin h-12 w-12 text-blue-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							<p class="text-gray-600 dark:text-gray-400">문서 로딩 중...</p>
						</div>
					</div>
				{:else}
					<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
						<pre class="whitespace-pre-wrap text-sm text-gray-900 dark:text-gray-100 font-mono">{previewContent}</pre>
					</div>
				{/if}
			</div>

			<!-- Preview Footer -->
			<div class="flex items-center justify-end px-6 py-4 border-t dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
				<button
					on:click={closePreview}
					class="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700 transition-all duration-200"
				>
					닫기
				</button>
			</div>
		</div>
	</div>
{/if}
