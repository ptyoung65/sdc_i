<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';

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
	import { toast } from 'svelte-sonner';

	export let files: any[] = [];
	export let show: boolean = false;

	const dispatch = createEventDispatcher();

	let selectedFiles: string[] = [];

	// 권한이 있는 파일만 선택 가능
	function hasPermission(file: any): boolean {
		return file.maxObjtSharePolicyId !== null && file.maxObjtSharePolicyId !== undefined;
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
			selectedFiles = [...selectedFiles, objid];
		}
	}

	// 전체 선택
	function selectAll() {
		const selectableFiles = files.filter(hasPermission);
		selectedFiles = selectableFiles.map((f) => f.objid);
	}

	// 전체 해제
	function deselectAll() {
		selectedFiles = [];
	}

	// 파일 지식화 (다운로드 → 파싱 → 청킹 → 임베딩 → Milvus 저장)
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

		try {
			// 1. edm_download 파이프 존재 여부 확인 (필수)
			const downloadPipeName = 'edm_download';
			
			console.log('🔵 [파이프 존재 여부 확인]', {
				timestamp: new Date().toISOString(),
				action: 'check_pipe_exists',
				requiredPipe: downloadPipeName
			});

			// 파이프 목록 가져오기
			const pipesResponse = await fetch('/api/pipelines', {
				headers: {
					'Authorization': `Bearer ${localStorage.token}`
				}
			});

			if (!pipesResponse.ok) {
				throw new Error('파이프 목록을 가져올 수 없습니다.');
			}

			const pipesData = await pipesResponse.json();
			const availablePipes = pipesData.data || pipesData || [];
			const pipeExists = availablePipes.some(p => p.id === downloadPipeName);

			if (!pipeExists) {
				console.error('🔴 [파이프 없음 오류]', {
					timestamp: new Date().toISOString(),
					requiredPipe: downloadPipeName,
					availablePipes: availablePipes.map(p => p.id)
				});
				throw new Error(`❌ 지식화를 위해서는 ${downloadPipeName} 파이프가 필요합니다. 파이프를 등록해주세요.`);
			}

			console.log('🟢 [파이프 확인 완료]', {
				timestamp: new Date().toISOString(),
				pipeName: downloadPipeName,
				status: 'exists'
			});

			// 2. 파일 다운로드 시작
			toast.info(`${selectedFileObjects.length}개 파일 다운로드 중...`);
			const downloadResults = [];

			for (const file of selectedFileObjects) {
				try {
					const downloadPayload = {
						objid: file.objid,
						objtNm: file.objtNm,
						workspaceNm: file.workspaceNm
					};

									console.log('🔵 [edm_download 호출]', {
					timestamp: new Date().toISOString(),
					action: 'download_pipe_call',
					pipeName: downloadPipeName,
					payload: downloadPayload
				});

				const downloadResponse = await fetch(`/api/pipelines/${downloadPipeName}`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							'Authorization': `Bearer ${localStorage.token}`
						},
						body: JSON.stringify(downloadPayload)
					});

					if (!downloadResponse.ok) {
						throw new Error(`다운로드 실패: ${downloadResponse.status}`);
					}

					const downloadResult = await downloadResponse.json();
					console.log('🟢 [파일 다운로드 성공]', {
					timestamp: new Date().toISOString(),
					action: 'download_success',
					objid: file.objid,
					fileName: downloadResult.fileName || downloadResult.filename,
					filePath: downloadResult.filePath || downloadResult.filepath,
					response: downloadResult
				});

					// 파일명, 파일경로 포함
					downloadResults.push({
						...file,
						fileName: downloadResult.fileName || downloadResult.filename,
						filePath: downloadResult.filePath || downloadResult.filepath,
						downloadSuccess: true
					});
				} catch (error) {
					console.error('🔴 [파일 다운로드 실패]', {
					timestamp: new Date().toISOString(),
					action: 'download_error',
					objid: file.objid,
					fileName: file.objtNm,
					error: error.message,
					stack: error.stack
				});
					downloadResults.push({
						...file,
						downloadSuccess: false,
						error: error.message
					});
				}
			}

			// 다운로드 성공한 파일만 임베딩 처리
			const successFiles = downloadResults.filter(f => f.downloadSuccess);

			if (successFiles.length === 0) {
				toast.error('모든 파일 다운로드에 실패했습니다.');
				return;
			}

			toast.success(`${successFiles.length}개 파일 다운로드 완료. 임베딩 처리 중...`);

			// 임베딩 이벤트 발송 (Chat.svelte에서 처리)
			console.log('🔵 [dispatch embed 이벤트]', {
				timestamp: new Date().toISOString(),
				action: 'dispatch_embed',
				successFilesCount: successFiles.length,
				successFiles: successFiles.map(f => ({
					objid: f.objid,
					fileName: f.fileName,
					filePath: f.filePath
				}))
			});

			dispatch('embed', {
				files: successFiles
			});

			close();
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
				class="flex items-center justify-between px-6 py-3 bg-gray-50 dark:bg-gray-800/50 border-b dark:border-gray-800"
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
				<div
					class="flex items-center gap-2 text-sm px-4 py-1.5 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700"
				>
					<span class="text-gray-600 dark:text-gray-400">선택됨:</span>
					<span class="font-bold text-blue-600 dark:text-blue-400">{selectedFiles.length}</span>
					<span class="text-gray-400">/ {files.length}개</span>
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
										on:click|stopPropagation
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
