<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { fade, scale } from 'svelte/transition';
	import Modal from '$lib/components/common/Modal.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	const handleConfirm = () => {
		dispatch('confirm');
		show = false;
	};

	const handleCancel = () => {
		dispatch('cancel');
		show = false;
	};
</script>

{#if show}
	<Modal bind:show size="sm">
		<div class="px-4 py-6">
			<!-- 아이콘 -->
			<div class="flex justify-center mb-4">
				<div class="flex items-center justify-center w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30">
					<svg class="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
					</svg>
				</div>
			</div>

			<!-- 제목 -->
			<h3 class="text-center text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
				외부모델로 전환
			</h3>

			<!-- 메시지 -->
			<div class="space-y-2 text-sm text-gray-600 dark:text-gray-400 text-center mb-6">
				<p class="font-medium text-amber-700 dark:text-amber-400">
					외부 검색 전용 공간입니다.
				</p>
				<p>내부 데이터와 분리됩니다.</p>
				<p>내부모델의 챗팅내역은 외부모델에서 사용할 수 없습니다.</p>
			</div>

			<!-- 버튼 -->
			<div class="flex gap-3 justify-center">
				<button
					class="px-6 py-2 rounded-lg text-sm font-medium
					       bg-gray-100 dark:bg-gray-700
					       text-gray-700 dark:text-gray-300
					       hover:bg-gray-200 dark:hover:bg-gray-600
					       transition-colors duration-200"
					on:click={handleCancel}
				>
					취소
				</button>
				<button
					class="px-6 py-2 rounded-lg text-sm font-medium
					       bg-blue-600 hover:bg-blue-700
					       text-white
					       transition-colors duration-200"
					on:click={handleConfirm}
				>
					동의 후 이동
				</button>
			</div>
		</div>
	</Modal>
{/if}
