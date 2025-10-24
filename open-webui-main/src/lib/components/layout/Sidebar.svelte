<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';

	import { goto } from '$app/navigation';
	import {
		user,
		chats,
		settings,
		showSettings,
		chatId,
		tags,
		folders as _folders,
		showSidebar,
		showSearch,
		mobile,
		showArchivedChats,
		pinnedChats,
		scrollPaginationEnabled,
		currentChatPage,
		temporaryChatEnabled,
		channels,
		socket,
		config,
		isApp,
		models,
		selectedFolder,
		WEBUI_NAME,
		modelType
	} from '$lib/stores';
	import { onMount, getContext, tick, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	import {
		getChatList,
		getAllTags,
		getPinnedChatList,
		toggleChatPinnedStatusById,
		getChatById,
		updateChatFolderIdById,
		importChat,
		createNewChat,
		deleteAllChats
	} from '$lib/apis/chats';
	import { createNewFolder, getFolders, updateFolderParentIdById } from '$lib/apis/folders';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import ArchivedChatsModal from './ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import Folder from '../common/Folder.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import { getChannels, createNewChannel } from '$lib/apis/channels';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Search from '../icons/Search.svelte';
	import SearchModal from './SearchModal.svelte';
	import FolderModal from './Sidebar/Folders/FolderModal.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import PinnedModelList from './Sidebar/PinnedModelList.svelte';
	import Note from '../icons/Note.svelte';
	import Database from '../icons/Database.svelte';
	import Refresh from '../icons/Refresh.svelte';
	import XMark from '../icons/XMark.svelte';
	import { slide } from 'svelte/transition';

	const BREAKPOINT = 768;

	let scrollTop = 0;

	let navElement;
	let shiftKey = false;

	let selectedChatId = null;
	let showPinnedChat = true;

	let showCreateChannel = false;

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	let showCreateFolderModal = false;

	let folders = {};
	let folderRegistry = {};

	let newFolderId = null;

	// Filtered chats based on model type
	let filteredChats = [];
	$: filteredChats = $chats?.filter(chat => {
		// If chat doesn't have model type info yet, show in internal by default
		if (!chat.models || chat.models.length === 0) {
			return $modelType === 'internal';
		}

		// Check if any of the chat's models match the current model type
		const chatModels = Array.isArray(chat.models) ? chat.models : [chat.models];
		const isExternal = chatModels.some(modelId => {
			const model = $models.find(m => m.id === modelId);
			return model?.external === true;
		});

		return ($modelType === 'external' && isExternal) || ($modelType === 'internal' && !isExternal);
	}) || [];

	const initFolders = async () => {
		const folderList = await getFolders(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return [];
		});
		_folders.set(folderList.sort((a, b) => b.updated_at - a.updated_at));

		folders = {};

		// First pass: Initialize all folder entries
		for (const folder of folderList) {
			// Ensure folder is added to folders with its data
			folders[folder.id] = { ...(folders[folder.id] || {}), ...folder };

			if (newFolderId && folder.id === newFolderId) {
				folders[folder.id].new = true;
				newFolderId = null;
			}
		}

		// Second pass: Tie child folders to their parents
		for (const folder of folderList) {
			if (folder.parent_id) {
				// Ensure the parent folder is initialized if it doesn't exist
				if (!folders[folder.parent_id]) {
					folders[folder.parent_id] = {}; // Create a placeholder if not already present
				}

				// Initialize childrenIds array if it doesn't exist and add the current folder id
				folders[folder.parent_id].childrenIds = folders[folder.parent_id].childrenIds
					? [...folders[folder.parent_id].childrenIds, folder.id]
					: [folder.id];

				// Sort the children by updated_at field
				folders[folder.parent_id].childrenIds.sort((a, b) => {
					return folders[b].updated_at - folders[a].updated_at;
				});
			}
		}
	};

	const createFolder = async ({ name, data }) => {
		if (name === '') {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const rootFolders = Object.values(folders).filter((folder) => folder.parent_id === null);
		if (rootFolders.find((folder) => folder.name.toLowerCase() === name.toLowerCase())) {
			// If a folder with the same name already exists, append a number to the name
			let i = 1;
			while (
				rootFolders.find((folder) => folder.name.toLowerCase() === `${name} ${i}`.toLowerCase())
			) {
				i++;
			}

			name = `${name} ${i}`;
		}

		// Add a dummy folder to the list to show the user that the folder is being created
		const tempId = uuidv4();
		folders = {
			...folders,
			tempId: {
				id: tempId,
				name: name,
				created_at: Date.now(),
				updated_at: Date.now()
			}
		};

		const res = await createNewFolder(localStorage.token, {
			name,
			data
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// newFolderId = res.id;
			await initFolders();
		}
	};

	const initChannels = async () => {
		await channels.set(await getChannels(localStorage.token));
	};

	const initChatList = async () => {
		// Reset pagination variables
		console.log('🔄 [Sidebar] initChatList started');
		currentChatPage.set(1);
		allChatsLoaded = false;

		initFolders();
		await Promise.all([
			await (async () => {
				console.log('📌 [Sidebar] Init tags');
				const _tags = await getAllTags(localStorage.token);
				tags.set(_tags);
				console.log('✅ [Sidebar] Tags loaded:', _tags?.length || 0);
			})(),
			await (async () => {
				console.log('📍 [Sidebar] Init pinned chats');
				const _pinnedChats = await getPinnedChatList(localStorage.token);
				pinnedChats.set(_pinnedChats);
				console.log('✅ [Sidebar] Pinned chats loaded:', _pinnedChats?.length || 0);
			})(),
			await (async () => {
				console.log('💬 [Sidebar] Init chat list');
				const _chats = await getChatList(localStorage.token, $currentChatPage);
				await chats.set(_chats);
				console.log('✅ [Sidebar] Chats loaded:', _chats?.length || 0, _chats);
			})()
		]);

		// Enable pagination
		scrollPaginationEnabled.set(true);
		console.log('✨ [Sidebar] initChatList completed');
	};

	const loadMoreChats = async () => {
		chatListLoading = true;

		currentChatPage.set($currentChatPage + 1);

		let newChatList = [];

		newChatList = await getChatList(localStorage.token, $currentChatPage);

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;
		await chats.set([...($chats ? $chats : []), ...newChatList]);

		chatListLoading = false;
	};

	const importChatHandler = async (items, pinned = false, folderId = null) => {
		console.log('importChatHandler', items, pinned, folderId);
		for (const item of items) {
			console.log(item);
			if (item.chat) {
				await importChat(
					localStorage.token,
					item.chat,
					item?.meta ?? {},
					pinned,
					folderId,
					item?.created_at ?? null,
					item?.updated_at ?? null
				);
			}
		}

		initChatList();
	};

	const inputFilesHandler = async (files) => {
		console.log(files);

		for (const file of files) {
			const reader = new FileReader();
			reader.onload = async (e) => {
				const content = e.target.result;

				try {
					const chatItems = JSON.parse(content);
					importChatHandler(chatItems);
				} catch {
					toast.error($i18n.t(`Invalid file format.`));
				}
			};

			reader.readAsText(file);
		}
	};

	const tagEventHandler = async (type, tagName, chatId) => {
		console.log(type, tagName, chatId);
		if (type === 'delete') {
			initChatList();
		} else if (type === 'add') {
			initChatList();
		}
	};

	let draggedOver = false;

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being draggedOver.
		if (e.dataTransfer?.types?.includes('Files')) {
			draggedOver = true;
		} else {
			draggedOver = false;
		}
	};

	const onDragLeave = () => {
		draggedOver = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		console.log(e); // Log the drop event

		// Perform file drop check and handle it accordingly
		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer?.files);

			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles); // Log the dropped files
				inputFilesHandler(inputFiles); // Handle the dropped files
			}
		}

		draggedOver = false; // Reset draggedOver status after drop
	};

	let touchstart;
	let touchend;

	function checkDirection() {
		const screenWidth = window.innerWidth;
		const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);
		if (touchstart.clientX < 40 && swipeDistance >= screenWidth / 8) {
			if (touchend.screenX < touchstart.screenX) {
				showSidebar.set(false);
			}
			if (touchend.screenX > touchstart.screenX) {
				showSidebar.set(true);
			}
		}
	}

	const onTouchStart = (e) => {
		touchstart = e.changedTouches[0];
		console.log(touchstart.clientX);
	};

	const onTouchEnd = (e) => {
		touchend = e.changedTouches[0];
		checkDirection();
	};

	const onKeyDown = (e) => {
		if (e.key === 'Shift') {
			shiftKey = true;
		}
	};

	const onKeyUp = (e) => {
		if (e.key === 'Shift') {
			shiftKey = false;
		}
	};

	const onFocus = () => {};

	const onBlur = () => {
		shiftKey = false;
		selectedChatId = null;
	};

	let unsubscribers = [];
	onMount(async () => {
		showPinnedChat = localStorage?.showPinnedChat ? localStorage.showPinnedChat === 'true' : true;
		await showSidebar.set(!$mobile ? localStorage.sidebar === 'true' : false);

		unsubscribers = [
			mobile.subscribe((value) => {
				console.log('📱 [Sidebar] mobile changed:', value);
				if ($showSidebar && value) {
					showSidebar.set(false);
				}

				if ($showSidebar && !value) {
					const navElement = document.getElementsByTagName('nav')[0];
					if (navElement) {
						navElement.style['-webkit-app-region'] = 'drag';
					}
				}

				if (!$showSidebar && !value) {
					showSidebar.set(true);
				}
			}),
			showSidebar.subscribe(async (value) => {
				console.log('👁️ [Sidebar] showSidebar changed:', value);
				localStorage.sidebar = value;

				// nav element is not available on the first render
				const navElement = document.getElementsByTagName('nav')[0];

				if (navElement) {
					if ($mobile) {
						if (!value) {
							navElement.style['-webkit-app-region'] = 'drag';
						} else {
							navElement.style['-webkit-app-region'] = 'no-drag';
						}
					} else {
						navElement.style['-webkit-app-region'] = 'drag';
					}
				}

				if (value) {
					console.log('🚀 [Sidebar] Sidebar opened - loading data...');
					await initChannels();
					await initChatList();
				} else {
					console.log('🚪 [Sidebar] Sidebar closed');
				}
			})
		];

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('touchstart', onTouchStart);
		window.addEventListener('touchend', onTouchEnd);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur', onBlur);

		const dropZone = document.getElementById('sidebar');

		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		if (unsubscribers && unsubscribers.length > 0) {
			unsubscribers.forEach((unsubscriber) => {
				if (unsubscriber) {
					unsubscriber();
				}
			});
		}

		window.removeEventListener('keydown', onKeyDown);
		window.removeEventListener('keyup', onKeyUp);

		window.removeEventListener('touchstart', onTouchStart);
		window.removeEventListener('touchend', onTouchEnd);

		window.removeEventListener('focus', onFocus);
		window.removeEventListener('blur', onBlur);

		const dropZone = document.getElementById('sidebar');

		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});

	const newChatHandler = async () => {
		selectedChatId = null;
		selectedFolder.set(null);

		if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
			await temporaryChatEnabled.set(true);
		} else {
			await temporaryChatEnabled.set(false);
		}

		// 첫 화면으로 이동
		await goto('/');

		setTimeout(() => {
			if ($mobile) {
				showSidebar.set(false);
			}
		}, 0);
	};

	// 새로운 채팅 세션 생성 (API 사용)
	const createNewChatSession = async () => {
		try {
			const newChat = {
				id: uuidv4(),
				title: $i18n.t('New Chat'),
				models: [],
				messages: [],
				history: { messages: {}, currentId: null },
				tags: [],
				timestamp: Math.floor(Date.now() / 1000)
			};

			await createNewChat(localStorage.token, newChat, null);

			// 채팅 리스트 새로고침
			await initChatList();

			// 새 채팅으로 이동
			goto('/');
			newChatHandler();

			toast.success($i18n.t('New chat session created'));
		} catch (error) {
			console.error('Error creating new chat:', error);
			toast.error($i18n.t('Failed to create new chat session'));
		}
	};

	// 전체 채팅 삭제
	const deleteAllChatsHandler = async () => {
		const confirmed = confirm($i18n.t('Are you sure you want to delete all chats? This action cannot be undone.'));

		if (!confirmed) return;

		try {
			await deleteAllChats(localStorage.token);

			// 채팅 리스트 초기화
			chats.set([]);

			// 홈으로 이동
			goto('/');
			newChatHandler();

			toast.success($i18n.t('All chats deleted successfully'));
		} catch (error) {
			console.error('Error deleting all chats:', error);
			toast.error($i18n.t('Failed to delete all chats'));
		}
	};

	const itemClickHandler = async () => {
		selectedChatId = null;
		chatId.set('');

		if ($mobile) {
			showSidebar.set(false);
		}

		await tick();
	};

	const isWindows = /Windows/i.test(navigator.userAgent);
</script>

<ArchivedChatsModal
	bind:show={$showArchivedChats}
	onUpdate={async () => {
		await initChatList();
	}}
/>

<ChannelModal
	bind:show={showCreateChannel}
	onSubmit={async ({ name, access_control }) => {
		const res = await createNewChannel(localStorage.token, {
			name: name,
			access_control: access_control
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			$socket.emit('join-channels', { auth: { token: $user?.token } });
			await initChannels();
			showCreateChannel = false;
		}
	}}
/>

<FolderModal
	bind:show={showCreateFolderModal}
	onSubmit={async (folder) => {
		await createFolder(folder);
		showCreateFolderModal = false;
	}}
/>

<!-- svelte-ignore a11y-no-static-element-interactions -->

{#if $showSidebar}
	<div
		class=" {$isApp
			? ' ml-[4.5rem] md:ml-0'
			: ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showSidebar.set(!$showSidebar);
		}}
	/>
{/if}

<SearchModal
	bind:show={$showSearch}
	onClose={() => {
		if ($mobile) {
			showSidebar.set(false);
		}
	}}
/>

<button
	id="sidebar-new-chat-button"
	class="hidden"
	on:click={() => {
		goto('/');
		newChatHandler();
	}}
/>

{#if !$mobile && !$showSidebar}
	<div
		class=" py-2 px-1.5 flex flex-col justify-between text-black dark:text-white hover:bg-gray-50/50 dark:hover:bg-gray-950/50 h-full border-e border-gray-50 dark:border-gray-850 z-10 transition-all"
		id="sidebar"
	>
		<button
			class="flex flex-col flex-1 {isWindows ? 'cursor-pointer' : 'cursor-[e-resize]'}"
			on:click={async () => {
				showSidebar.set(!$showSidebar);
			}}
		>
			<div class="pb-1.5">
				<Tooltip
					content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					placement="right"
				>
					<button
						class="flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group {isWindows
							? 'cursor-pointer'
							: 'cursor-[e-resize]'}"
						aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					>
						<div class=" self-center flex items-center justify-center size-9">
							<img
								crossorigin="anonymous"
								src="{WEBUI_BASE_URL}/static/favicon.png"
								class="sidebar-new-chat-icon size-6 rounded-full group-hover:hidden"
								alt=""
							/>

							<!-- 햄버거 메뉴 아이콘 (호버시) -->
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-5 hidden group-hover:flex"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
								/>
							</svg>
						</div>
					</button>
				</Tooltip>
			</div>

			<div>
				<div class="">
					<Tooltip content={$i18n.t('New Chat')} placement="right">
						<a
							class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
							href="/"
							draggable="false"
							on:click={async (e) => {
								e.stopImmediatePropagation();
								e.preventDefault();

								goto('/');
								newChatHandler();
							}}
							aria-label={$i18n.t('New Chat')}
						>
							<div class=" self-center flex items-center justify-center size-9">
								<PencilSquare className="size-4.5" />
							</div>
						</a>
					</Tooltip>
				</div>

				<!-- 새로운 채팅 세션 생성 버튼 -->
				<div class="">
					<Tooltip content="새 채팅 세션" placement="right">
						<button
							class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
							on:click={async (e) => {
								e.stopImmediatePropagation();
								e.preventDefault();

								await createNewChatSession();
							}}
							draggable="false"
							aria-label="새 채팅 세션"
						>
							<div class=" self-center flex items-center justify-center size-9">
								<Refresh className="size-4.5" />
							</div>
						</button>
					</Tooltip>
				</div>

				<!-- 전체 채팅 삭제 버튼 -->
				<div class="">
					<Tooltip content="전체 삭제" placement="right">
						<button
							class=" cursor-pointer flex rounded-xl hover:bg-red-100 dark:hover:bg-red-900/30 transition group text-red-600 dark:text-red-400"
							on:click={async (e) => {
								e.stopImmediatePropagation();
								e.preventDefault();

								await deleteAllChatsHandler();
							}}
							draggable="false"
							aria-label="전체 채팅 삭제"
						>
							<div class=" self-center flex items-center justify-center size-9">
								<XMark className="size-4.5" />
							</div>
						</button>
					</Tooltip>
				</div>

				<div class="">
					<Tooltip content={$i18n.t('Search')} placement="right">
						<button
							class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
							on:click={(e) => {
								e.stopImmediatePropagation();
								e.preventDefault();

								showSearch.set(true);
							}}
							draggable="false"
							aria-label={$i18n.t('Search')}
						>
							<div class=" self-center flex items-center justify-center size-9">
								<Search className="size-4.5" />
							</div>
						</button>
					</Tooltip>
				</div>

				{#if ($config?.features?.enable_notes ?? false) && ($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))}
					<div class="">
						<Tooltip content={$i18n.t('Notes')} placement="right">
							<a
								class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
								href="/notes"
								on:click={async (e) => {
									e.stopImmediatePropagation();
									e.preventDefault();

									goto('/notes');
									itemClickHandler();
								}}
								draggable="false"
								aria-label={$i18n.t('Notes')}
							>
								<div class=" self-center flex items-center justify-center size-9">
									<Note className="size-4.5" />
								</div>
							</a>
						</Tooltip>
					</div>
				{/if}

			{#if $user?.role === 'admin' || $user?.permissions?.workspace?.knowledge}
				<div class="">
					<Tooltip content={$i18n.t('Knowledge')} placement="right">
						<a
							class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
							href="/workspace/knowledge"
							on:click={async (e) => {
								e.stopImmediatePropagation();
								e.preventDefault();

								goto('/workspace/knowledge');
								itemClickHandler();
							}}
							draggable="false"
							aria-label={$i18n.t('Knowledge')}
						>
							<div class=" self-center flex items-center justify-center size-9">
								<Database className="size-4.5" />
							</div>
						</a>
					</Tooltip>
				</div>
			{/if}

				{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models || $user?.permissions?.workspace?.knowledge || $user?.permissions?.workspace?.prompts || $user?.permissions?.workspace?.tools}
					<div class="">
						<Tooltip content={$i18n.t('Workspace')} placement="right">
							<a
								class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
								href="/workspace"
								on:click={async (e) => {
									e.stopImmediatePropagation();
									e.preventDefault();

									goto('/workspace');
									itemClickHandler();
								}}
								aria-label={$i18n.t('Workspace')}
								draggable="false"
							>
								<div class=" self-center flex items-center justify-center size-9">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-4.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
										/>
									</svg>
								</div>
							</a>
						</Tooltip>
					</div>
				{/if}
			</div>
		</button>

		<div>
			<div>
				<div class=" py-0.5">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							role={$user?.role}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<div
								class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
							>
								<div class=" self-center flex items-center justify-center size-9">
									<img
										src={$user?.profile_image_url}
										class=" size-6 object-cover rounded-full"
										alt={$i18n.t('Open User Profile Menu')}
										aria-label={$i18n.t('Open User Profile Menu')}
									/>
								</div>
							</div>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}

{#if $showSidebar}
	<div
		bind:this={navElement}
		id="sidebar"
		class="h-screen max-h-[100dvh] min-h-screen select-none {$showSidebar
			? 'bg-gradient-to-br from-gray-50 via-gray-100/30 to-gray-50 dark:from-gray-950 dark:via-gray-900/50 dark:to-gray-950 z-50 shadow-xl border-r border-gray-200/50 dark:border-gray-800/50'
			: ' bg-transparent z-0 '} {$isApp
			? `ml-[4.5rem] md:ml-0 `
			: ' transition-all duration-300 '} shrink-0 text-gray-900 dark:text-gray-200 text-sm fixed top-0 left-0 overflow-x-hidden
        "
		transition:slide={{ duration: 250, axis: 'x' }}
		data-state={$showSidebar}
	>
		<div
			class=" my-auto flex flex-col justify-between h-screen max-h-[100dvh] w-[260px] overflow-x-hidden scrollbar-hidden z-50 {$showSidebar
				? ''
				: 'invisible'}"
		>
			<div
				class="sidebar px-2 pt-2 pb-1.5 flex justify-between space-x-1 text-gray-600 dark:text-gray-400 sticky top-0 z-10 -mb-3 bg-gradient-to-b from-white/80 via-gray-50/50 to-transparent dark:from-gray-900/80 dark:via-gray-950/50 dark:to-transparent backdrop-blur-sm"
			>
				<a href="/" class="flex flex-1 px-1.5" on:click={newChatHandler}>
					<div class=" self-center font-medium text-gray-850 dark:text-white font-primary">
						ChatPro
					</div>
				</a>
				<Tooltip
					content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					placement="bottom"
				>
					<button
						class="flex rounded-xl size-8.5 justify-center items-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition {isWindows
							? 'cursor-pointer'
							: 'cursor-[w-resize]'}"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					>
						<div class="self-center p-1.5">
							<!-- 햄버거 메뉴 아이콘 -->
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
								/>
							</svg>
						</div>
					</button>
				</Tooltip>

				<!-- 새 채팅 세션 버튼 -->
				<Tooltip content="새 채팅 세션" placement="bottom">
					<button
						class="flex rounded-xl size-8.5 justify-center items-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition"
						on:click={async (e) => {
							e.stopImmediatePropagation();
							e.preventDefault();
							await createNewChatSession();
						}}
						aria-label="새 채팅 세션"
					>
						<div class="self-center p-1.5">
							<Refresh className="size-4.5" />
						</div>
					</button>
				</Tooltip>

				<!-- 전체 삭제 버튼 -->
				<Tooltip content="전체 삭제" placement="bottom">
					<button
						class="flex rounded-xl size-8.5 justify-center items-center hover:bg-red-100/50 dark:hover:bg-red-900/30 transition text-red-600 dark:text-red-400"
						on:click={async (e) => {
							e.stopImmediatePropagation();
							e.preventDefault();
							await deleteAllChatsHandler();
						}}
						aria-label="전체 채팅 삭제"
					>
						<div class="self-center p-1.5">
							<XMark className="size-4.5" />
						</div>
					</button>
				</Tooltip>

				<div
					class="{scrollTop > 0
						? 'visible'
						: 'invisible'} sidebar-bg-gradient-to-b bg-linear-to-b from-gray-50 dark:from-gray-950 to-transparent from-50% pointer-events-none absolute inset-0 -z-10 -mb-6"
				></div>
			</div>

			<!-- 채팅 히스토리 헤더 - 상단 헤더 바로 아래 고정 -->
			<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-950 sticky top-[52px] z-10">
				<div class="flex items-center justify-between">
					<h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
						<span>📝</span>
						<span>채팅 히스토리</span>
					</h3>
					<span class="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full font-medium">
						{filteredChats?.length || 0}
					</span>
				</div>
			</div>

			<!-- 채팅 히스토리 컨텐츠 영역 -->
			<div
				class="flex-1 flex flex-col overflow-y-auto scrollbar-hidden"
				on:scroll={(e) => {
					if (e.target.scrollTop === 0) {
						scrollTop = 0;
					} else {
						scrollTop = e.target.scrollTop;
					}
				}}
			>
				<!-- 채팅 히스토리 표시 -->
				{#if filteredChats && filteredChats.length > 0}
					<div class="py-2 px-2">
						{#each filteredChats as chat, idx (`chat-history-${chat?.id ?? idx}`)}
							{#if idx === 0 || (idx > 0 && chat.time_range !== filteredChats[idx - 1].time_range)}
								<div class="px-2 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 {idx === 0 ? '' : 'pt-4'}">
									{$i18n.t(chat.time_range)}
								</div>
							{/if}

							<button
								class="w-full text-left px-2 py-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition group border border-gray-200/50 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600"
								on:click={() => {
									goto(`/c/${chat.id}`);
									if ($mobile) {
										showSidebar.set(false);
									}
								}}
							>
								<div class="flex items-start gap-2">
									<div class="flex-shrink-0 mt-1">
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-4 h-4 text-gray-400 dark:text-gray-500">
											<path fill-rule="evenodd" d="M1 8.74c0 .983.713 1.825 1.69 1.943.904.108 1.817.19 2.737.243.363.02.688.231.85.556l1.052 2.103a.75.75 0 0 0 1.342 0l1.052-2.103c.162-.325.487-.535.85-.556.92-.053 1.833-.134 2.738-.243.976-.118 1.689-.96 1.689-1.942V4.259c0-.982-.713-1.824-1.69-1.942a44.45 44.45 0 0 0-10.62 0C1.712 2.435 1 3.277 1 4.26V8.74Z" clip-rule="evenodd" />
										</svg>
									</div>
									<div class="flex-1 min-w-0">
										<p class="text-sm text-gray-800 dark:text-gray-200 truncate font-medium">
											{chat.title}
										</p>
										{#if chat.updated_at}
											<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
												{new Date(chat.updated_at * 1000).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
											</p>
										{/if}
									</div>
								</div>
							</button>
						{/each}
					</div>
				{:else if filteredChats && filteredChats.length === 0 && $chats && $chats.length > 0}
					<div class="flex-1 flex flex-col items-center justify-center px-4">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
						</svg>
						<p class="text-sm text-gray-500 dark:text-gray-400 text-center font-medium">
							{$modelType === 'internal' ? '내부 모델' : '외부 모델'} 채팅 히스토리가 없습니다
						</p>
						<p class="text-xs text-gray-400 dark:text-gray-500 text-center mt-2">
							{$modelType === 'internal' ? '내부 모델로' : '외부 모델로'} 대화를 시작해보세요
						</p>
					</div>
				{:else if $chats && $chats.length === 0}
					<div class="flex-1 flex flex-col items-center justify-center px-4">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
						</svg>
						<p class="text-sm text-gray-500 dark:text-gray-400 text-center font-medium">
							아직 채팅 히스토리가 없습니다
						</p>
						<p class="text-xs text-gray-400 dark:text-gray-500 text-center mt-2">
							새로운 대화를 시작해보세요
						</p>
					</div>
				{:else}
					<div class="flex-1 flex items-center justify-center">
						<Spinner className="size-5" />
					</div>
				{/if}
			</div>

			<div class="px-1.5 pt-1.5 pb-2 sticky bottom-0 z-10 -mt-3 sidebar">
				<div
					class=" sidebar-bg-gradient-to-t bg-linear-to-t from-white/90 via-gray-50/70 dark:from-gray-900/90 dark:via-gray-950/70 to-transparent from-40% pointer-events-none absolute inset-0 -z-10 -mt-6 backdrop-blur-sm"
				></div>
				<div class="flex flex-col font-primary">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							role={$user?.role}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<div
								class=" flex items-center rounded-2xl py-2 px-1.5 w-full hover:bg-gray-100/50 dark:hover:bg-gray-900/50 transition"
							>
								<div class=" self-center mr-3">
									<img
										src={$user?.profile_image_url}
										class=" size-6 object-cover rounded-full"
										alt={$i18n.t('Open User Profile Menu')}
										aria-label={$i18n.t('Open User Profile Menu')}
									/>
								</div>
								<div class=" self-center font-medium">{$user?.name}</div>
							</div>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
