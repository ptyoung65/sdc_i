<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';

	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
	import { blur, fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();

	import { getChatList } from '$lib/apis/chats';
	import { updateFolderById } from '$lib/apis/folders';

	import {
		config,
		user,
		models as _models,
		temporaryChatEnabled,
		selectedFolder,
		chats,
		currentChatPage
	} from '$lib/stores';
	import { sanitizeResponseContent, extractCurlyBraceWords } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import MessageInput from './MessageInput.svelte';
	import FolderPlaceholder from './Placeholder/FolderPlaceholder.svelte';
	import FolderTitle from './Placeholder/FolderTitle.svelte';

	const i18n = getContext('i18n');

	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];
	export let messageInput = null;

	export let selectedToolIds = [];
	export let selectedFilterIds = [];

	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;

	export let showCommands = false;

	export let toolServers = [];

	export let onSelect: Function;
	export let onChange: Function;

	let models = [];
	let selectedModelIdx = 0;

	$: models = (atSelectedModel
		? [atSelectedModel]
		: selectedModels.map((id) => $_models.find((m) => m.id === id))
	).filter((m) => m);
</script>

<div class="m-auto w-full h-full max-w-6xl px-2 @2xl:px-20 flex flex-col justify-end">
	<!-- 인사말과 아이콘 모두 제거 -->

	<!-- MessageInput을 화면 완전 하단에 고정 -->
	<div class="w-full pb-4">
		<div class="text-base font-normal @md:max-w-3xl w-full mx-auto">
			<MessageInput
				bind:this={messageInput}
				{history}
				{selectedModels}
				bind:files
				bind:prompt
				bind:autoScroll
				bind:selectedToolIds
				bind:selectedFilterIds
				bind:imageGenerationEnabled
				bind:codeInterpreterEnabled
				bind:webSearchEnabled
				bind:atSelectedModel
				bind:showCommands
				{toolServers}
				{stopResponse}
				{createMessagePair}
				placeholder={$i18n.t('How can I help you today?')}
				{onChange}
				on:upload={(e) => {
					dispatch('upload', e.detail);
				}}
				on:submit={(e) => {
					dispatch('submit', e.detail);
				}}
			/>
		</div>
	</div>
</div>
