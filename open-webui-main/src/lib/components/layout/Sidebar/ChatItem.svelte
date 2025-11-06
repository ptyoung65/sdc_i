<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto, invalidate, invalidateAll } from '$app/navigation';
	import { onMount, getContext, createEventDispatcher, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	const dispatch = createEventDispatcher();

	import {
		archiveChatById,
		cloneChatById,
		deleteChatById,
		getAllTags,
		getChatById,
		getChatList,
		getChatListByTagName,
		getPinnedChatList,
		updateChatById,
		updateChatFolderIdById
	} from '$lib/apis/chats';
	import {
		chatId,
		chatTitle as _chatTitle,
		chats,
		mobile,
		pinnedChats,
		showSidebar,
		currentChatPage,
		tags,
		selectedFolder
	} from '$lib/stores';

	import ChatMenu from './ChatMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ShareChatModal from '$lib/components/chat/ShareChatModal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import DragGhost from '$lib/components/common/DragGhost.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import { generateTitle } from '$lib/apis';

	export let className = '';

	export let id;
	export let title;

	export let selected = false;
	export let shiftKey = false;

	export let onDragEnd = () => {};

	let chat = null;
	let draggable = true;

	// 롤오버 기능 제거 - 더 이상 마우스 오버 시 자동 로드하지 않음
	// mouseOver 시 chat 로드 기능 제거됨

	let showShareChatModal = false;
	let confirmEdit = false;

	let chatTitle = title;

	const editChatTitle = async (id, title) => {
		if (title === '') {
			toast.error($i18n.t('Title cannot be an empty string.'));
		} else {
			await updateChatById(localStorage.token, id, {
				title: title
			});

			if (id === $chatId) {
				_chatTitle.set(title);
			}

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			await pinnedChats.set(await getPinnedChatList(localStorage.token));

			dispatch('change');
		}
	};

	const cloneChatHandler = async (id) => {
		const res = await cloneChatById(
			localStorage.token,
			id,
			$i18n.t('Clone of {{TITLE}}', {
				TITLE: title
			})
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			goto(`/c/${res.id}`);

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			await pinnedChats.set(await getPinnedChatList(localStorage.token));
		}
	};

	const deleteChatHandler = async (id) => {
		const res = await deleteChatById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			tags.set(await getAllTags(localStorage.token));
			if ($chatId === id) {
				await goto('/');

				await chatId.set('');
				await tick();
			}

			dispatch('change');
		}
	};

	const archiveChatHandler = async (id) => {
		await archiveChatById(localStorage.token, id);
		dispatch('change');
	};

	const moveChatHandler = async (chatId, folderId) => {
		console.log('🔍 [moveChatHandler] Called with:', { chatId, folderId });

		if (chatId && folderId) {
			console.log('✅ [moveChatHandler] Both chatId and folderId are valid, calling API...');
			const res = await updateChatFolderIdById(localStorage.token, chatId, folderId).catch(
				(error) => {
					console.error('❌ [moveChatHandler] API Error:', error);
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				console.log('✅ [moveChatHandler] API Success:', res);
				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
				await pinnedChats.set(await getPinnedChatList(localStorage.token));

				dispatch('change');

				toast.success($i18n.t('Chat moved successfully'));
			}
		} else {
			console.error('❌ [moveChatHandler] Missing parameter:', { chatId, folderId });
			toast.error($i18n.t('Failed to move chat'));
		}
	};

	let itemElement;

	let generating = false;

	let ignoreBlur = false;
	let doubleClicked = false;

	let dragged = false;
	let x = 0;
	let y = 0;

	const dragImage = new Image();
	dragImage.src =
		'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

	const onDragStart = (event) => {
		event.stopPropagation();

		event.dataTransfer.setDragImage(dragImage, 0, 0);

		// Set the data to be transferred
		event.dataTransfer.setData(
			'text/plain',
			JSON.stringify({
				type: 'chat',
				id: id,
				item: chat
			})
		);

		dragged = true;
		itemElement.style.opacity = '0.5'; // Optional: Visual cue to show it's being dragged
	};

	const onDrag = (event) => {
		event.stopPropagation();

		x = event.clientX;
		y = event.clientY;
	};

	const onDragEndHandler = (event) => {
		event.stopPropagation();

		itemElement.style.opacity = '1'; // Reset visual cue after drag
		dragged = false;

		onDragEnd(event);
	};

	const onClickOutside = (event) => {
		if (confirmEdit && !event.target.closest(`#chat-title-input-${id}`)) {
			confirmEdit = false;
			ignoreBlur = false;
			chatTitle = '';
		}
	};

	onMount(() => {
		if (itemElement) {
			document.addEventListener('click', onClickOutside, true);

			// Event listener for when dragging starts
			itemElement.addEventListener('dragstart', onDragStart);
			// Event listener for when dragging occurs (optional)
			itemElement.addEventListener('drag', onDrag);
			// Event listener for when dragging ends
			itemElement.addEventListener('dragend', onDragEndHandler);
		}
	});

	onDestroy(() => {
		if (itemElement) {
			document.removeEventListener('click', onClickOutside, true);

			itemElement.removeEventListener('dragstart', onDragStart);
			itemElement.removeEventListener('drag', onDrag);
			itemElement.removeEventListener('dragend', onDragEndHandler);
		}
	});

	let showDeleteConfirm = false;

	const chatTitleInputKeydownHandler = (e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			setTimeout(() => {
				const input = document.getElementById(`chat-title-input-${id}`);
				if (input) input.blur();
			}, 0);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			confirmEdit = false;
			chatTitle = '';
		}
	};

	const renameHandler = async () => {
		chatTitle = title;
		confirmEdit = true;

		await tick();

		setTimeout(() => {
			const input = document.getElementById(`chat-title-input-${id}`);
			if (input) {
				input.focus();
				input.select();
			}
		}, 0);
	};

	const generateTitleHandler = async () => {
		generating = true;
		if (!chat) {
			chat = await getChatById(localStorage.token, id);
		}

		const messages = (chat.chat?.messages ?? []).map((message) => {
			return {
				role: message.role,
				content: message.content
			};
		});

		const model = chat.chat.models.at(0) ?? chat.models.at(0) ?? '';

		chatTitle = '';

		const generatedTitle = await generateTitle(localStorage.token, model, messages).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (generatedTitle) {
			if (generatedTitle !== title) {
				editChatTitle(id, generatedTitle);
			}

			confirmEdit = false;
		} else {
			chatTitle = title;
		}

		generating = false;
	};
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={id} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={`${title} 을(를) 대화이력에서 삭제합니다`}
	on:confirm={() => {
		deleteChatHandler(id);
	}}
>
	<div class=" text-sm text-gray-500 flex-1 line-clamp-3">
		이 작업은 취소할 수 없습니다.
	</div>
</DeleteConfirmDialog>

{#if dragged && x && y}
	<DragGhost {x} {y}>
		<div class=" bg-black/80 backdrop-blur-2xl px-2 py-1 rounded-lg w-fit max-w-40">
			<div class="flex items-center gap-1">
				<Document className=" size-[18px]" strokeWidth="2" />
				<div class=" text-xs text-white line-clamp-1">
					{title}
				</div>
			</div>
		</div>
	</DragGhost>
{/if}

<div
	id="sidebar-chat-group"
	bind:this={itemElement}
	class=" w-full {className} relative group"
	draggable={draggable && !confirmEdit}
>
	{#if confirmEdit}
		<div
			id="sidebar-chat-item"
			class=" w-full flex justify-between rounded-xl px-[11px] py-[6px] {id === $chatId ||
			confirmEdit
				? 'bg-gray-100 dark:bg-gray-900 selected'
				: selected
					? 'bg-gray-100 dark:bg-gray-950 selected'
					: 'group-hover:bg-gray-100 dark:group-hover:bg-gray-950'}  whitespace-nowrap text-ellipsis relative"
		>
			<input
				id="chat-title-input-{id}"
				bind:value={chatTitle}
				class=" bg-transparent w-full outline-hidden mr-10"
				placeholder=""
				disabled={false}
				on:keydown={chatTitleInputKeydownHandler}
				on:blur={async (e) => {
					// check if target is generate button
					if (ignoreBlur) {
						ignoreBlur = false;

						if (e.relatedTarget?.id === 'generate-title-button') {
							generateTitleHandler();
						}
						return;
					}

					if (doubleClicked) {
						e.preventDefault();
						e.stopPropagation();

						await tick();
						setTimeout(() => {
							const input = document.getElementById(`chat-title-input-${id}`);
							if (input) input.focus();
						}, 0);

						doubleClicked = false;
						return;
					}

					if (chatTitle !== title) {
						editChatTitle(id, chatTitle);
					}

					confirmEdit = false;
					chatTitle = '';
				}}
			/>
		</div>
	{:else}
		<div class="flex items-center w-full relative">
			<a
				id="sidebar-chat-item"
				class="flex-1 flex rounded-xl px-[11px] py-2 min-h-[48px] {id === $chatId ||
				confirmEdit
					? 'bg-gray-100 dark:bg-gray-900 selected'
					: selected
						? 'bg-gray-100 dark:bg-gray-950 selected'
						: ' group-hover:bg-gray-100 dark:group-hover:bg-gray-950'}"
				href="/c/{id}"
				on:click={() => {
					dispatch('select');

					if ($selectedFolder) {
						selectedFolder.set(null);
					}

					if ($mobile) {
						showSidebar.set(false);
					}
				}}
				on:dblclick={async (e) => {
					e.preventDefault();
					e.stopPropagation();

					doubleClicked = true;
					renameHandler();
				}}
				on:focus={(e) => {}}
				draggable="false"
			>
				<div class=" flex flex-1 items-center gap-2 pr-10">
					<!-- Chat Title Display -->
					<div dir="auto" class="text-left overflow-hidden w-full line-clamp-2 text-sm">
						{title}
					</div>
				</div>
			</a>

			<!-- More Options Menu Button (Always Visible) -->
			<div class="absolute right-2 z-20">
				<ChatMenu
					{id}
					shareHandler={() => {
						showShareChatModal = true;
					}}
					cloneChatHandler={cloneChatHandler}
					{renameHandler}
					deleteHandler={() => {
						showDeleteConfirm = true;
					}}
					archiveChatHandler={archiveChatHandler}
					moveChatHandler={moveChatHandler}
					onClose={() => {}}
					chatId={id}
					on:change
				>
					<button
						class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition"
						type="button"
						title={$i18n.t('More options')}
					>
						<!-- Three Dots Icon -->
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
						</svg>
					</button>
				</ChatMenu>
			</div>
		</div>
	{/if}

	</div>
