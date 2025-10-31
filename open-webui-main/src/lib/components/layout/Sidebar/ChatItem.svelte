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

	let mouseOver = false;
	let draggable = false;
	$: if (mouseOver) {
		loadChat();
	}

	const loadChat = async () => {
		if (!chat) {
			draggable = false;
			chat = await getChatById(localStorage.token, id);
			draggable = true;
		}
	};

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
		if (chatId && folderId) {
			const res = await updateChatFolderIdById(localStorage.token, chatId, folderId).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
				await pinnedChats.set(await getPinnedChatList(localStorage.token));

				dispatch('change');

				toast.success($i18n.t('Chat moved successfully'));
			}
		} else {
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
	title={$i18n.t('Delete chat?')}
	on:confirm={() => {
		deleteChatHandler(id);
	}}
>
	<div class=" text-sm text-gray-500 flex-1 line-clamp-3">
		{$i18n.t('This will delete')} <span class="  font-semibold">{title}</span>.
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
		<a
			id="sidebar-chat-item"
			class=" w-full flex rounded-xl px-[11px] py-2 min-h-[48px] {id === $chatId ||
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
			on:mouseenter={(e) => {
				mouseOver = true;
			}}
			on:mouseleave={(e) => {
				mouseOver = false;
			}}
			on:focus={(e) => {}}
			draggable="false"
		>
			<div class=" flex flex-col self-start flex-1 w-full gap-1">
				<!-- Title -->
				<div dir="auto" class="text-left self-center overflow-hidden w-full truncate font-medium">
					{title}
				</div>

				<!-- Chat content preview -->
				{#if chat?.chat?.messages && chat.chat.messages.length > 0}
					{@const firstUserMessage = chat.chat.messages.find(m => m.role === 'user')}
					{#if firstUserMessage?.content}
						<div dir="auto" class="text-left text-xs text-gray-500 dark:text-gray-400 overflow-hidden w-full truncate">
							{firstUserMessage.content}
						</div>
					{/if}
				{/if}

				<!-- Tags/Categories -->
				{#if chat?.meta?.tags && chat.meta.tags.length > 0}
					<div class="flex flex-wrap gap-1 mt-0.5">
						{#each chat.meta.tags as tag}
							<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
								{tag}
							</span>
						{/each}
					</div>
				{/if}
			</div>
		</a>

		<!-- Edit and Delete Buttons (Outside <a> tag) -->
		<div class="absolute right-2 top-2 flex items-center gap-1 z-10">
			<button
				class="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition"
				on:click={(e) => {
					e.preventDefault();
					e.stopPropagation();
					renameHandler();
				}}
				type="button"
				title="Edit"
			>
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
					<path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
				</svg>
			</button>

			<button
				class="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition"
				on:click={(e) => {
					e.preventDefault();
					e.stopPropagation();
					deleteChatHandler(id);
				}}
				type="button"
				title="Delete"
			>
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
					<path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
				</svg>
			</button>
		</div>
	{/if}

	</div>
