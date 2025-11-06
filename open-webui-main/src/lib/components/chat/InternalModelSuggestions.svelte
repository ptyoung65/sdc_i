<script lang="ts">
	import { getContext } from 'svelte';
	import { fade } from 'svelte/transition';

	const i18n = getContext('i18n');

	export let onSelect = (e) => {};

	const suggestionCategories = [
		{
			title: '회사생활가이드',
			icon: '📋',
			suggestions: [
				'육아휴직 신청 방법 알려 줘.',
				'연간 패밀리넷 사용 가능 금액 알려 줘'
			]
		},
		{
			title: 'IT Help Desk',
			icon: '💻',
			suggestions: [
				'Knox 비밀번호 초기화 방법 알려 줘.',
				'Wave 운영팀 내선 번호 알려 줘.'
			]
		},
		{
			title: '지식용어 사전',
			icon: '📚',
			suggestions: [
				'우리회사 PCCB 절차는 어떻게 돼',
				'Rfzen, Rpsc와 관련된 WSD는 어떤 뜻이야'
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
							       hover:bg-blue-50 dark:hover:bg-blue-900/30
							       border border-gray-200 dark:border-gray-600
							       hover:border-blue-300 dark:hover:border-blue-700
							       transition-all duration-200 group"
							on:click={() => onSelect({ type: 'prompt', data: suggestion })}
						>
							<div class="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-blue-300 line-clamp-2">
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
