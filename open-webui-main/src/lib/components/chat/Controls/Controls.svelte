<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import { user, settings, modelType } from '$lib/stores';
	export let models = [];
	export let chatFiles = [];
	export let params = {};

	export let categories = [];
	export let selectedCategories = [];

	let showValves = false;
</script>

<style>
	/* 카테고리 체크박스 커스텀 스타일 */
	input[type="checkbox"] {
		-webkit-appearance: none;
		-moz-appearance: none;
		appearance: none;
		width: 1rem;
		height: 1rem;
		border: 2px solid #d1d5db;
		border-radius: 0.25rem;
		background-color: white;
		cursor: pointer;
		position: relative;
		transition: all 0.2s;
	}

	:global(.dark) input[type="checkbox"] {
		background-color: #374151;
		border-color: #4b5563;
	}

	input[type="checkbox"]:checked {
		background-color: #3b82f6;
		border-color: #3b82f6;
	}

	input[type="checkbox"]:checked::after {
		content: '';
		position: absolute;
		left: 0.25rem;
		top: 0.05rem;
		width: 0.35rem;
		height: 0.6rem;
		border: solid white;
		border-width: 0 2px 2px 0;
		transform: rotate(45deg);
	}

	input[type="checkbox"]:hover {
		border-color: #3b82f6;
	}
</style>

<div class=" dark:text-white">
	<div class=" flex items-center justify-between dark:text-gray-100 mb-2">
		<div class="flex items-center gap-2">
			<div class=" text-lg font-medium self-center font-primary">카테고리 선택</div>
		</div>
		<!-- 닫기 버튼 -->
		<Tooltip content={$modelType === 'internal' ? "카테고리 닫기" : "외부 모델 사용 중에는 카테고리 선택이 불가능합니다"}>
			<button
				class="cursor-pointer flex rounded-lg transition p-1 {$modelType === 'internal' ? 'hover:bg-gray-100 dark:hover:bg-gray-850' : 'opacity-50 cursor-not-allowed'}"
				on:click={() => {
					if ($modelType === 'internal') {
						dispatch('close');
					}
				}}
				disabled={$modelType !== 'internal'}
				aria-label="Close Controls"
			>
				<div class="self-center p-0.5">
					<!-- 햄버거 아이콘 -->
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="size-5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
						/>
					</svg>
				</div>
			</button>
		</Tooltip>
	</div>

	{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
		<div class=" dark:text-gray-200 text-sm font-primary py-0.5 px-0.5">
			<!-- Files, Valves, System Prompt, Advanced Params 숨김 -->
			{#if false && chatFiles.length > 0}
				<Collapsible title={$i18n.t('Files')} open={true} buttonClassName="w-full">
					<div class="flex flex-col gap-1 mt-1.5" slot="content">
						{#each chatFiles as file, fileIdx}
							<FileItem
								className="w-full"
								item={file}
								edit={true}
								url={file?.url ? file.url : null}
								name={file.name}
								type={file.type}
								size={file?.size}
								dismissible={true}
								small={true}
								on:dismiss={() => {
									// Remove the file from the chatFiles array

									chatFiles.splice(fileIdx, 1);
									chatFiles = chatFiles;
								}}
								on:click={() => {
									console.log(file);
								}}
							/>
						{/each}
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if false && ($user?.role === 'admin' || ($user?.permissions.chat?.valves ?? true))}
				<Collapsible bind:open={showValves} title={$i18n.t('Valves')} buttonClassName="w-full">
					<div class="text-sm" slot="content">
						<Valves show={showValves} />
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if false && ($user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true))}
				<Collapsible title={$i18n.t('System Prompt')} open={true} buttonClassName="w-full">
					<div class="" slot="content">
						<textarea
							bind:value={params.system}
							class="w-full text-xs outline-hidden resize-vertical {$settings.highContrastMode
								? 'border-2 border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5'
								: 'py-1.5 bg-transparent'}"
							rows="4"
							placeholder={$i18n.t('Enter system prompt')}
						/>
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if false && ($user?.role === 'admin' || ($user?.permissions.chat?.params ?? true))}
				<Collapsible title={$i18n.t('Advanced Params')} open={true} buttonClassName="w-full">
					<div class="text-sm mt-1.5" slot="content">
						<div>
							<AdvancedParams admin={$user?.role === 'admin'} custom={true} bind:params />
						</div>
					</div>
				</Collapsible>
			{/if}

			{#if categories.length > 0}
				<div class="space-y-2">
					{#each categories as category}
						<label class="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors border border-gray-200 dark:border-gray-700">
							<input
								type="checkbox"
								checked={selectedCategories.some(c => c.id === category.id)}
								on:change={(e) => {
									if (e.target.checked) {
										selectedCategories = [...selectedCategories, category];
									} else {
										selectedCategories = selectedCategories.filter(c => c.id !== category.id);
									}
								}}
							/>
							<div class="flex-1">
								<div class="text-base font-semibold text-gray-800 dark:text-gray-200">{category.name}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">{category.description}</div>
							</div>
						</label>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>
