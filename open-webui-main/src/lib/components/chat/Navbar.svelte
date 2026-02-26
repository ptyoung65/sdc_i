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
		theme,
		showHelpModal
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

	// ----- [2025.01.05] 외부 서버 연결 상태 표시 컴포넌트 추가 시작 -----
	import ServerStatusIndicator from '$lib/components/layout/ServerStatusIndicator.svelte';
	// ----- [2025.01.05] 외부 서버 연결 상태 표시 컴포넌트 추가 종료 -----

	// ----- [2026.01.07] 도움말 이미지 뷰어 컴포넌트 추가 시작 -----
	import HelpImageViewer from '$lib/components/chat/HelpImageViewer.svelte';
	// ----- [2026.01.07] 도움말 이미지 뷰어 컴포넌트 추가 종료 -----

	// ----- [2026-02-19] 공지사항 다시보기 기능 추가 시작 -----
	// [2026-02-26] import 설명:
	//   - PopupAnnouncementModal: 공지 팝업 모달 컴포넌트 (제목, 내용, 네비게이션, 오늘 하루 보지 않기)
	//   - getActiveAnnouncements: GET /api/v1/configs/announcements/active 호출
	//     → 백엔드에서 MAX_POPUP_COUNT 적용하여 활성 공지 N개 반환
	import PopupAnnouncementModal from '$lib/components/common/PopupAnnouncementModal.svelte';
	import { getActiveAnnouncements } from '$lib/apis/announcements';
	// ----- [2026-02-19] 공지사항 다시보기 기능 추가 종료 -----

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

	// ----- [2026-02-19] 공지사항 다시보기 상태 시작 -----
	// ----- [2026-02-26] 공지사항 다시보기 기능 상세 설명 시작 -----
	// ■ 기능: Navbar 메가폰 아이콘 클릭 시 활성 공지사항을 팝업으로 다시 표시
	//
	// ■ 데이터 흐름:
	//   1. 사용자가 Navbar의 메가폰(확성기) 아이콘 클릭
	//   2. loadAndShowAnnouncements() 호출
	//   3. getActiveAnnouncements(token) → GET /api/v1/configs/announcements/active
	//   4. 백엔드 configs.py get_active_announcements():
	//      - get_config()에서 MAX_POPUP_COUNT 조회 (config 테이블 data JSONB)
	//      - PopupAnnouncements.get_active_announcements(limit=max_popup_count)
	//      - 활성 공지 중 최근 N개만 반환 (관리자 설정값 적용)
	//   5. 반환된 공지를 start_date 내림차순 정렬
	//   6. PopupAnnouncementModal에 전달하여 팝업 표시
	//
	// ■ MAX_POPUP_COUNT 설정 변경 시 즉시 반영:
	//   관리자가 /admin/settings/notification에서 개수 변경 → config 테이블 저장
	//   → 이 버튼 클릭 시 백엔드에서 변경된 값으로 제한된 공지 반환
	//
	// ■ "오늘 하루 보지 않기" 무시:
	//   이 버튼은 로그인 시 자동 팝업과 달리 dismiss 상태를 무시하고 항상 표시
	// ----- [2026-02-26] 공지사항 다시보기 기능 상세 설명 종료 -----
	let showAnnouncementPopup = false;
	let popupAnnouncements: any[] = [];

	const loadAndShowAnnouncements = async () => {
		try {
			// [2026-02-26] 백엔드 get_active_announcements가 MAX_POPUP_COUNT를 서버에서 적용하므로
			// exportConfig 호출 불필요 (설정 개수 제한은 백엔드에서 처리)
			const announcements = await getActiveAnnouncements(localStorage.token);
			if (announcements && announcements.length > 0) {
				const sorted = [...announcements].sort((a: any, b: any) => b.start_date - a.start_date);
				popupAnnouncements = sorted;
				showAnnouncementPopup = true;
			} else {
				toast.info('등록된 공지사항이 없습니다.');
			}
		} catch (err) {
			toast.error('공지사항을 불러올 수 없습니다.');
		}
	};
	// ----- [2026-02-19] 공지사항 다시보기 상태 종료 -----

	// 왼쪽 사이드바가 닫혔을 때만 토글 버튼 표시 (내부/외부 모델 모두)
	$: showLeftSidebarToggle = !$showSidebar;
	// 오른쪽 Controls가 닫혔을 때만 토글 버튼 표시 (내부/외부 모델 모두)
	$: showRightControlsToggle = !$showControls;

	// 모델명 간소화 함수 (버전 정보 제거)
	const simplifyModelName = (modelName: string): string => {
		// qwen2-1.5b-instruct -> qwen2
		// gpt-4-turbo-preview -> gpt
		// claude-3-opus-20240229 -> claude
		// 첫 번째 하이픈 앞 부분만 반환
		const parts = modelName.split('-');
		return parts[0];
	};

	// 모델 목록을 간소화된 이름으로 변환
	$: simplifiedModels = selectedModels.map(simplifyModelName);

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
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400">외부:</span>
							<ModelSelector bind:selectedModels {showModelSelector} disabled={modelSelectorDisabled} />
						</div>
					{:else}
						<!-- 내부 모델: 간단 표시 (내부 표시 + 모델명) -->
						<div class="flex items-center gap-2 px-2">
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400">내부:</span>
							<span class="text-sm font-semibold text-gray-700 dark:text-gray-200 truncate">
								{simplifiedModels.length > 0 ? simplifiedModels.join(', ') : 'None'}
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

					<!-- ----- [2025.01.05] 외부 서버 연결 상태 인디케이터 시작 ----- -->
					<!-- [2026-02-04] 숨김 처리 -->
					<!-- <ServerStatusIndicator /> -->
					<!-- ----- [2025.01.05] 외부 서버 연결 상태 인디케이터 종료 ----- -->

					<!-- ----- [2026-02-19] 공지사항 다시보기 버튼 (모든 사용자) 시작 ----- -->
					<!-- [2026-02-26] 공지사항 다시보기 아이콘 버튼 상세 설명
					     ■ 대상: 모든 사용자 (admin + user 공통)
					     ■ 아이콘: 메가폰(확성기) SVG - 기존 벨 아이콘(Notification Settings, admin 전용)과 구분
					     ■ 위치: Navbar 우측 아이콘 중 첫 번째 (알림설정 벨 아이콘 왼쪽)
					     ■ 클릭 시 동작:
					       1. loadAndShowAnnouncements() 호출
					       2. getActiveAnnouncements(token) → GET /api/v1/configs/announcements/active
					       3. 백엔드에서 MAX_POPUP_COUNT 적용된 활성 공지 반환
					       4. 공지 있으면 → PopupAnnouncementModal 팝업 표시
					       5. 공지 없으면 → toast.info('등록된 공지사항이 없습니다.') 표시
					     ■ 로그인 시 자동 팝업과의 차이:
					       - "오늘 하루 보지 않기" 상태를 무시하고 항상 표시
					       - exportConfig 호출 없이 getActiveAnnouncements만 호출 (404 오류 방지)
					-->
					<Tooltip content="공지사항 다시보기">
						<button
							class="flex cursor-pointer rounded-xl p-1.5 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							on:click={loadAndShowAnnouncements}
							aria-label="공지사항 다시보기"
						>
							<div class="self-center">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
									<path stroke-linecap="round" stroke-linejoin="round" d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 1 1 0-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 0 1-1.44-4.282m3.102.069a18.03 18.03 0 0 1-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 0 1 8.835 2.535M10.34 6.66a23.847 23.847 0 0 0 8.835-2.535m0 0A23.74 23.74 0 0 0 18.795 3m.38 1.125a23.91 23.91 0 0 1 1.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 0 0 1.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 0 1 0 3.46" />
								</svg>
							</div>
						</button>
					</Tooltip>
					<!-- ----- [2026-02-19] 공지사항 다시보기 버튼 종료 ----- -->

					<!-- ----- [2026-02-04] 공지사항 알림 버튼 (Admin만 표시) 시작 ----- -->
					{#if $user?.role === 'admin'}
						<Tooltip content={$i18n.t('Notification Settings')}>
							<a
								href="/admin/settings/notification"
								class="flex cursor-pointer rounded-xl p-1.5 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								aria-label="Notification Settings"
							>
								<div class="self-center">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
										<path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
									</svg>
								</div>
							</a>
						</Tooltip>
					{/if}
					<!-- ----- [2026-02-04] 공지사항 알림 버튼 종료 ----- -->

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

						<!-- ============================================ -->
						<!-- [2026.01.07] 도움말 아이콘 추가 시작 -->
						<!-- 역할: 사용자 아이콘 오른쪽에 ? 아이콘을 표시하여 -->
						<!--       클릭 시 도움말 이미지 뷰어 모달을 열기 -->
						<!-- ============================================ -->
						<Tooltip content="도움말">
							<button
								class="flex cursor-pointer rounded-xl p-1.5 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								on:click={() => showHelpModal.set(true)}
								aria-label="도움말"
							>
								<div class="self-center">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
										 stroke-width="1.5" stroke="currentColor" class="size-6">
										<path stroke-linecap="round" stroke-linejoin="round"
											  d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z"/>
									</svg>
								</div>
							</button>
						</Tooltip>
						<!-- ============================================ -->
						<!-- [2026.01.07] 도움말 아이콘 추가 종료 -->
						<!-- ============================================ -->
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

<!-- [2026.01.07] 도움말 이미지 뷰어 모달 -->
<HelpImageViewer />

<!-- ----- [2026-02-19] 공지사항 다시보기 모달 시작 ----- -->
<!-- [2026-02-26] PopupAnnouncementModal 렌더링 상세 설명
     ■ 역할: 메가폰 아이콘 클릭 시 팝업 공지사항을 모달로 표시
     ■ Props:
       - bind:show={showAnnouncementPopup}: 모달 표시/숨김 제어 (양방향 바인딩)
       - announcements={popupAnnouncements}: 백엔드에서 MAX_POPUP_COUNT 적용된 공지 목록
     ■ Events:
       - on:close: 모달 닫기 시 showAnnouncementPopup = false 설정
     ■ 동일 컴포넌트가 +layout.svelte에서도 로그인 시 자동 팝업용으로 사용됨
-->
<PopupAnnouncementModal
	bind:show={showAnnouncementPopup}
	announcements={popupAnnouncements}
	on:close={() => { showAnnouncementPopup = false; }}
/>
<!-- ----- [2026-02-19] 공지사항 다시보기 모달 종료 ----- -->
