<script lang="ts">
	import { getContext } from 'svelte';
	import ChatItem from './ChatItem.svelte';
	import Folder from '../../common/Folder.svelte';

	const i18n = getContext('i18n');

	export let chats = [];
	export let shiftKey = false;
	export let selectedChatId = null;
	export let categoryType: 'time' | 'tag' | 'none' = 'time';

	// 이벤트 디스패쳐
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	// 챗을 카테고리별로 그룹화
	$: groupedChats = groupChatsByCategory(chats, categoryType);

	function groupChatsByCategory(chatList: any[], type: string) {
		if (!chatList || chatList.length === 0) return {};

		const grouped: Record<string, any[]> = {};

		switch (type) {
			case 'tag':
				// 태그별 그룹화
				chatList.forEach(chat => {
					if (chat.meta?.tags && chat.meta.tags.length > 0) {
						chat.meta.tags.forEach((tag: string) => {
							if (!grouped[tag]) grouped[tag] = [];
							grouped[tag].push(chat);
						});
					} else {
						if (!grouped['Untagged']) grouped['Untagged'] = [];
						grouped['Untagged'].push(chat);
					}
				});
				break;

			case 'time':
				// 시간별 그룹화 (기존 방식 개선)
				chatList.forEach(chat => {
					const timeRange = chat.time_range || 'Unknown';
					if (!grouped[timeRange]) grouped[timeRange] = [];
					grouped[timeRange].push(chat);
				});
				break;

			default:
				// 그룹화 안함
				grouped['All Chats'] = chatList;
		}

		return grouped;
	}

	// 카테고리 순서 정렬
	$: sortedCategories = Object.keys(groupedChats).sort((a, b) => {
		if (categoryType === 'time') {
			const timeOrder = ['Today', 'Yesterday', 'Previous 7 days', 'Previous 30 days'];
			const indexA = timeOrder.indexOf(a);
			const indexB = timeOrder.indexOf(b);
			if (indexA !== -1 && indexB !== -1) return indexA - indexB;
			if (indexA !== -1) return -1;
			if (indexB !== -1) return 1;
		}
		return a.localeCompare(b);
	});
</script>

<div class="chat-history-section">
	{#if sortedCategories.length === 0}
		<div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
			{$i18n.t('No chats available')}
		</div>
	{:else}
		{#each sortedCategories as category}
			<Folder
				className="mb-2"
				name={$i18n.t(category)}
				chevron={true}
				open={true}
			>
				<div class="flex flex-col space-y-1">
					{#each groupedChats[category] as chat, idx}
						<ChatItem
							className=""
							id={chat.id}
							title={chat.title}
							{shiftKey}
							selected={selectedChatId === chat.id}
							on:select={() => {
								selectedChatId = chat.id;
								dispatch('select', chat.id);
							}}
							on:unselect={() => {
								selectedChatId = null;
								dispatch('unselect');
							}}
							on:change={() => {
								dispatch('change');
							}}
							on:tag={(e) => {
								dispatch('tag', e.detail);
							}}
						/>
					{/each}
				</div>
			</Folder>
		{/each}
	{/if}
</div>

<style>
	.chat-history-section {
		@apply flex flex-col;
	}
</style>
