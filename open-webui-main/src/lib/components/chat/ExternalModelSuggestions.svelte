<script lang="ts">
	import { getContext } from 'svelte';
	import { fade } from 'svelte/transition';

	const i18n = getContext('i18n');

	export let onSelect = (e) => {};

	const suggestionCategories = [
		{
			title: '정보 검색',
			icon: '🔍',
			suggestions: [
				'삼성디스플레이 관련 뉴스 보여줘',
				'AI 기반 업무 혁신 사례 찾아줘'
			]
		}
	];
</script>

<div class="w-full" in:fade={{ duration: 300 }}>
	<!-- 헤더 -->
	<div class="mb-4 text-left">
		<h3 class="text-lg font-medium text-gray-700 dark:text-gray-300">
			다음과 같은 질문을 물어볼 수 있어요
		</h3>
	</div>

	<!-- 카테고리 카드들 -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		{#each suggestionCategories as category, categoryIdx}
			<div
				class="waterfall flex flex-col gap-2 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm"
				style="animation-delay: {categoryIdx * 100}ms"
			>
				<!-- 카테고리 제목 -->
				<div class="flex items-center gap-2 mb-2">
					<span class="text-2xl">{category.icon}</span>
					<h4 class="text-sm font-semibold text-gray-800 dark:text-gray-200">
						{category.title}
					</h4>
				</div>

				<!-- 제안 버튼들 -->
				<div class="flex flex-col gap-2">
					{#each category.suggestions as suggestion, idx}
						<button
							class="text-left px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/50
							       hover:bg-emerald-50 dark:hover:bg-emerald-900/30
							       border border-gray-200 dark:border-gray-600
							       hover:border-emerald-300 dark:hover:border-emerald-700
							       transition-all duration-200 group"
							on:click={() => onSelect({ type: 'prompt', data: suggestion })}
						>
							<div class="text-sm text-gray-700 dark:text-gray-300 group-hover:text-emerald-700 dark:group-hover:text-emerald-300 line-clamp-2">
								{suggestion}
							</div>
						</button>
					{/each}
				</div>
			</div>
		{/each}
	</div>
</div>

<style>
	/* Waterfall animation */
	@keyframes fadeInUp {
		0% {
			opacity: 0;
			transform: translateY(20px);
		}
		100% {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.waterfall {
		opacity: 0;
		animation-name: fadeInUp;
		animation-duration: 400ms;
		animation-fill-mode: forwards;
		animation-timing-function: ease-out;
	}
</style>
