<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import EdmSearchResultsModal from './EdmSearchResultsModal.svelte';
	import EdmFeedbackModal from './EdmFeedbackModal.svelte';

	const dispatch = createEventDispatcher();

	export let showInitialMessage = true;
	export let searchResults = null;
	export let learnedDocsCount = 0;
	export let edmSearchCount = 0;
	export let sources = [];
	export let externalSources = [];

	let showSearchModal = false;
	let showFeedbackModal = false;
	let feedbackType: 'up' | 'down' = 'up';
</script>

{#if showInitialMessage}
	<!-- 초기 안내 메시지 -->
	<div class="w-full max-w-4xl mx-auto py-8 space-y-4">
		<!-- 단순 텍스트 -->
		<div class="text-sm text-gray-600 dark:text-gray-400">
			텍스트, 표, 차트 등 지원
		</div>

		<!-- 안내 카드 -->
		<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
			<p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
				EDM 문서 활용 영역은 이미 학습된 문서를 참고하여 답변을 생성하고 추가로 키워드 기반으로 EDM 문서 검색 결과를 제공합니다.
				아래의 답변이 마음에 들지 않으시면 답변 하단에 문서 검색결과 보기 버튼을 눌러 검색결과를 확인하고 원하는 문서를 첨부 등록할 수 있습니다.
			</p>
		</div>
	</div>
{/if}

{#if searchResults}
	<!-- 답변 영역들 -->
	<div class="w-full max-w-4xl mx-auto space-y-6 py-4">
		<!-- 답변영역 1: 요약 정보 -->
		<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
			<p class="text-sm text-gray-700 dark:text-gray-300">
				현재 질문내용 요약과 관련된 학습 문서는 <span class="font-semibold text-blue-600 dark:text-blue-400">{learnedDocsCount}건</span>,
				EDM 문서 검색 결과는 <span class="font-semibold text-blue-600 dark:text-blue-400">{edmSearchCount}건</span>으로 확인되었습니다.
			</p>
		</div>

		<!-- 답변영역 2: 출처 표시 -->
		<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3">
			<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
				출처 표시
			</div>

			<div class="space-y-2">
				<!-- 소스 -->
				<div>
					<div class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">소스:</div>
					<div class="flex flex-wrap gap-2">
						{#each sources as source}
							<span class="inline-flex items-center px-3 py-1 rounded-full text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
								{source}
							</span>
						{/each}
					</div>
				</div>

				<!-- 외부검색 자료 -->
				<div>
					<div class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">외부검색 자료:</div>
					<div class="flex flex-wrap gap-2">
						{#each externalSources as extSource}
							<span class="inline-flex items-center px-3 py-1 rounded-full text-xs bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">
								{extSource}
							</span>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<!-- 답변영역 3: 문서검색 결과 -->
		<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
			<div class="flex items-center justify-between">
				<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
					문서검색 결과
				</div>
				<div class="flex gap-2">
					<button
						on:click={() => (showSearchModal = true)}
						class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
					>
						EDM 문서 검색 결과 보기
					</button>
				</div>
			</div>
		</div>

		<!-- 피드백 영역 -->
		<div class="flex items-center justify-end gap-2 pt-2">
			<span class="text-xs text-gray-500 dark:text-gray-400 mr-2">이 답변이 도움이 되셨나요?</span>
			<button
				on:click={() => {
					feedbackType = 'up';
					dispatch('feedback', { type: 'up' });
				}}
				class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
				title="좋아요"
			>
				<svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
				</svg>
			</button>
			<button
				on:click={() => {
					feedbackType = 'down';
					showFeedbackModal = true;
				}}
				class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
				title="싫어요"
			>
				<svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
				</svg>
			</button>
		</div>
	</div>
{/if}

<!-- 검색 결과 모달 -->
{#if showSearchModal}
	<EdmSearchResultsModal
		results={searchResults}
		on:close={() => (showSearchModal = false)}
		on:selectDocument={(e) => dispatch('selectDocument', e.detail)}
	/>
{/if}

<!-- 피드백 모달 -->
{#if showFeedbackModal}
	<EdmFeedbackModal
		on:close={() => (showFeedbackModal = false)}
		on:submit={(e) => {
			dispatch('feedback', { type: 'down', details: e.detail });
			showFeedbackModal = false;
		}}
	/>
{/if}
