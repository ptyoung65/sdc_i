<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fly, fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();

	let selectedReason = '';
	let detailFeedback = '';

	const feedbackReasons = [
		{ value: 'low_relevance', label: '질문과 답변의 관련성이 낮음' },
		{ value: 'incorrect', label: '사실과 다르거나 오류가 있음' },
		{ value: 'ignored_instructions', label: '지시한 조건이나 형식을 무시함' },
		{ value: 'not_helpful', label: '도움이 되지 않음' }
	];

	const handleSubmit = () => {
		if (!selectedReason) {
			alert('불만족 유형을 선택해주세요.');
			return;
		}

		dispatch('submit', {
			reason: selectedReason,
			detail: detailFeedback
		});

		// 제출 후 상태 초기화
		resetForm();
	};

	const handleClose = () => {
		resetForm();
		dispatch('close');
	};

	const resetForm = () => {
		selectedReason = '';
		detailFeedback = '';
	};
</script>

<!-- 모달 배경 -->
<div
	class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
	on:click={handleClose}
	transition:fade={{ duration: 200 }}
>
	<!-- 모달 컨텐츠 -->
	<div
		class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden"
		on:click|stopPropagation
		transition:fly={{ y: 50, duration: 300 }}
	>
		<!-- 헤더 -->
		<div class="p-6 border-b border-gray-200 dark:border-gray-700">
			<h2 class="text-lg font-bold text-gray-900 dark:text-gray-100">
				어떤 점이 마음에 들지 않으셨나요?
			</h2>
		</div>

		<!-- 본문 -->
		<div class="p-6 space-y-6">
			<!-- 불만족 유형 선택 -->
			<div class="space-y-3">
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
					불만족 유형 선택
				</label>

				{#each feedbackReasons as reason}
					<label class="flex items-start gap-3 p-3 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors">
						<input
							type="radio"
							name="feedback-reason"
							value={reason.value}
							bind:group={selectedReason}
							class="mt-0.5 w-4 h-4 text-blue-600 focus:ring-blue-500"
						/>
						<span class="text-sm text-gray-700 dark:text-gray-300">
							{reason.label}
						</span>
					</label>
				{/each}
			</div>

			<!-- 기타 의견 입력 -->
			<div class="space-y-2">
				<label for="detail-feedback" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
					기타 의견 입력
				</label>
				<p class="text-xs text-gray-500 dark:text-gray-400">
					선택한 불만족 유형에 대한 상세한 설명을 작성해주세요
				</p>
				<textarea
					id="detail-feedback"
					bind:value={detailFeedback}
					rows="4"
					placeholder="상세한 피드백을 입력해주세요..."
					class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
				></textarea>
			</div>
		</div>

		<!-- 푸터 -->
		<div class="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
			<button
				on:click={handleClose}
				class="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-900 dark:text-gray-100 font-medium rounded-lg transition-colors"
			>
				취소
			</button>
			<button
				on:click={handleSubmit}
				class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
			>
				제출
			</button>
		</div>
	</div>
</div>
