<script lang="ts">
	import { searchByDataType, type SearchResult } from '$lib/apis/rag-search';
	import { onMount } from 'svelte';

	let query = '';
	let searchLevel: 1 | 2 | 3 = 2;
	let results: SearchResult[] = [];
	let loading = false;
	let error = '';
	let totalTerms = 0;
	let categories = 0;

	// 필터
	let filters = {
		tech: true,
		business: true,
		acronym: true
	};

	async function handleSearch() {
		if (!query.trim()) return;

		loading = true;
		error = '';

		try {
			const response = await searchByDataType(query, 'term', searchLevel);
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
		// 통계 로드 (실제로는 API에서)
		totalTerms = 1234;
		categories = 12;
	});
</script>

<div class="flex flex-col h-full">
	<!-- 헤더 -->
	<div class="mb-4">
		<h2 class="text-2xl font-semibold flex items-center gap-2">
			📖 용어사전 검색
		</h2>
		<p class="text-sm text-gray-500 mt-1">기술 용어, 약어, 정의를 검색하세요</p>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
		<!-- 검색 패널 -->
		<div class="flex flex-col gap-4">
			<!-- 통계 -->
			<div class="grid grid-cols-3 gap-3">
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{totalTerms}</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">전체 용어</div>
				</div>
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{categories}</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">카테고리</div>
				</div>
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{results.length}</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">검색 결과</div>
				</div>
			</div>

			<!-- 검색 폼 -->
			<div class="bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
				<div class="space-y-4">
					<!-- 검색어 입력 -->
					<div>
						<label class="block text-sm font-medium mb-2">용어 또는 약어 검색</label>
						<input
							type="text"
							bind:value={query}
							on:keypress={handleKeyPress}
							placeholder="예: API, REST, JWT..."
							class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<!-- 카테고리 필터 -->
					<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
						<h3 class="text-sm font-medium mb-3">카테고리 필터</h3>
						<div class="space-y-2">
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={filters.tech} class="rounded" />
								<span class="text-sm">기술 용어</span>
							</label>
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={filters.business} class="rounded" />
								<span class="text-sm">비즈니스 용어</span>
							</label>
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={filters.acronym} class="rounded" />
								<span class="text-sm">약어</span>
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
							<option value={1}>⚡ Level 1 - 빠른 검색</option>
							<option value={2}>⚖️ Level 2 - 균형 검색</option>
							<option value={3}>🎯 Level 3 - 정밀 검색</option>
						</select>
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
							🔍 용어 검색
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
					<div class="text-6xl mb-4">📖</div>
					<p>용어를 검색하여 정의를 확인하세요</p>
				</div>
			{:else}
				<div class="space-y-3 max-h-[600px] overflow-y-auto">
					{#each results as result, idx}
						<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border-l-4 border-blue-500">
							<div class="flex items-start justify-between mb-2">
								<div class="font-semibold text-lg">{result.metadata?.term || '용어'}</div>
								<div class="bg-blue-600 text-white text-xs px-2 py-1 rounded-full">
									{((result.final_score || result.score) * 100).toFixed(1)}%
								</div>
							</div>

							<div class="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400 mb-2">
								<span>📖 {result.doc_id}</span>
								<span>🏷️ {result.metadata?.category || '일반'}</span>
							</div>

							<div class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
								{result.text}
							</div>

							{#if result.metadata?.tags}
								<div class="flex flex-wrap gap-2 mt-3">
									{#each result.metadata.tags as tag}
										<span class="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs px-2 py-1 rounded">
											{tag}
										</span>
									{/each}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>
