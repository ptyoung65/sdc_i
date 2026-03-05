<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, tick, getContext } from 'svelte';
	import { openDB, deleteDB } from 'idb';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fade } from 'svelte/transition';

	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { getFunctions } from '$lib/apis/functions';
	import { getModels, getToolServersData, getVersionUpdates } from '$lib/apis';
	import { getAllTags } from '$lib/apis/chats';
	import { getPrompts } from '$lib/apis/prompts';
	import { getTools } from '$lib/apis/tools';
	import { getBanners, getModelColors, exportConfig } from '$lib/apis/configs';
	import { getUserSettings } from '$lib/apis/users';
	// ----- [2026-02-04] 팝업 공지사항 API import 시작 -----
	import { getActiveAnnouncements, type PopupAnnouncement } from '$lib/apis/announcements';
	// ----- [2026-02-04] 팝업 공지사항 API import 종료 -----

	import { WEBUI_VERSION } from '$lib/constants';
	import { compareVersion } from '$lib/utils';

	import {
		config,
		user,
		settings,
		models,
		prompts,
		knowledge,
		tools,
		functions,
		tags,
		banners,
		showSettings,
		showShortcuts,
		showChangelog,
		temporaryChatEnabled,
		toolServers,
		showSearch,
		showSidebar,
		showRightSidebar,
		// ----- [2025.01.05] 외부 서버 연결 상태 추적 기능 추가 시작 -----
		updateServerStatus,
		removeServerStatus,
		type ExternalServerType,
		// ----- [2025.01.05] 외부 서버 연결 상태 추적 기능 추가 종료 -----
		// ----- [2026.01.19] 모델 색상 설정 Store -----
		modelColors
	} from '$lib/stores';

	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import SettingsModal from '$lib/components/chat/SettingsModal.svelte';
	import ChangelogModal from '$lib/components/ChangelogModal.svelte';
	import AccountPending from '$lib/components/layout/Overlay/AccountPending.svelte';
	import UpdateInfoToast from '$lib/components/layout/UpdateInfoToast.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	// ----- [2026-02-04] 팝업 공지사항 컴포넌트 import 시작 -----
	import PopupAnnouncementModal from '$lib/components/common/PopupAnnouncementModal.svelte';
	// ----- [2026-02-04] 팝업 공지사항 컴포넌트 import 종료 -----

	const i18n = getContext('i18n');

	let loaded = false;
	let DB = null;
	let localDBChats = [];

	// ----- [2026-02-04] 팝업 공지사항 상태 변수 시작 -----
	let popupAnnouncements: PopupAnnouncement[] = [];
	let showPopupAnnouncement = false;
	// ----- [2026-02-04] 팝업 공지사항 상태 변수 종료 -----

	let version;

	const clearChatInputStorage = () => {
		const chatInputKeys = Object.keys(localStorage).filter((key) => key.startsWith('chat-input'));
		if (chatInputKeys.length > 0) {
			chatInputKeys.forEach((key) => {
				localStorage.removeItem(key);
			});
		}
	};

	const checkLocalDBChats = async () => {
		try {
			// Check if IndexedDB exists
			DB = await openDB('Chats', 1);

			if (!DB) {
				return;
			}

			const chats = await DB.getAllFromIndex('chats', 'timestamp');
			localDBChats = chats.map((item, idx) => chats[chats.length - 1 - idx]);

			if (localDBChats.length === 0) {
				await deleteDB('Chats');
			}
		} catch (error) {
			// IndexedDB Not Found
		}
	};

	import { settingsService } from '$lib/services/settings.service';
	import { logger } from '$lib/utils/logger';

	const setUserSettings = async (cb: () => Promise<void>) => {
		// 1. localStorage 마이그레이션 시도 (최초 1회)
		await settingsService.migrateFromLocalStorage(localStorage.token);

		// 2. DB에서 설정 로드
		const userSettings = await settingsService.loadSettings(localStorage.token);

		// 3. Store 업데이트
		if (userSettings?.ui) {
			settings.set(userSettings.ui);
			logger.debug('UI', 'UI 설정 적용 완료', userSettings.ui);
		}

		if (cb) {
			await cb();
		}
	};

	// ----- [2025.01.05] 외부 LLM 연결 지연으로 인한 로그인 차단 방지 시작 -----
	// 문제: 외부 LLM 서버가 응답하지 않으면 전체 페이지 로드가 차단됨
	// 해결: timeout 추가 및 백그라운드 로드로 변경
	const MODEL_LOAD_TIMEOUT = 5000; // 5초 타임아웃
	const LLM_SERVER_URL = 'openai-api'; // LLM 서버 식별자

	const setModels = async (background = false) => {
		const startTime = Date.now();

		// 연결 시도 중 상태로 업데이트
		if (!background) {
			updateServerStatus(LLM_SERVER_URL, 'connecting', { name: 'LLM Server', type: 'llm' });
		}

		try {
			// timeout을 적용한 모델 로드
			const modelPromise = getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null
			);

			// background 모드가 아닐 때만 timeout 적용
			if (!background) {
				const timeoutPromise = new Promise((_, reject) =>
					setTimeout(() => reject(new Error('Model load timeout')), MODEL_LOAD_TIMEOUT)
				);

				const result = await Promise.race([modelPromise, timeoutPromise]);
				models.set(result);

				// 성공 시 연결 상태 업데이트
				const responseTime = Date.now() - startTime;
				updateServerStatus(LLM_SERVER_URL, 'connected', {
					name: 'LLM Server',
					type: 'llm',
					responseTime
				});
			} else {
				// 백그라운드 모드: timeout 없이 완료될 때까지 대기
				const result = await modelPromise;
				models.set(result);

				// 백그라운드 성공 시에도 상태 업데이트
				const responseTime = Date.now() - startTime;
				updateServerStatus(LLM_SERVER_URL, 'connected', {
					name: 'LLM Server',
					type: 'llm',
					responseTime
				});
			}
		} catch (error) {
			console.warn('[2025.01.05] 모델 로드 실패 또는 타임아웃:', error.message);

			// 타임아웃/에러 상태 업데이트
			const isTimeout = error.message.includes('timeout');
			updateServerStatus(LLM_SERVER_URL, isTimeout ? 'timeout' : 'error', {
				name: 'LLM Server',
				type: 'llm',
				errorMessage: error.message
			});

			// 실패해도 빈 배열로 초기화하여 UI는 정상 표시
			if (!$models || $models.length === 0) {
				models.set([]);
			}
			// 백그라운드에서 다시 시도 (타임아웃 없이)
			if (!background) {
				console.log('[2025.01.05] 백그라운드에서 모델 재로드 시도...');
				setModels(true); // 비동기로 백그라운드 재시도 (await 없음)
			}
		}
	};
	// ----- [2025.01.05] 외부 LLM 연결 지연으로 인한 로그인 차단 방지 종료 -----

	// ----- [2025.01.05] 도구 서버 연결 지연으로 인한 로그인 차단 방지 시작 -----
	const TOOL_SERVER_TIMEOUT = 5000; // 5초 타임아웃

	const setToolServers = async (background = false) => {
		const toolServerUrls = $settings?.toolServers ?? [];

		// 도구 서버가 없으면 스킵
		if (toolServerUrls.length === 0) {
			return;
		}

		try {
			const toolServerPromise = getToolServersData(toolServerUrls);

			let toolServersData;
			if (!background) {
				const timeoutPromise = new Promise((_, reject) =>
					setTimeout(() => reject(new Error('Tool server load timeout')), TOOL_SERVER_TIMEOUT)
				);
				toolServersData = await Promise.race([toolServerPromise, timeoutPromise]);
			} else {
				toolServersData = await toolServerPromise;
			}

			toolServersData = toolServersData.filter((data) => {
				if (!data || data.error) {
					toast.error(
						$i18n.t(`Failed to connect to {{URL}} OpenAPI tool server`, {
							URL: data?.url
						})
					);
					return false;
				}
				return true;
			});
			toolServers.set(toolServersData);
		} catch (error) {
			console.warn('[2025.01.05] 도구 서버 로드 실패 또는 타임아웃:', error.message);
			// 실패해도 빈 배열로 초기화
			if (!$toolServers || $toolServers.length === 0) {
				toolServers.set([]);
			}
			// 백그라운드에서 재시도
			if (!background) {
				console.log('[2025.01.05] 백그라운드에서 도구 서버 재로드 시도...');
				setToolServers(true);
			}
		}
	};
	// ----- [2025.01.05] 도구 서버 연결 지연으로 인한 로그인 차단 방지 종료 -----

	// ----- [2025.01.05] 외부 서버 (파서, 청크, 임베더) 연결 상태 체크 시작 -----
	const EXTERNAL_SERVER_TIMEOUT = 5000;

	// 외부 서버 설정 (환경에 맞게 수정 가능)
	const externalServers: { url: string; name: string; type: ExternalServerType }[] = [
		{ url: 'http://192.168.122.177:8100', name: 'Parser Server', type: 'parser' },
		{ url: 'http://192.168.122.177:8101', name: 'Chunker Server', type: 'chunker' },
		{ url: 'http://192.168.122.177:8102', name: 'Embedder Server', type: 'embedder' }
	];

	const checkExternalServer = async (server: { url: string; name: string; type: ExternalServerType }) => {
		const startTime = Date.now();
		updateServerStatus(server.url, 'connecting', { name: server.name, type: server.type });

		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), EXTERNAL_SERVER_TIMEOUT);

		try {
			const response = await fetch(`${server.url}/health`, {
				method: 'GET',
				signal: controller.signal
			});
			clearTimeout(timeoutId);

			const responseTime = Date.now() - startTime;
			if (response.ok) {
				updateServerStatus(server.url, 'connected', {
					name: server.name,
					type: server.type,
					responseTime
				});
			} else {
				updateServerStatus(server.url, 'error', {
					name: server.name,
					type: server.type,
					errorMessage: `HTTP ${response.status}`
				});
			}
		} catch (error: any) {
			clearTimeout(timeoutId);
			const isTimeout = error.name === 'AbortError';
			updateServerStatus(server.url, isTimeout ? 'timeout' : 'error', {
				name: server.name,
				type: server.type,
				errorMessage: isTimeout ? 'Connection timeout' : error.message
			});
		}
	};

	const checkAllExternalServers = async () => {
		await Promise.all(externalServers.map(server => checkExternalServer(server)));
	};
	// ----- [2025.01.05] 외부 서버 (파서, 청크, 임베더) 연결 상태 체크 종료 -----

	const setBanners = async () => {
		const bannersData = await getBanners(localStorage.token);
		banners.set(bannersData);
	};

	const setTools = async () => {
		const toolsData = await getTools(localStorage.token);
		tools.set(toolsData);
	};

	// ----- [2026.01.19] 모델 색상 설정 로드 함수 시작 -----
	const loadModelColors = async () => {
		try {
			const result = await getModelColors(localStorage.token);
			if (result?.colors && Array.isArray(result.colors)) {
				modelColors.set(result.colors);
			}
		} catch (e) {
			console.error('[Layout] 모델 색상 설정 로드 실패:', e);
		}
	};
	// ----- [2026.01.19] 모델 색상 설정 로드 함수 종료 -----

	// ----- [2026-02-04] 팝업 공지사항 로드 함수 시작 -----
	// 오늘 날짜 키 생성 (오늘 하루 보지 않기 체크용)
	const getAnnouncementDismissKey = () => {
		const today = new Date();
		return `popup_announcement_dismissed_${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
	};

	// ----- [2026-02-26] loadPopupAnnouncements 팝업 공지 로드 상세 설명 시작 -----
	// ■ 기능: 로그인 시 활성 공지사항을 API에서 가져와 팝업으로 표시
	//
	// ■ 호출 시점: onMount() → 페이지 최초 로드 시 자동 실행
	//
	// ■ 데이터 흐름:
	//   1. exportConfig(token) → GET /api/v1/configs/export
	//      → config 테이블에서 MAX_POPUP_COUNT 값 조회 (기본값 3)
	//   2. getActiveAnnouncements(token) → GET /api/v1/configs/announcements/active
	//      → 백엔드에서 MAX_POPUP_COUNT 적용하여 활성 공지 N개 반환
	//   3. 프론트엔드에서 start_date 내림차순 정렬 후 maxPopupCount개로 제한
	//   4. PopupAnnouncementModal 컴포넌트에 전달하여 팝업 표시
	//
	// ■ MAX_POPUP_COUNT 설정 변경 시 반영 경로:
	//   관리자 /admin/settings/notification에서 개수 변경
	//   → savePopupCount() → updateConfigPartial() → POST /api/v1/configs/import
	//   → config 테이블 data(JSONB) 저장
	//   → 다음 로그인 시 이 함수에서 새 값 적용
	// ----- [2026-02-26] loadPopupAnnouncements 팝업 공지 로드 상세 설명 종료 -----
	const loadPopupAnnouncements = async () => {
		try {
			console.log('[Layout] ===== 팝업 공지사항 로드 시작 =====');

			// ----- [2026-03-02] MAX_POPUP_COUNT 팝업 개수 적용 확인 시작 -----
			// ■ 확인: exportConfig(token) → GET /configs/export → get_verified_user
			//   관리자/일반사용자 모두 동일한 MAX_POPUP_COUNT 값 조회됨 (API 테스트 완료)
			// ■ 흐름: exportConfig → MAX_POPUP_COUNT 읽기 → getActiveAnnouncements → 팝업 표시
			// ----- [2026-03-02] MAX_POPUP_COUNT 팝업 개수 적용 확인 종료 -----
			// ----- [2026-02-05] 팝업 표시 개수 설정 로드 시작 -----
			// [2026-02-26] exportConfig로 MAX_POPUP_COUNT 조회 (config 테이블 → data JSONB)
			let maxPopupCount = 3; // 기본값
			try {
				const config = await exportConfig(localStorage.token);
				if (config && config.MAX_POPUP_COUNT !== undefined) {
					maxPopupCount = config.MAX_POPUP_COUNT;
				}
			} catch (configError) {
				console.log('[Layout] 팝업 개수 설정 로드 실패, 기본값 사용:', configError);
			}
			console.log('[Layout] 팝업 표시 개수 설정:', maxPopupCount);
			// ----- [2026-02-05] 팝업 표시 개수 설정 로드 종료 -----

			// [2026-02-26] 백엔드에서 MAX_POPUP_COUNT 적용된 활성 공지 반환
			const announcements = await getActiveAnnouncements(localStorage.token);
			console.log('[Layout] API 응답:', JSON.stringify(announcements));
			console.log('[Layout] 팝업 공지사항 로드:', announcements?.length || 0, '개');

			if (announcements && announcements.length > 0) {
				// ----- [2026-03-02] 프론트엔드 팝업 개수 제한 확인 시작 -----
				// ■ 확인: 백엔드(limit) + 프론트엔드(slice) 이중 제한 → 관리자/사용자 동일 적용
				// ----- [2026-03-02] 프론트엔드 팝업 개수 제한 확인 종료 -----
				// ----- [2026-02-05] 팝업 표시 개수 제한 적용 시작 -----
				// [2026-02-26] 프론트엔드에서도 start_date 내림차순 정렬 후 maxPopupCount개로 이중 제한
				const sortedAnnouncements = [...announcements].sort((a, b) => b.start_date - a.start_date);
				popupAnnouncements = sortedAnnouncements.slice(0, maxPopupCount);
				console.log('[Layout] 팝업 표시 개수 제한 적용:', popupAnnouncements.length, '/', announcements.length);
				// ----- [2026-02-05] 팝업 표시 개수 제한 적용 종료 -----
				showPopupAnnouncement = true;
				console.log('[Layout] showPopupAnnouncement 설정됨:', showPopupAnnouncement);
				console.log('[Layout] popupAnnouncements:', popupAnnouncements.length, '개');
			// DOM 업데이트 강제
				await tick();
				console.log("[Layout] tick() 완료 - DOM 업데이트됨");
				// DOM 요소 확인
				setTimeout(() => {
					const popupEl = document.querySelector(".z-\\[9999\\]");
					console.log("[Layout] DOM에 팝업 요소:", popupEl ? "존재함" : "없음", popupEl);
				}, 100);
			} else {
				console.log('[Layout] 활성 공지사항 없음');
			}
		} catch (e) {
			console.error('[Layout] 팝업 공지사항 로드 실패:', e);
		}
	};
	// ----- [2026-02-04] 팝업 공지사항 로드 함수 종료 -----

	onMount(async () => {
		console.log('[Layout] ===== onMount 시작 =====');
		console.log('[Layout] $user:', $user);

		if ($user === undefined || $user === null) {
			console.log('[Layout] 사용자 없음, /auth로 이동');
			await goto('/auth');
			return;
		}
		if (!['user', 'admin'].includes($user?.role)) {
			console.log('[Layout] 권한 없음, role:', $user?.role);
			return;
		}

		console.log('[Layout] Promise.all 시작');
		clearChatInputStorage();
		await Promise.all([
			checkLocalDBChats(),
			setBanners(),
			setTools(),
			setUserSettings(async () => {
				await Promise.all([setModels(), setToolServers()]);
			}),
			// ----- [2025.01.05] 외부 서버 (파서, 청크, 임베더) 연결 상태 체크 -----
			checkAllExternalServers(),
			// ----- [2026.01.19] 모델 색상 설정 로드 -----
			loadModelColors(),
			// ----- [2026-02-04] 팝업 공지사항 로드 -----
			loadPopupAnnouncements()
		]);

		const setupKeyboardShortcuts = () => {
			document.addEventListener('keydown', async function (event) {
				const isCtrlPressed = event.ctrlKey || event.metaKey; // metaKey is for Cmd key on Mac
				// Check if the Shift key is pressed
				const isShiftPressed = event.shiftKey;

				// Check if Ctrl  + K is pressed
				if (isCtrlPressed && event.key.toLowerCase() === 'k') {
					event.preventDefault();
					console.log('search');
					showSearch.set(!$showSearch);
				}

				// Check if Ctrl + Shift + O is pressed
				if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 'o') {
					event.preventDefault();
					console.log('newChat');
					document.getElementById('sidebar-new-chat-button')?.click();
				}

				// Check if Shift + Esc is pressed
				if (isShiftPressed && event.key === 'Escape') {
					event.preventDefault();
					console.log('focusInput');
					document.getElementById('chat-input')?.focus();
				}

				// Check if Ctrl + Shift + ; is pressed
				if (isCtrlPressed && isShiftPressed && event.key === ';') {
					event.preventDefault();
					console.log('copyLastCodeBlock');
					const button = [...document.getElementsByClassName('copy-code-button')]?.at(-1);
					button?.click();
				}

				// Check if Ctrl + Shift + C is pressed
				if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 'c') {
					event.preventDefault();
					console.log('copyLastResponse');
					const button = [...document.getElementsByClassName('copy-response-button')]?.at(-1);
					console.log(button);
					button?.click();
				}

				// Check if Ctrl + Shift + S is pressed
				if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 's') {
					event.preventDefault();
					console.log('toggleSidebar');
					document.getElementById('sidebar-toggle-button')?.click();
				}

				// Check if Ctrl + Shift + Backspace is pressed
				if (
					isCtrlPressed &&
					isShiftPressed &&
					(event.key === 'Backspace' || event.key === 'Delete')
				) {
					event.preventDefault();
					console.log('deleteChat');
					document.getElementById('delete-chat-button')?.click();
				}

				// Check if Ctrl + . is pressed
				if (isCtrlPressed && event.key === '.') {
					event.preventDefault();
					console.log('openSettings');
					showSettings.set(!$showSettings);
				}

				// Check if Ctrl + / is pressed
				if (isCtrlPressed && event.key === '/') {
					event.preventDefault();

					showShortcuts.set(!$showShortcuts);
				}

				// Check if Ctrl + Shift + ' is pressed
				if (
					isCtrlPressed &&
					isShiftPressed &&
					(event.key.toLowerCase() === `'` || event.key.toLowerCase() === `"`)
				) {
					event.preventDefault();
					console.log('temporaryChat');

					if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
						temporaryChatEnabled.set(true);
					} else {
						temporaryChatEnabled.set(!$temporaryChatEnabled);
					}

					await goto('/');
					const newChatButton = document.getElementById('new-chat-button');
					setTimeout(() => {
						newChatButton?.click();
					}, 0);
				}
			});
		};
		setupKeyboardShortcuts();

		// ----- [2026-02-04] 릴리스 노트 모달 비활성화 (팝업 공지와 충돌 방지) -----
		// if ($user?.role === 'admin' && ($settings?.showChangelog ?? true)) {
		// 	showChangelog.set($settings?.version !== $config.version);
		// }
		// ----- [2026-02-04] 릴리스 노트 모달 비활성화 종료 -----

		if ($user?.role === 'admin' || ($user?.permissions?.chat?.temporary ?? true)) {
			if ($page.url.searchParams.get('temporary-chat') === 'true') {
				temporaryChatEnabled.set(true);
			}

			if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
				temporaryChatEnabled.set(true);
			}
		}

		// Check for version updates
		if ($user?.role === 'admin' && $config?.features?.enable_version_update_check) {
			// Check if the user has dismissed the update toast in the last 24 hours
			if (localStorage.dismissedUpdateToast) {
				const dismissedUpdateToast = new Date(Number(localStorage.dismissedUpdateToast));
				const now = new Date();

				if (now - dismissedUpdateToast > 24 * 60 * 60 * 1000) {
					checkForVersionUpdates();
				}
			} else {
				checkForVersionUpdates();
			}
		}
		await tick();

		loaded = true;
	});

	const checkForVersionUpdates = async () => {
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});
	};

	// ----- [2026-02-04] 팝업 공지 상태 변경 감지 -----
	$: {
		console.log('[Layout] 팝업 조건 체크 - showPopupAnnouncement:', showPopupAnnouncement, ', length:', popupAnnouncements?.length);
		if (showPopupAnnouncement) {
			console.log('[Layout] 팝업 조건 TRUE - 모달이 표시되어야 함!');
		}
	}
</script>

<SettingsModal bind:show={$showSettings} />
<ChangelogModal bind:show={$showChangelog} />

<!-- ----- [2026-02-04] 팝업 공지사항 모달 (컴포넌트 사용) ----- -->
<PopupAnnouncementModal
	bind:show={showPopupAnnouncement}
	announcements={popupAnnouncements}
	on:close={() => { showPopupAnnouncement = false; }}
/>
<!-- ----- [2026-02-04] 팝업 공지사항 모달 종료 ----- -->

<!-- ----- [2026-02-04] 새 버전 안내 비활성화 (팝업 공지와 충돌 방지) ----- -->
{#if false && version && compareVersion(version.latest, version.current) && ($settings?.showUpdateToast ?? true)}
	<div class=" absolute bottom-8 right-8 z-50" in:fade={{ duration: 100 }}>
		<UpdateInfoToast
			{version}
			on:close={() => {
				localStorage.setItem('dismissedUpdateToast', Date.now().toString());
				version = null;
			}}
		/>
	</div>
{/if}
<!-- ----- [2026-02-04] 새 버전 안내 비활성화 종료 ----- -->

{#if $user}
	<div class="app relative">
		<div
			class=" text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900 h-screen max-h-[100dvh] overflow-auto flex flex-row justify-end"
		>
			{#if !['user', 'admin'].includes($user?.role)}
				<AccountPending />
			{:else}
				{#if localDBChats.length > 0}
					<div class="fixed w-full h-full flex z-50">
						<div
							class="absolute w-full h-full backdrop-blur-md bg-white/20 dark:bg-gray-900/50 flex justify-center"
						>
							<div class="m-auto pb-44 flex flex-col justify-center">
								<div class="max-w-md">
									<div class="text-center dark:text-white text-2xl font-medium z-50">
										{$i18n.t('Important Update')}<br />
										{$i18n.t('Action Required for Chat Log Storage')}
									</div>

									<div class=" mt-4 text-center text-sm dark:text-gray-200 w-full">
										{$i18n.t(
											"Saving chat logs directly to your browser's storage is no longer supported. Please take a moment to download and delete your chat logs by clicking the button below. Don't worry, you can easily re-import your chat logs to the backend through"
										)}
										<span class="font-semibold dark:text-white"
											>{$i18n.t('Settings')} > {$i18n.t('Chats')} > {$i18n.t('Import Chats')}</span
										>. {$i18n.t(
											'This ensures that your valuable conversations are securely saved to your backend database. Thank you!'
										)}
									</div>

									<div class=" mt-6 mx-auto relative group w-fit">
										<button
											class="relative z-20 flex px-5 py-2 rounded-full bg-white border border-gray-100 dark:border-none hover:bg-gray-100 transition font-medium text-sm"
											on:click={async () => {
												let blob = new Blob([JSON.stringify(localDBChats)], {
													type: 'application/json'
												});
												saveAs(blob, `chat-export-${Date.now()}.json`);

												const tx = DB.transaction('chats', 'readwrite');
												await Promise.all([tx.store.clear(), tx.done]);
												await deleteDB('Chats');

												localDBChats = [];
											}}
										>
											{$i18n.t('Download & Delete')}
										</button>

										<button
											class="text-xs text-center w-full mt-2 text-gray-400 underline"
											on:click={async () => {
												localDBChats = [];
											}}>{$i18n.t('Close')}</button
										>
									</div>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- 3분할 레이아웃: 왼쪽 사이드바 - 중앙 컨텐츠 - 오른쪽 사이드바 -->
				<div class="flex flex-1 h-full overflow-hidden">
					<!-- 왼쪽 사이드바 영역 -->
					{#if $showSidebar}
						<div class="w-[260px] h-full flex-shrink-0">
							<Sidebar />
						</div>
				{/if}

					<!-- 중앙 컨텐츠 영역 (동적 폭 조정) -->
					<div class="flex-1 h-full overflow-auto">
						{#if loaded}
							<slot />
						{:else}
							<div class="w-full h-full flex items-center justify-center">
								<Spinner className="size-5" />
							</div>
						{/if}
					</div>

					<!-- 오른쪽 사이드바는 Chat 컴포넌트의 Controls에서만 관리 -->
				</div>


			{/if}
		</div>
	</div>
{/if}

<style>
	.loading {
		display: inline-block;
		clip-path: inset(0 1ch 0 0);
		animation: l 1s steps(3) infinite;
		letter-spacing: -0.5px;
	}

	@keyframes l {
		to {
			clip-path: inset(0 -1ch 0 0);
		}
	}

	pre[class*='language-'] {
		position: relative;
		overflow: auto;

		/* make space  */
		margin: 5px 0;
		padding: 1.75rem 0 1.75rem 1rem;
		border-radius: 10px;
	}

	pre[class*='language-'] button {
		position: absolute;
		top: 5px;
		right: 5px;

		font-size: 0.9rem;
		padding: 0.15rem;
		background-color: #828282;

		border: ridge 1px #7b7b7c;
		border-radius: 5px;
		text-shadow: #c4c4c4 0 0 2px;
	}

	pre[class*='language-'] button:hover {
		cursor: pointer;
		background-color: #bcbabb;
	}
</style>
