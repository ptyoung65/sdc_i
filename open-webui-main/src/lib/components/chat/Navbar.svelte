<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		WEBUI_NAME,
		banners,
		chatId,
		config,
		mobile,
		settings,
		showArchivedChats,
		showControls,
		showSidebar,
		showSettings,
		temporaryChatEnabled,
		user,
		modelType,
		theme
	} from '$lib/stores';

	import { slide } from 'svelte/transition';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Menu from '$lib/components/layout/Navbar/Menu.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';

	import PencilSquare from '../icons/PencilSquare.svelte';
	import Banner from '../common/Banner.svelte';
	import Sidebar from '../icons/Sidebar.svelte';

	import ChatBubbleDotted from '../icons/ChatBubbleDotted.svelte';
	import ChatBubbleDottedChecked from '../icons/ChatBubbleDottedChecked.svelte';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import ChatPlus from '../icons/ChatPlus.svelte';
	import ChatCheck from '../icons/ChatCheck.svelte';
	import Knobs from '../icons/Knobs.svelte';
	import Settings from '../icons/Settings.svelte';
	import UserGroup from '../icons/UserGroup.svelte';

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let shareEnabled: boolean = false;

	export let chat;
	export let history;
	export let selectedModels;
	export let showModelSelector = true;
	export let modelSelectorDisabled = false;

	export let onSaveTempChat: () => {};
	export let archiveChatHandler: (id: string) => void;
	export let moveChatHandler: (id: string, folderId: string) => void;
	export let controlPaneComponent = null;

	let closedBannerIds = [];

	let showShareChatModal = false;
	let showDownloadChatModal = false;

	// 왼쪽 사이드바가 닫혔을 때만 토글 버튼 표시 (내부/외부 모델 모두)
	$: showLeftSidebarToggle = !$showSidebar;
	// 오른쪽 Controls가 닫혔을 때만 토글 버튼 표시 (내부/외부 모델 모두)
	$: showRightControlsToggle = !$showControls;

	// Theme toggle function
	const applyTheme = (_theme: string) => {
		let themeToApply = _theme === 'oled-dark' ? 'dark' : _theme === 'her' ? 'light' : _theme;

		if (_theme === 'system') {
			themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		}

		if (themeToApply === 'dark' && !_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#333');
			document.documentElement.style.setProperty('--color-gray-850', '#262626');
			document.documentElement.style.setProperty('--color-gray-900', '#171717');
			document.documentElement.style.setProperty('--color-gray-950', '#0d0d0d');
		}

		['dark', 'light', 'oled-dark']
			.filter((e) => e !== themeToApply)
			.forEach((e) => {
				e.split(' ').forEach((e) => {
					document.documentElement.classList.remove(e);
				});
			});

		themeToApply.split(' ').forEach((e) => {
			document.documentElement.classList.add(e);
		});

		const metaThemeColor = document.querySelector('meta[name="theme-color"]');
		if (metaThemeColor) {
			metaThemeColor.setAttribute(
				'content',
				_theme === 'dark' ? '#171717' : _theme === 'oled-dark' ? '#000000' : '#ffffff'
			);
		}

		if (_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#101010');
			document.documentElement.style.setProperty('--color-gray-850', '#050505');
			document.documentElement.style.setProperty('--color-gray-900', '#000000');
			document.documentElement.style.setProperty('--color-gray-950', '#000000');
			document.documentElement.classList.add('dark');
		}
	};

	const toggleTheme = () => {
		const newTheme = $theme === 'dark' ? 'light' : 'dark';
		theme.set(newTheme);
		localStorage.setItem('theme', newTheme);
		applyTheme(newTheme);
	};
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={$chatId} />

<button
	id="new-chat-button"
	class="hidden"
	on:click={() => {
		initNewChat();
	}}
	aria-label="New Chat"
/>

<nav class="sticky top-0 z-30 w-full py-1 -mb-8 flex flex-col items-center drag-region bg-gray-50 dark:bg-gray-800">
	<div class="flex items-center w-full pl-1.5 pr-1">
		<div
			class=" bg-linear-to-b via-40% to-97% from-gray-50 via-gray-50 to-transparent dark:from-gray-800 dark:via-gray-800 dark:to-transparent pointer-events-none absolute inset-0 -bottom-7 z-[-1]"
		></div>

		<div class=" flex max-w-full w-full mx-auto px-1.5 md:px-2 pt-0.5 bg-transparent">
			<div class="flex items-center w-full max-w-full">
				<!-- 왼쪽 사이드바 토글 버튼: 사이드바가 닫혔을 때만 표시 -->
				{#if showLeftSidebarToggle}
					<div
						class="-translate-x-0.5 mr-1 mt-1 self-start flex flex-none items-center text-gray-600 dark:text-gray-400"
					>
						<Tooltip content={$i18n.t('Open Sidebar')}>
							<button
								class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => {
									showSidebar.set(true);
								}}
								aria-label="Open Left Sidebar"
							>
								<div class="self-center p-1.5">
									<!-- 햄버거 아이콘 -->
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
										 stroke-width="2" stroke="currentColor" class="size-5">
										<path stroke-linecap="round" stroke-linejoin="round"
											  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"/>
									</svg>
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div
					class="flex-1 overflow-hidden max-w-full py-0.5
			{$showSidebar ? 'ml-1' : ''}
			"
				>
					{#if $modelType === 'external'}
						<!-- 외부 모델: ModelSelector를 통해 다중 모델 선택 가능 -->
						<div class="flex items-center gap-2 px-2">
							<ModelSelector bind:selectedModels {showModelSelector} disabled={modelSelectorDisabled} />
						</div>
					{:else}
						<!-- 내부 모델: 기존 방식 (텍스트 표시) -->
						<div class="flex items-center gap-2 px-2">
							<span class="text-sm font-semibold text-gray-700 dark:text-gray-200 truncate">
								내부 모델: {selectedModels.length > 0 ? selectedModels.join(', ') : 'None'}
							</span>
						</div>
					{/if}
				</div>

				<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400 {$showControls ? 'pr-16' : 'pr-1'}">
					<!-- <div class="md:hidden flex self-center w-[1px] h-5 mx-2 bg-gray-300 dark:bg-stone-700" /> -->

					<!-- 제어 버튼들 숨김 -->
					{#if $user?.role === 'user' ? ($user?.permissions?.chat?.temporary ?? true) && !($user?.permissions?.chat?.temporary_enforced ?? false) : true}
						{#if !chat?.id}
							<Tooltip content={$i18n.t(`Temporary Chat`)}>
								<button
									style="display: none;"
									class="flex cursor-pointer px-2 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									id="temporary-chat-button"
									on:click={async () => {
										if (($settings?.temporaryChatByDefault ?? false) && $temporaryChatEnabled) {
											// for proper initNewChat handling
											await temporaryChatEnabled.set(null);
										} else {
											await temporaryChatEnabled.set(!$temporaryChatEnabled);
										}

										await goto('/');

										// add 'temporary-chat=true' to the URL
										if ($temporaryChatEnabled) {
											window.history.replaceState(null, '', '?temporary-chat=true');
										} else {
											window.history.replaceState(null, '', location.pathname);
										}
									}}
								>
									<div class=" m-auto self-center">
										{#if $temporaryChatEnabled}
											<ChatBubbleDottedChecked className=" size-4.5" strokeWidth="1.5" />
										{:else}
											<ChatBubbleDotted className=" size-4.5" strokeWidth="1.5" />
										{/if}
									</div>
								</button>
							</Tooltip>
						{:else if $temporaryChatEnabled}
							<Tooltip content={$i18n.t(`Save Chat`)}>
								<button
									style="display: none;"
									class="flex cursor-pointer px-2 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									id="save-temporary-chat-button"
									on:click={async () => {
										onSaveTempChat();
									}}
								>
									<div class=" m-auto self-center">
										<ChatCheck className=" size-4.5" strokeWidth="1.5" />
									</div>
								</button>
							</Tooltip>
						{/if}
					{/if}

					{#if $mobile && !$temporaryChatEnabled && chat && chat.id}
						<Tooltip content={$i18n.t('New Chat')}>
							<button
								style="display: none;"
								class=" flex {$showSidebar
									? 'md:hidden'
									: ''} cursor-pointer px-2 py-2 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								on:click={() => {
									initNewChat();
								}}
								aria-label="New Chat"
							>
								<div class=" m-auto self-center">
									<ChatPlus className=" size-4.5" strokeWidth="1.5" />
								</div>
							</button>
						</Tooltip>
					{/if}

					{#if shareEnabled && chat && (chat.id || $temporaryChatEnabled)}
						<Menu
							{chat}
							{shareEnabled}
							shareHandler={() => {
								showShareChatModal = !showShareChatModal;
							}}
							archiveChatHandler={() => {
								archiveChatHandler(chat.id);
							}}
							{moveChatHandler}
						>
							<button
								style="display: none;"
								class="flex cursor-pointer px-2 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								id="chat-context-menu-button"
							>
								<div class=" m-auto self-center">
									<EllipsisHorizontal className=" size-5" strokeWidth="1.5" />
								</div>
							</button>
						</Menu>
					{/if}

					<!-- 관리자 기능 버튼 (Admin만 표시) -->
					{#if $user?.role === 'admin'}
						<Tooltip content={$i18n.t('Admin Panel')}>
							<a
								href="/admin"
								class="flex cursor-pointer rounded-xl p-1.5 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								aria-label="Admin Panel"
							>
								<div class="self-center">
									<UserGroup className="size-6" strokeWidth="1.5" />
								</div>
							</a>
						</Tooltip>
					{/if}

					<!-- 주/야간 모드 토글 (모든 사용자) -->
					<Tooltip content={$theme === 'dark' ? $i18n.t('Light mode') : $i18n.t('Dark mode')}>
						<button
							class="flex cursor-pointer rounded-xl p-1.5 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							on:click={toggleTheme}
							aria-label="Toggle theme"
						>
							<div class="self-center">
								{#if $theme === 'dark'}
									<!-- Sun 아이콘 (라이트 모드로 전환) -->
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
										 stroke-width="1.5" stroke="currentColor" class="size-6">
										<path stroke-linecap="round" stroke-linejoin="round"
											  d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z"/>
									</svg>
								{:else}
									<!-- Moon 아이콘 (다크 모드로 전환) -->
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
										 stroke-width="1.5" stroke="currentColor" class="size-6">
										<path stroke-linecap="round" stroke-linejoin="round"
											  d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z"/>
									</svg>
								{/if}
							</div>
						</button>
					</Tooltip>

					<!-- 설정 버튼 (Admin만 표시) -->
					{#if $user?.role === 'admin'}
						<Tooltip content={$i18n.t('Settings')}>
							<button
								class="flex cursor-pointer rounded-xl p-1.5 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								on:click={async () => {
									await showSettings.set(true);
									if ($mobile) {
										showSidebar.set(false);
									}
								}}
								aria-label="Settings"
							>
								<div class="self-center">
									<Settings className="size-6" strokeWidth="1.5" />
								</div>
							</button>
						</Tooltip>
					{/if}

					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[240px]"
							role={$user?.role}
							help={false}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<div
								class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							>
								<div class=" self-center">
									<span class="sr-only">{$i18n.t('User menu')}</span>
									<img
										src={$user?.profile_image_url}
										class="size-6 object-cover rounded-full"
										alt=""
										draggable="false"
									/>
								</div>
							</div>
						</UserMenu>
					{/if}

					<!-- 오른쪽 Controls 토글 버튼: Controls가 닫혔을 때만 표시 -->
					{#if showRightControlsToggle && ($user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true))}
						<div
							class="ml-1 mt-1 self-start flex flex-none items-center text-gray-600 dark:text-gray-400"
						>
							<Tooltip content="카테고리 열기">
								<button
									class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
									on:click={() => {
										showControls.set(true);
									}}
									aria-label="Open Controls"
								>
									<div class="self-center p-1.5">
										<!-- 햄버거 아이콘 -->
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
											 stroke-width="2" stroke="currentColor" class="size-5">
											<path stroke-linecap="round" stroke-linejoin="round"
												  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"/>
										</svg>
									</div>
								</button>
							</Tooltip>
						</div>
					{/if}

				</div>
			</div>
		</div>
	</div>

	{#if $temporaryChatEnabled && ($chatId ?? '').startsWith('local:')}
		<div class=" w-full z-30 text-center">
			<div class="text-xs text-gray-500">{$i18n.t('Temporary Chat')}</div>
		</div>
	{/if}

	<div class="absolute top-[100%] left-0 right-0 h-fit">
		{#if !history.currentId && !$chatId && ($banners.length > 0 || ($config?.license_metadata?.type ?? null) === 'trial' || (($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats))}
			<div class=" w-full z-30">
				<div class=" flex flex-col gap-1 w-full">
					{#if ($config?.license_metadata?.type ?? null) === 'trial'}
						<Banner
							banner={{
								type: 'info',
								title: 'Trial License',
								content: $i18n.t(
									'You are currently using a trial license. Please contact support to upgrade your license.'
								)
							}}
						/>
					{/if}

					{#if ($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats}
						<Banner
							banner={{
								type: 'error',
								title: 'License Error',
								content: $i18n.t(
									'Exceeded the number of seats in your license. Please contact support to increase the number of seats.'
								)
							}}
						/>
					{/if}

					{#each $banners.filter((b) => ![...JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]'), ...closedBannerIds].includes(b.id)) as banner (banner.id)}
						<Banner
							{banner}
							on:dismiss={(e) => {
								const bannerId = e.detail;

								if (banner.dismissible) {
									localStorage.setItem(
										'dismissedBannerIds',
										JSON.stringify(
											[
												bannerId,
												...JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]')
											].filter((id) => $banners.find((b) => b.id === id))
										)
									);
								} else {
									closedBannerIds = [...closedBannerIds, bannerId];
								}
							}}
						/>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</nav>
