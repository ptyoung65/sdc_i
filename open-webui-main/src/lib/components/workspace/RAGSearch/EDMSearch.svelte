<script lang="ts">
	import { searchByDataType, type SearchResult } from '$lib/apis/rag-search';
	import { onMount } from 'svelte';

	let query = '';
	let searchLevel: 2 | 3 = 3;
	let useGraph = true;
	let results: SearchResult[] = [];
	let loading = false;
	let error = '';
	let totalDocs = 0;
	let totalPatents = 0;
	let totalCitations = 0;

	// 필터
	let docTypes = {
		patent: true,
		research: true,
		technical: true,
		report: true
	};

	async function handleSearch() {
		if (!query.trim()) return;

		loading = true;
		error = '';

		try {
			const response = await searchByDataType(query, 'edm', searchLevel);
			results = response.results;
		} catch (err: any) {
			error = err.message || '검색 중 오류가 발생했습니다';
			results = [];
		} finally {
			loading = false;
		}
	}

	function handleKeyPress(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			handleSearch();
		}
	}

	onMount(() => {
		totalDocs = 456;
		totalPatents = 123;
		totalCitations = 789;
	});
</script>

<div class="flex flex-col h-full">
	<!-- 헤더 -->
	<div class="mb-4">
		<h2 class="text-2xl font-semibold flex items-center gap-2">
			📄 EDM 문서 검색
		</h2>
		<p class="text-sm text-gray-500 mt-1">특허, 논문, 기술 문서를 검색하세요</p>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
		<!-- 검색 패널 -->
		<div class="flex flex-col gap-4">
			<!-- 통계 -->
			<div class="grid grid-cols-3 gap-3">
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{totalDocs}</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">문서 수</div>
				</div>
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{totalPatents}</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">특허</div>
				</div>
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{totalCitations}</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">인용 관계</div>
				</div>
			</div>

			<!-- 검색 폼 -->
			<div class="bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
				<div class="space-y-4">
					<!-- 검색어 입력 -->
					<div>
						<label class="block text-sm font-medium mb-2">문서 또는 기술 검색</label>
						<textarea
							bind:value={query}
							on:keypress={handleKeyPress}
							placeholder="예: AI 검색 시스템, 자연어 처리, 벡터 데이터베이스..."
							rows="4"
							class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<!-- 문서 유형 필터 -->
					<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
						<h3 class="text-sm font-medium mb-3">문서 유형</h3>
						<div class="space-y-2">
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={docTypes.patent} class="rounded" />
								<span class="text-sm">특허</span>
							</label>
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={docTypes.research} class="rounded" />
								<span class="text-sm">연구 논문</span>
							</label>
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={docTypes.technical} class="rounded" />
								<span class="text-sm">기술 문서</span>
							</label>
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={docTypes.report} class="rounded" />
								<span class="text-sm">보고서</span>
							</label>
						</div>
					</div>

					<!-- 검색 레벨 -->
					<div>
						<label class="block text-sm font-medium mb-2">검색 레벨</label>
						<select
							bind:value={searchLevel}
							class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
						>
							<option value={2}>⚖️ Level 2 - 균형 검색</option>
							<option value={3}>🎯 Level 3 - 정밀 검색 (Multi-Hop)</option>
						</select>
					</div>

					<!-- Multi-Hop 옵션 -->
					<div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
						<label class="flex items-start gap-3 cursor-pointer">
							<input type="checkbox" bind:checked={useGraph} class="mt-1 rounded" />
							<div>
								<div class="text-sm font-medium text-blue-900 dark:text-blue-100">
									인용 그래프 탐색 (Multi-Hop Retrieval)
								</div>
								<div class="text-xs text-blue-700 dark:text-blue-300 mt-1">
									관련 문서의 인용 관계를 따라 추가 검색을 수행합니다
								</div>
							</div>
						</label>
					</div>

					<!-- 검색 버튼 -->
					<button
						on:click={handleSearch}
						disabled={loading || !query.trim()}
						class="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
					>
						{#if loading}
							<span class="flex items-center justify-center gap-2">
								<svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
								</svg>
								<span>검색 중...</span>
							</span>
						{:else}
							🔍 문서 검색
						{/if}
					</button>
				</div>
			</div>
		</div>

		<!-- 검색 결과 -->
		<div class="bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
				검색 결과
				<span class="text-sm text-gray-500">({results.length}개)</span>
			</h3>

			{#if error}
				<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg">
					❌ {error}
				</div>
			{:else if results.length === 0}
				<div class="text-center py-12 text-gray-500">
					<div class="text-6xl mb-4">📄</div>
					<p>EDM 문서를 검색하세요</p>
				</div>
			{:else}
				<div class="space-y-3 max-h-[600px] overflow-y-auto">
					{#each results as result, idx}
						<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border-l-4 border-purple-500">
							<div class="flex items-start justify-between mb-2">
								<div class="font-semibold text-lg flex items-center gap-2">
									<span>📄</span>
									<span class="flex-1">{result.metadata?.title || 'EDM 문서'}</span>
								</div>
								<div class="bg-purple-600 text-white text-xs px-2 py-1 rounded-full whitespace-nowrap">
									{((result.final_score || result.score) * 100).toFixed(1)}%
								</div>
							</div>

							<div class="flex items-center flex-wrap gap-2 text-xs text-gray-600 dark:text-gray-400 mb-2">
								<span>🏷️ {result.metadata?.doc_type || '문서'}</span>
								<span>📅 {result.metadata?.filing_date || 'N/A'}</span>
								<span>👤 {result.metadata?.inventor || result.metadata?.author || '저자'}</span>
							</div>

							<div class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-3">
								{result.text}
							</div>

							<div class="flex flex-wrap gap-2">
								{#if result.metadata?.patent_number}
									<span class="bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 text-xs px-2 py-1 rounded">
										🔢 {result.metadata.patent_number}
									</span>
								{/if}
								{#if result.metadata?.citations}
									<span class="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs px-2 py-1 rounded">
										📎 인용 {result.metadata.citations}건
									</span>
								{/if}
								{#if result.metadata?.ipc_code}
									<span class="bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-xs px-2 py-1 rounded">
										IPC: {result.metadata.ipc_code}
									</span>
								{/if}
								{#if result.metadata?.classification}
									<span class="bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 text-xs px-2 py-1 rounded">
										{result.metadata.classification}
									</span>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>
