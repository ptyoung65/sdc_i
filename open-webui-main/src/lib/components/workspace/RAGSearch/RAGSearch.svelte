<script lang="ts">
	import TermSearch from './TermSearch.svelte';
	import ITHelpSearch from './ITHelpSearch.svelte';
	import PolicySearch from './PolicySearch.svelte';
	import EDMSearch from './EDMSearch.svelte';

	let activeTab: 'term' | 'ithelp' | 'policy' | 'edm' = 'term';

	const tabs = [
		{ id: 'term', icon: '📖', label: '용어사전' },
		{ id: 'ithelp', icon: '🛠️', label: 'IT Help Desk' },
		{ id: 'policy', icon: '📋', label: '회사사규' },
		{ id: 'edm', icon: '📄', label: 'EDM 문서' }
	];

	function setActiveTab(tab: typeof activeTab) {
		activeTab = tab;
	}
</script>

<div class="flex flex-col h-full">
	<!-- 탭 헤더 -->
	<div class="mb-6">
		<div class="flex items-center gap-4 flex-wrap">
			{#each tabs as tab}
				<button
					on:click={() => setActiveTab(tab.id as typeof activeTab)}
					class="px-6 py-3 rounded-lg font-medium transition-all {activeTab === tab.id
						? 'bg-blue-600 text-white shadow-lg'
						: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'}"
				>
					<span class="mr-2">{tab.icon}</span>
					{tab.label}
				</button>
			{/each}
		</div>
	</div>

	<!-- 탭 컨텐츠 -->
	<div class="flex-1 overflow-auto">
		{#if activeTab === 'term'}
			<TermSearch />
		{:else if activeTab === 'ithelp'}
			<ITHelpSearch />
		{:else if activeTab === 'policy'}
			<PolicySearch />
		{:else if activeTab === 'edm'}
			<EDMSearch />
		{/if}
	</div>
</div>

<style>
	/* 스크롤바 스타일링 */
	:global(.overflow-y-auto::-webkit-scrollbar) {
		width: 8px;
	}

	:global(.overflow-y-auto::-webkit-scrollbar-track) {
		background: transparent;
	}

	:global(.overflow-y-auto::-webkit-scrollbar-thumb) {
		background: #cbd5e0;
		border-radius: 4px;
	}

	:global(.dark .overflow-y-auto::-webkit-scrollbar-thumb) {
		background: #4a5568;
	}
</style>
