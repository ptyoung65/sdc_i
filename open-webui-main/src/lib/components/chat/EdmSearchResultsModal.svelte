<script lang="ts">
	import Modal from '../common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { toast } from 'svelte-sonner';

	export let show = true;
	export let results = [];

	// 선택된 문서들
	let selectedDocs = [];

	// 지식화 진행 상태
	let knowledgingStatus = 'idle'; // 'idle' | 'processing' | 'completed'
	let knowledgingProgress = 0;

	// 문서 타입별 아이콘
	const getFileIcon = (fileType: string) => {
		const type = (fileType || '').toLowerCase();
		if (type.includes('excel') || type.includes('xlsx') || type.includes('xls')) {
			return '📊';
		} else if (type.includes('powerpoint') || type.includes('pptx') || type.includes('ppt')) {
			return '📽️';
		} else if (type.includes('word') || type.includes('docx') || type.includes('doc')) {
			return '📄';
		} else if (type.includes('pdf')) {
			return '📕';
		}
		return '📋';
	};

	// 문서 타입명 정리
	const getFileTypeName = (fileType: string) => {
		const type = (fileType || '').toLowerCase();
		if (type.includes('excel') || type.includes('xlsx') || type.includes('xls')) return 'Excel';
		if (type.includes('powerpoint') || type.includes('pptx') || type.includes('ppt'))
			return 'PowerPoint';
		if (type.includes('word') || type.includes('docx') || type.includes('doc')) return 'Word';
		if (type.includes('pdf')) return 'PDF';
		return fileType || '문서';
	};

	// 체크박스 토글
	const toggleSelection = (doc: any) => {
		const docId = doc.FILE_ID || doc.id || doc.FILE_NAME || doc.fileName;
		const index = selectedDocs.findIndex((d) => {
			const id = d.FILE_ID || d.id || d.FILE_NAME || d.fileName;
			return id === docId;
		});

		if (index > -1) {
			selectedDocs = selectedDocs.filter((_, i) => i !== index);
		} else {
			selectedDocs = [...selectedDocs, doc];
		}
	};

	// 선택 여부 확인
	const isSelected = (doc: any) => {
		const docId = doc.FILE_ID || doc.id || doc.FILE_NAME || doc.fileName;
		return selectedDocs.some((d) => {
			const id = d.FILE_ID || d.id || d.FILE_NAME || d.fileName;
			return id === docId;
		});
	};

	// 전체 선택/해제
	const toggleSelectAll = () => {
		if (selectedDocs.length === results.length) {
			selectedDocs = [];
		} else {
			selectedDocs = [...results];
		}
	};

	// 지식화 시작
	const startKnowledging = async () => {
		if (selectedDocs.length === 0) {
			toast.error('지식화할 문서를 선택해주세요.');
			return;
		}

		knowledgingStatus = 'processing';
		knowledgingProgress = 0;

		// 지식화 진행 시뮬레이션
		const totalDocs = selectedDocs.length;
		for (let i = 0; i < totalDocs; i++) {
			await new Promise((resolve) => setTimeout(resolve, 500)); // 실제로는 API 호출
			knowledgingProgress = Math.round(((i + 1) / totalDocs) * 100);
		}

		knowledgingStatus = 'completed';
		toast.success(`${selectedDocs.length}건의 문서가 지식화되었습니다.`);
	};

	// 모달 닫기
	const handleClose = () => {
		if (knowledgingStatus === 'processing') {
			toast.error('지식화 진행 중에는 닫을 수 없습니다.');
			return;
		}
		show = false;
	};
</script>

<Modal bind:show size="2xl">
	<div>
		<!-- 헤더 -->
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div>
				<div class="text-lg font-medium self-center">EDM 문서 검색 결과</div>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					총 {results.length}건의 문서 | 선택됨: {selectedDocs.length}건
				</p>
			</div>
			<button
				class="self-center"
				on:click={handleClose}
				disabled={knowledgingStatus === 'processing'}
				aria-label="Close"
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<!-- 문서 목록 -->
		<div class="flex flex-col px-5 pb-5 max-h-[60vh] overflow-y-auto">
			{#if results && results.length > 0}
				<!-- 전체 선택 -->
				<div class="flex items-center gap-3 mb-3 pb-3 border-b dark:border-gray-700">
					<input
						type="checkbox"
						checked={selectedDocs.length === results.length && results.length > 0}
						on:change={toggleSelectAll}
						class="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
						disabled={knowledgingStatus === 'processing'}
					/>
					<span class="text-xs font-medium dark:text-gray-300">전체 선택</span>
				</div>

				<!-- 문서 리스트 -->
				<div class="space-y-2">
					{#each results as doc, index}
						<div
							class="bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-lg p-3 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all {isSelected(
								doc
							)
								? 'ring-1 ring-blue-500'
								: ''}"
						>
							<div class="flex items-start gap-3">
								<!-- 체크박스 -->
								<div class="flex-shrink-0 pt-1">
									<input
										type="checkbox"
										checked={isSelected(doc)}
										on:change={() => toggleSelection(doc)}
										class="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
										disabled={knowledgingStatus === 'processing'}
									/>
								</div>

								<!-- 문서 아이콘 -->
								<div class="flex-shrink-0 text-2xl">{getFileIcon(doc.FILE_TYPE || doc.fileType || '')}</div>

								<!-- 문서 정보 -->
								<div class="flex-1 min-w-0">
									<!-- 문서명 -->
									<h3 class="text-sm font-semibold dark:text-gray-100 mb-1.5">
										{doc.FILE_NAME || doc.fileName || '제목 없음'}
									</h3>

									<!-- 메타 정보 -->
									<div class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
										<!-- 문서 종류 -->
										<div class="flex items-center gap-1.5">
											<span class="text-gray-500 dark:text-gray-400">문서종류:</span>
											<span class="dark:text-gray-300">
												{getFileTypeName(doc.FILE_TYPE || doc.fileType || '')}
											</span>
										</div>

										<!-- 작성자 -->
										<div class="flex items-center gap-1.5">
											<span class="text-gray-500 dark:text-gray-400">작성자:</span>
											<span class="dark:text-gray-300">
												{doc.AUTHOR || doc.author || '작성자 미상'}
											</span>
										</div>

										<!-- 작성일 -->
										<div class="flex items-center gap-1.5">
											<span class="text-gray-500 dark:text-gray-400">작성일:</span>
											<span class="dark:text-gray-300">
												{doc.CREATE_DATE || doc.createDate || '-'}
											</span>
										</div>

										<!-- 파일 크기 -->
										{#if doc.FILE_SIZE || doc.fileSize}
											<div class="flex items-center gap-1.5">
												<span class="text-gray-500 dark:text-gray-400">파일크기:</span>
												<span class="dark:text-gray-300">
													{doc.FILE_SIZE || doc.fileSize}
												</span>
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>
					{/each}
				</div>

				<!-- Mock 문서 보기 링크 -->
				<div class="mt-4 pt-3 border-t dark:border-gray-700 text-center">
					<a
						href="/api/edm/mock-documents"
						target="_blank"
						class="text-sm text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
					>
						<svg
							class="w-4 h-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
							/>
						</svg>
						Mock 문서 전체 보기
					</a>
				</div>
			{:else}
				<div class="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
					검색 결과가 없습니다.
				</div>
			{/if}
		</div>

		<!-- 하단 액션 영역 -->
		<div class="px-5 pb-4 pt-3 border-t dark:border-gray-700">
			{#if knowledgingStatus === 'idle'}
				<!-- 초기 상태: 지식화 버튼 -->
				<div class="flex items-center justify-between">
					<div class="text-xs text-gray-600 dark:text-gray-400">
						<span class="font-medium text-blue-600 dark:text-blue-400">{selectedDocs.length}건</span
						>의 문서가 선택되었습니다.
					</div>
					<div class="flex gap-2">
						<button
							on:click={handleClose}
							class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-800 transition rounded-full"
						>
							닫기
						</button>
						<button
							on:click={startKnowledging}
							disabled={selectedDocs.length === 0}
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition rounded-full"
						>
							지식화
						</button>
					</div>
				</div>
			{:else if knowledgingStatus === 'processing'}
				<!-- 지식화 진행 중 -->
				<div class="space-y-3">
					<div class="flex items-center justify-between text-xs">
						<span class="dark:text-gray-300 font-medium">지식화 진행 중...</span>
						<span class="text-blue-600 dark:text-blue-400 font-bold">{knowledgingProgress}%</span>
					</div>
					<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
						<div
							class="bg-blue-600 dark:bg-blue-500 h-full transition-all duration-300 rounded-full"
							style="width: {knowledgingProgress}%"
						></div>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 text-center">
						{selectedDocs.length}건의 문서를 지식 베이스에 추가하고 있습니다...
					</p>
				</div>
			{:else if knowledgingStatus === 'completed'}
				<!-- 지식화 완료 -->
				<div class="space-y-3">
					<div class="flex items-center justify-center gap-2 text-green-600 dark:text-green-400">
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<span class="text-base font-bold">지식화 완료!</span>
					</div>
					<p class="text-xs text-gray-600 dark:text-gray-400 text-center">
						{selectedDocs.length}건의 문서가 성공적으로 지식 베이스에 추가되었습니다.
					</p>
					<div class="flex justify-center pt-1">
						<button
							on:click={handleClose}
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						>
							종료
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>
</Modal>
