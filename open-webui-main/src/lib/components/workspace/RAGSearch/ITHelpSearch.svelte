<script lang="ts">
	import { searchByDataType, type SearchResult } from '$lib/apis/rag-search';
	import { onMount } from 'svelte';

	let query = '';
	let priority = '';
	let results: SearchResult[] = [];
	let loading = false;
	let error = '';
	let totalCases = 0;
	let avgRating = 4.5;

	// 필터
	let problemTypes = {
		login: true,
		network: true,
		software: true,
		hardware: true
	};

	async function handleSearch() {
		if (!query.trim()) return;

		loading = true;
		error = '';

		try {
			const response = await searchByDataType(query, 'ithelp', 2);
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

	function getPriorityColor(p: string) {
		switch (p) {
			case 'high':
				return 'text-red-600 dark:text-red-400';
			case 'medium':
				return 'text-yellow-600 dark:text-yellow-400';
			case 'low':
				return 'text-green-600 dark:text-green-400';
			default:
				return 'text-gray-600 dark:text-gray-400';
		}
	}

	function getPriorityIcon(p: string) {
		switch (p) {
			case 'high':
				return '🔴';
			case 'medium':
				return '🟡';
			case 'low':
				return '🟢';
			default:
				return '⚪';
		}
	}

	onMount(() => {
		totalCases = 567;
		avgRating = 4.5;
	});
</script>

<div class="flex flex-col h-full">
	<!-- 헤더 -->
	<div class="mb-4">
		<h2 class="text-2xl font-semibold flex items-center gap-2">
			🛠️ IT Help Desk 검색
		</h2>
		<p class="text-sm text-gray-500 mt-1">IT 문제 해결 사례를 검색하세요</p>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
		<!-- 검색 패널 -->
		<div class="flex flex-col gap-4">
			<!-- 통계 -->
			<div class="grid grid-cols-3 gap-3">
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{totalCases}</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">해결 사례</div>
				</div>
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">8</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">문제 유형</div>
				</div>
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-center">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{avgRating}</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">평균 만족도</div>
				</div>
			</div>

			<!-- 검색 폼 -->
			<div class="bg-white dark:bg-gray-900 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
				<div class="space-y-4">
					<!-- 문제 입력 -->
					<div>
						<label class="block text-sm font-medium mb-2">문제 또는 증상 검색</label>
						<textarea
							bind:value={query}
							on:keypress={handleKeyPress}
							placeholder="예: 로그인 오류, 네트워크 연결 안됨..."
							rows="4"
							class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<!-- 문제 유형 필터 -->
					<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
						<h3 class="text-sm font-medium mb-3">문제 유형</h3>
						<div class="space-y-2">
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={problemTypes.login} class="rounded" />
								<span class="text-sm">로그인/인증</span>
							</label>
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={problemTypes.network} class="rounded" />
								<span class="text-sm">네트워크</span>
							</label>
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={problemTypes.software} class="rounded" />
								<span class="text-sm">소프트웨어</span>
							</label>
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="checkbox" bind:checked={problemTypes.hardware} class="rounded" />
								<span class="text-sm">하드웨어</span>
							</label>
						</div>
					</div>

					<!-- 우선순위 -->
					<div>
						<label class="block text-sm font-medium mb-2">우선순위</label>
						<select
							bind:value={priority}
							class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
						>
							<option value="">전체</option>
							<option value="high">🔴 높음</option>
							<option value="medium">🟡 보통</option>
							<option value="low">🟢 낮음</option>
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
							🔍 해결책 검색
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
					<div class="text-6xl mb-4">🛠️</div>
					<p>문제를 검색하여 해결책을 찾아보세요</p>
				</div>
			{:else}
				<div class="space-y-3 max-h-[600px] overflow-y-auto">
					{#each results as result, idx}
						{@const p = result.metadata?.priority || 'medium'}
						<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border-l-4 border-blue-500">
							<div class="flex items-start justify-between mb-2">
								<div class="font-semibold text-lg flex items-center gap-2">
									<span>{getPriorityIcon(p)}</span>
									<span>{result.metadata?.title || '문제 해결'}</span>
								</div>
								<div class="bg-blue-600 text-white text-xs px-2 py-1 rounded-full">
									{((result.final_score || result.score) * 100).toFixed(1)}%
								</div>
							</div>

							<div class="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400 mb-2">
								<span>🛠️ {result.metadata?.category || 'IT 지원'}</span>
								<span>👤 해결률: {result.metadata?.solved_rate || '95'}%</span>
								<span class={getPriorityColor(p)}>
									우선순위: {p === 'high' ? '높음' : p === 'medium' ? '보통' : '낮음'}
								</span>
							</div>

							<div class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-3">
								{result.text}
							</div>

							<div class="flex flex-wrap gap-2">
								<span class="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs px-2 py-1 rounded">
									⏱️ 평균 {result.metadata?.resolution_time || '30'}분
								</span>
								<span class="bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 text-xs px-2 py-1 rounded">
									⭐ {result.metadata?.rating || '4.5'}/5.0
								</span>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>
