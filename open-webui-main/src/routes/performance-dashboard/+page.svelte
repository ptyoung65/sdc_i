<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	interface PerformanceMetric {
		operation: string;
		batch_size: number;
		total_items: number;
		start_time: string;
		end_time: string;
		elapsed_seconds: number;
		items_per_second: number;
		success: boolean;
		error?: string;
	}

	interface DashboardData {
		timestamp: string;
		milvus_stats?: {
			collections: number;
			total_entities: number;
			status: string;
		};
		recent_metrics: PerformanceMetric[];
		summary: {
			total_operations: number;
			total_items_processed: number;
			average_speed: number;
			success_rate: number;
		};
	}

	let dashboardData: DashboardData | null = null;
	let loading = true;
	let error = '';
	let autoRefresh = true;
	let refreshInterval: any;

	// API 엔드포인트 (환경에 맞게 수정)
	const API_BASE = 'http://localhost:8099';

	async function fetchDashboardData() {
		try {
			loading = true;
			const response = await fetch(`${API_BASE}/api/performance/dashboard`);
			if (!response.ok) throw new Error('Failed to fetch dashboard data');
			dashboardData = await response.json();
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
			console.error('Dashboard fetch error:', e);
		} finally {
			loading = false;
		}
	}

	function startAutoRefresh() {
		if (autoRefresh) {
			refreshInterval = setInterval(fetchDashboardData, 5000); // 5초마다 갱신
		}
	}

	function stopAutoRefresh() {
		if (refreshInterval) {
			clearInterval(refreshInterval);
			refreshInterval = null;
		}
	}

	function toggleAutoRefresh() {
		autoRefresh = !autoRefresh;
		if (autoRefresh) {
			startAutoRefresh();
		} else {
			stopAutoRefresh();
		}
	}

	onMount(() => {
		fetchDashboardData();
		startAutoRefresh();
	});

	onDestroy(() => {
		stopAutoRefresh();
	});

	function formatNumber(num: number): string {
		return new Intl.NumberFormat('ko-KR').format(Math.round(num));
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleString('ko-KR');
	}
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
	<div class="max-w-7xl mx-auto">
		<!-- Header -->
		<div class="mb-8 flex justify-between items-center">
			<div>
				<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
					Milvus 성능 모니터링 대시보드
				</h1>
				<p class="mt-2 text-gray-600 dark:text-gray-400">
					실시간 벡터 DB 성능 모니터링 및 분석
				</p>
			</div>

			<div class="flex gap-3">
				<button
					on:click={fetchDashboardData}
					disabled={loading}
					class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
				>
					{loading ? '로딩 중...' : '새로고침'}
				</button>

				<button
					on:click={toggleAutoRefresh}
					class="px-4 py-2 rounded-lg border {autoRefresh
						? 'bg-green-500 text-white border-green-600'
						: 'bg-gray-200 text-gray-700 border-gray-300'}"
				>
					자동 갱신 {autoRefresh ? 'ON' : 'OFF'}
				</button>
			</div>
		</div>

		{#if error}
			<div class="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
				<strong>에러:</strong> {error}
				<p class="mt-2 text-sm">
					성능 모니터링 서버(포트 8099)가 실행 중인지 확인하세요.
				</p>
			</div>
		{/if}

		{#if dashboardData}
			<!-- Summary Cards -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
				<div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">총 작업 수</p>
							<p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
								{formatNumber(dashboardData.summary.total_operations)}
							</p>
						</div>
						<div class="p-3 bg-blue-100 rounded-full">
							<svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
							</svg>
						</div>
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">처리된 항목</p>
							<p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
								{formatNumber(dashboardData.summary.total_items_processed)}
							</p>
						</div>
						<div class="p-3 bg-green-100 rounded-full">
							<svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
							</svg>
						</div>
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">평균 처리 속도</p>
							<p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
								{formatNumber(dashboardData.summary.average_speed)}/s
							</p>
						</div>
						<div class="p-3 bg-purple-100 rounded-full">
							<svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
						</div>
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">성공률</p>
							<p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
								{dashboardData.summary.success_rate.toFixed(1)}%
							</p>
						</div>
						<div class="p-3 bg-yellow-100 rounded-full">
							<svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
						</div>
					</div>
				</div>
			</div>

			<!-- Milvus Stats -->
			{#if dashboardData.milvus_stats}
				<div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow mb-8">
					<h2 class="text-xl font-bold text-gray-900 dark:text-white mb-4">
						Milvus 상태
					</h2>
					<div class="grid grid-cols-3 gap-4">
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">컬렉션 수</p>
							<p class="text-lg font-semibold text-gray-900 dark:text-white">
								{dashboardData.milvus_stats.collections}
							</p>
						</div>
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">총 엔티티</p>
							<p class="text-lg font-semibold text-gray-900 dark:text-white">
								{formatNumber(dashboardData.milvus_stats.total_entities)}
							</p>
						</div>
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">상태</p>
							<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {dashboardData.milvus_stats.status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
								{dashboardData.milvus_stats.status}
							</span>
						</div>
					</div>
				</div>
			{/if}

			<!-- Recent Metrics Table -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
				<div class="p-6 border-b border-gray-200 dark:border-gray-700">
					<h2 class="text-xl font-bold text-gray-900 dark:text-white">
						최근 성능 지표
					</h2>
				</div>

				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
						<thead class="bg-gray-50 dark:bg-gray-900">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
									작업
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
									배치 크기
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
									총 항목
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
									처리 시간
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
									처리 속도
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
									상태
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
									시간
								</th>
							</tr>
						</thead>
						<tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
							{#each dashboardData.recent_metrics as metric}
								<tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
									<td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
										{metric.operation}
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
										{metric.batch_size}
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
										{formatNumber(metric.total_items)}
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
										{metric.elapsed_seconds.toFixed(2)}s
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
										{formatNumber(metric.items_per_second)}/s
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {metric.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
											{metric.success ? '성공' : '실패'}
										</span>
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
										{formatDate(metric.start_time)}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>

			<!-- Timestamp -->
			<div class="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
				마지막 갱신: {formatDate(dashboardData.timestamp)}
			</div>
		{:else if loading}
			<div class="flex items-center justify-center h-64">
				<div class="text-center">
					<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
					<p class="text-gray-600 dark:text-gray-400">데이터 로딩 중...</p>
				</div>
			</div>
		{/if}
	</div>
</div>
