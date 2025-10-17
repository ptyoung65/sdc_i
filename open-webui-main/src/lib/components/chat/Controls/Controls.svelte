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

<div class=" dark:text-white">
	<div class=" flex items-center justify-between dark:text-gray-100 mb-2">
		<div class="flex items-center gap-2">
			<Tooltip content="카테고리 닫기">
				<button
					class="flex rounded-lg transition p-1 {$modelType === 'external'
						? 'cursor-not-allowed opacity-30'
						: 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-850'}"
					on:click={() => {
						if ($modelType === 'internal') {
							dispatch('close');
						}
					}}
					disabled={$modelType === 'external'}
					aria-label="Close Category Sidebar"
				>
					<!-- 햄버거 메뉴 아이콘 -->
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
				</button>
			</Tooltip>
			<div class=" text-lg font-medium self-center font-primary">카테고리 선택</div>
		</div>
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
							<div class="relative flex items-center justify-center">
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
									class="peer w-6 h-6 rounded border-2 border-gray-400 dark:border-gray-500 appearance-none cursor-pointer transition-all
										checked:bg-gray-900 checked:dark:bg-white checked:border-gray-900 checked:dark:border-white
										focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
								/>
								<svg
									class="absolute w-4 h-4 text-white dark:text-gray-900 pointer-events-none hidden peer-checked:block"
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="4"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<polyline points="20 6 9 17 4 12"></polyline>
								</svg>
							</div>
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
