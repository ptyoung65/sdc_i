<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { WEBUI_NAME, mobile, showSidebar, user } from '$lib/stores';
	import { page } from '$app/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Admin Panel')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class=" flex flex-col h-screen max-h-[100dvh] flex-1 transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ' md:max-w-[calc(100%-49px)]'}  w-full max-w-full"
	>
		<nav class="   px-2.5 pt-1.5 backdrop-blur-xl drag-region">
			<div class=" flex items-center gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class=" flex w-full">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent pt-1"
					>
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/users')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin">{$i18n.t('Users')}</a
						>

						<!-- <a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/analytics')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/analytics">{$i18n.t('Analytics')}</a
						> -->

						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/evaluations') && !$page.url.pathname.includes('/admin/evaluations2')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/evaluations">{$i18n.t('Evaluations')}</a
						>

						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/evaluations2')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/evaluations2">{$i18n.t('Evaluations 2')}</a
						>


					<!-- ============================================ -->
					<!-- [2024.12.30] 관리자 메뉴 - 가드레일/모니터링/대시보드 시작 -->
					<!-- 역할: 관리자 패널에 추가 메뉴 표시 -->
					<!-- 메뉴: Guardrails, 가드레일, Monitoring, 모니터링, KPI, Dashboard, 서버현황, 대시보드 -->
					<!-- ============================================ -->

					<!-- ==================== 2025-11-19일 추가시작 ==================== -->
					<!-- 관리자 패널에 가드레일 메뉴 추가 -->
					<a
						class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/guardrails') && !$page.url.pathname.includes('/admin/guardrails2')
							? 'text-gray-600 dark:text-gray-400'
							: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
						href="/admin/guardrails">{$i18n.t('Guardrails')}</a
					>
					<!-- ==================== 2025-11-19일 추가완료 ==================== -->

						<!-- ==================== 2025-12-27 가드레일2 메뉴 추가시작 ==================== -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/guardrails2')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/guardrails2">{$i18n.t('가드레일')}</a
						>
						<!-- ==================== 2025-12-27 가드레일2 메뉴 추가완료 ==================== -->

						<!-- ==================== 2025-11-18일 수정시작 ==================== -->
						<!-- 관리자 패널에 모니터링 메뉴 추가 -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/monitoring') && !$page.url.pathname.includes('/admin/monitoring2')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/monitoring">{$i18n.t('Monitoring')}</a
						>
						<!-- ==================== 2025-11-18일 수정완료 ==================== -->

						<!-- ==================== 2025-12-27 모니터링2 메뉴 추가시작 ==================== -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/monitoring2')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/monitoring2">{$i18n.t('모니터링')}</a
						>
						<!-- ==================== 2025-12-27 모니터링2 메뉴 추가완료 ==================== -->

						<!-- ==================== 2025-11-27일 KPI 대시보드 추가시작 ==================== -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/kpi')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/kpi">{$i18n.t('KPI')}</a
						>
						<!-- ==================== 2025-11-27일 KPI 대시보드 추가완료 ==================== -->

						<!-- ==================== 2025-11-30일 대시보드 추가시작 ==================== -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/dashboard') && !$page.url.pathname.includes('/admin/dashboard2')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/dashboard">{$i18n.t('Dashboard')}</a
						>
						<!-- ==================== 2025-11-30일 대시보드 추가완료 ==================== -->

						<!-- ==================== 2025-12-14 서버현황 메뉴 추가시작 ==================== -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/server-status')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/server-status">{$i18n.t('서버현황')}</a
						>
						<!-- ==================== 2025-12-14 서버현황 메뉴 추가완료 ==================== -->

						<!-- ==================== 2026-01-06 토큰모니터링 메뉴 추가시작 ==================== -->
						<!-- 토큰 현황 모니터링 페이지 링크 (/admin/token-monitoring) -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/token-monitoring')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/token-monitoring">{$i18n.t('토큰현황')}</a
						>
						<!-- ==================== 2026-01-06 토큰모니터링 메뉴 추가완료 ==================== -->

						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/functions')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/functions">{$i18n.t('Functions')}</a
						>

						<!-- ==================== 2025-12-27 대시보드2 메뉴 추가시작 ==================== -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/dashboard2')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/dashboard2">{$i18n.t('대시보드')}</a
						>
						<!-- [2024.12.30] 관리자 메뉴 - 가드레일/모니터링/대시보드 완료 ============================================ -->
						<!-- ==================== 2025-12-27 대시보드2 메뉴 추가완료 ==================== -->

						<!-- ==================== 2026-02-07 Podman 컨테이너 관리 메뉴 추가시작 ==================== -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/podman')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'} transition"
							href="/admin/podman">{$i18n.t('Podman')}</a
						>
						<!-- ==================== 2026-02-07 Podman 컨테이너 관리 메뉴 추가완료 ==================== -->

						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/admin/settings')
								? 'text-gray-600 dark:text-gray-400'
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/admin/settings">{$i18n.t('Settings')}</a
						>
					</div>
				</div>
			</div>
		</nav>

		<div class="  pb-1 flex-1 max-h-full overflow-y-auto">
			<slot />
		</div>
	</div>
{/if}
