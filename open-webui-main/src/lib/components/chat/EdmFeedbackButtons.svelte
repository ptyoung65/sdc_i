<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	export let messageId: string;
	export let fileCount: number = 0;
	export let feedback: any = null; // 평가 정보

	// 버튼 클릭 핸들러 함수로 정의
	const handleFileListClick = () => {
		console.log('🔵 [EdmFeedbackButtons] EDM 검색 결과 보기 버튼 클릭');
		dispatch('openFileList');
	};

	const handleThumbsUpClick = () => {
		console.log('🔵 [EdmFeedbackButtons] 👍 버튼 클릭');
		dispatch('feedback', { messageId, type: 'thumbs-up' });
	};

	const handleThumbsDownClick = () => {
		console.log('🔵 [EdmFeedbackButtons] 👎 버튼 클릭');
		dispatch('feedback', { messageId, type: 'thumbs-down' });
	};

	// Class 계산 함수
	$: thumbsUpClass = feedback?.type === 'thumbs-up'
		? 'p-2 transition-colors rounded-lg relative z-20 text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30'
		: 'p-2 transition-colors rounded-lg relative z-20 text-gray-600 hover:text-green-600 dark:text-gray-400 dark:hover:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20';

	$: thumbsDownClass = feedback?.type === 'thumbs-down'
		? 'p-2 transition-colors rounded-lg relative z-20 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30'
		: 'p-2 transition-colors rounded-lg relative z-20 text-gray-600 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20';

	let fileListButtonEl: HTMLButtonElement;
	let thumbsUpButtonEl: HTMLButtonElement;
	let thumbsDownButtonEl: HTMLButtonElement;

	onMount(() => {
		console.log('🟢 [EdmFeedbackButtons] 컴포넌트 마운트:', { messageId, fileCount, feedback });
		console.log('🟢 [EdmFeedbackButtons] 버튼 요소:', {
			fileListButton: fileListButtonEl,
			thumbsUpButton: thumbsUpButtonEl,
			thumbsDownButton: thumbsDownButtonEl
		});

		// 직접 DOM 이벤트 리스너 추가 (디버깅용)
		if (thumbsDownButtonEl) {
			console.log('🟢 [EdmFeedbackButtons] 👎 버튼에 직접 addEventListener 추가');
			thumbsDownButtonEl.addEventListener('click', () => {
				console.log('🔵 [EdmFeedbackButtons] 👎 버튼 직접 리스너 실행!');
			});
		}
	});
</script>

<div
	class="flex items-center justify-between mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 relative z-10"
	style="pointer-events: auto;"
>
	<!-- EDM 검색 결과 보기 버튼 -->
	<button
		bind:this={fileListButtonEl}
		data-testid="edm-file-list-button"
		on:click={handleFileListClick}
		class="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg text-sm font-medium transition-colors shadow-sm hover:shadow-md relative z-20"
		style="pointer-events: auto;"
		type="button"
	>
		📂 문서 검색결과 보기 ({fileCount}건)
	</button>

	<!-- 피드백 버튼 영역 -->
	<div class="flex items-center space-x-4">
		<span class="text-sm text-gray-600 dark:text-gray-400">이 답변이 도움이 되셨나요?</span>

		<!-- 👍 Thumbs Up 버튼 -->
		<button
			data-testid="edm-thumbs-up-button"
			on:click={handleThumbsUpClick}
			class={thumbsUpClass}
			style="pointer-events: auto;"
			title="도움이 됨"
			type="button"
			aria-label="도움이 됨"
		>
			<svg
				class="w-5 h-5"
				fill="currentColor"
				viewBox="0 0 20 20"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z"
				/>
			</svg>
		</button>

			<!-- 👎 Thumbs Down 버튼 -->
		<button
			bind:this={thumbsDownButtonEl}
			data-testid="edm-thumbs-down-button"
			on:click={handleThumbsDownClick}
			class={thumbsDownClass}
			style="pointer-events: auto;"
			title="도움이 안됨"
			type="button"
			aria-label="도움이 안됨"
		>
			<svg
				class="w-5 h-5"
				fill="currentColor"
				viewBox="0 0 20 20"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.105-1.79l-.05-.025A4 4 0 0011.055 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z"
				/>
			</svg>
		</button>
	</div>
</div>
