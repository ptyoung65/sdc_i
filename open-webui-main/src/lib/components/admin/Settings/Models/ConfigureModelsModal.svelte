<script>
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { models } from '$lib/stores';
	import { deleteAllModels } from '$lib/apis/models';

	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ModelList from './ModelList.svelte';
	import { getModelsConfig, setModelsConfig } from '$lib/apis/configs';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let initHandler = () => {};

	let config = null;

	let selectedModelId = '';
	let defaultModelIds = [];
	let modelIds = [];

	// ============================================
	// [2024.12.30] 턴 및 토큰수 제약처리 - 모달 변수 시작
	// 역할: 모델 설정 모달에서 세션 제한 관리
	// ============================================
	let limitsArray = []; // [{id, name, maxTurns, maxTokens}, ...]
	let showLimitsSection = false;
	// [2024.12.30] 턴 및 토큰수 제약처리 - 모달 변수 완료 ============================================

	let sortKey = '';
	let sortOrder = '';

	let loading = false;
	let showResetModal = false;

	$: if (show) {
		init();
	}

	$: if (selectedModelId) {
		onModelSelect();
	}

	const onModelSelect = () => {
		if (selectedModelId === '') {
			return;
		}

		if (defaultModelIds.includes(selectedModelId)) {
			selectedModelId = '';
			return;
		}

		defaultModelIds = [...defaultModelIds, selectedModelId];
		selectedModelId = '';
	};

	const init = async () => {
		config = await getModelsConfig(localStorage.token);

		if (config?.DEFAULT_MODELS) {
			defaultModelIds = (config?.DEFAULT_MODELS).split(',').filter((id) => id);
		} else {
			defaultModelIds = [];
		}

		const modelOrderList = config.MODEL_ORDER_LIST || [];
		const allModelIds = $models.map((model) => model.id);
		const orderedSet = new Set(modelOrderList);

		modelIds = [
			...modelOrderList.filter((id) => orderedSet.has(id) && allModelIds.includes(id)),
			...allModelIds.filter((id) => !orderedSet.has(id)).sort((a, b) => a.localeCompare(b))
		];

		// ============================================
		// [2024.12.30] 턴 및 토큰수 제약처리 - 설정 로드 시작
		// ============================================
		const loadedLimits = config?.MODEL_SESSION_LIMITS || config?.model_session_limits || {};
		limitsArray = modelIds.map(id => ({
			id,
			name: $models.find(m => m.id === id)?.name || id,
			maxTurns: loadedLimits[id]?.maxTurns || 0,
			maxTokens: loadedLimits[id]?.maxTokens || 0,
			// ----- [2026-03-05] maxInputTokens, warningTurns 로드 누락 수정 시작 -----
			maxInputTokens: loadedLimits[id]?.maxInputTokens || 0,
			warningTurns: loadedLimits[id]?.warningTurns || 0
			// ----- [2026-03-05] maxInputTokens, warningTurns 로드 누락 수정 종료 -----
		}));
		// [2024.12.30] 턴 및 토큰수 제약처리 - 설정 로드 완료 ============================================

		sortKey = '';
		sortOrder = '';
	};

	const submitHandler = async () => {
		loading = true;

		// ============================================
		// [2024.12.30] 턴 및 토큰수 제약처리 - 설정 저장 시작
		// ============================================
		const limitsToSave = {};
		for (const item of limitsArray) {
			// ----- [2026-03-05] maxInputTokens, warningTurns 저장 누락 수정 시작 -----
			if (item.maxTurns > 0 || item.maxTokens > 0 || item.maxInputTokens > 0 || item.warningTurns > 0) {
				limitsToSave[item.id] = {
					maxTurns: item.maxTurns,
					maxTokens: item.maxTokens,
					maxInputTokens: item.maxInputTokens,
					warningTurns: item.warningTurns
				};
			}
			// ----- [2026-03-05] maxInputTokens, warningTurns 저장 누락 수정 종료 -----
		}
		// [2024.12.30] 턴 및 토큰수 제약처리 - 설정 저장 완료 ============================================

		// ----- [2026-03-05] 기존 config 보존하여 저장 (다른 설정 덮어쓰기 방지) 시작 -----
		const res = await setModelsConfig(localStorage.token, {
			...config,
			DEFAULT_MODELS: defaultModelIds.join(','),
			MODEL_ORDER_LIST: modelIds,
			MODEL_SESSION_LIMITS: limitsToSave
		});
		// ----- [2026-03-05] 기존 config 보존하여 저장 종료 -----

		if (res) {
			toast.success($i18n.t('Models configuration saved successfully'));
			initHandler();
			show = false;
		} else {
			toast.error($i18n.t('Failed to save models configuration'));
		}

		loading = false;
	};

	onMount(async () => {
		init();
	});
</script>

<ConfirmDialog
	title={$i18n.t('Reset All Models')}
	message={$i18n.t('This will delete all models including custom models and cannot be undone.')}
	bind:show={showResetModal}
	onConfirm={async () => {
		const res = deleteAllModels(localStorage.token);
		if (res) {
			toast.success($i18n.t('All models deleted successfully'));
			initHandler();
		}
	}}
/>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center font-primary">
				{$i18n.t('Settings')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				{#if config}
					<form
						class="flex flex-col w-full"
						on:submit|preventDefault={() => {
							submitHandler();
						}}
					>
						<div>
							<div class="flex flex-col w-full">
								<button
									class="mb-1 flex gap-2"
									type="button"
									on:click={() => {
										sortKey = 'model';

										if (sortOrder === 'asc') {
											sortOrder = 'desc';
										} else {
											sortOrder = 'asc';
										}

										modelIds = modelIds
											.filter((id) => id !== '')
											.sort((a, b) => {
												const nameA = $models.find((model) => model.id === a)?.name || a;
												const nameB = $models.find((model) => model.id === b)?.name || b;
												return sortOrder === 'desc'
													? nameA.localeCompare(nameB)
													: nameB.localeCompare(nameA);
											});
									}}
								>
									<div class="text-xs text-gray-500">{$i18n.t('Reorder Models')}</div>

									{#if sortKey === 'model'}
										<span class="font-normal self-center">
											{#if sortOrder === 'asc'}
												<ChevronUp className="size-3" />
											{:else}
												<ChevronDown className="size-3" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-3" />
										</span>
									{/if}
								</button>

								<ModelList bind:modelIds />
							</div>
						</div>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<div>
							<div class="flex flex-col w-full">
								<div class="mb-1 flex justify-between">
									<div class="text-xs text-gray-500">{$i18n.t('Default Models')}</div>
								</div>

								<div class="flex items-center -mr-1">
									<select
										class="w-full py-1 text-sm rounded-lg bg-transparent {selectedModelId
											? ''
											: 'text-gray-500'} placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
										bind:value={selectedModelId}
									>
										<option value="">{$i18n.t('Select a model')}</option>
										{#each $models as model}
											<option value={model.id} class="bg-gray-50 dark:bg-gray-700"
												>{model.name}</option
											>
										{/each}
									</select>
								</div>

								<!-- <hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" /> -->

								{#if defaultModelIds.length > 0}
									<div class="flex flex-col">
										{#each defaultModelIds as modelId, modelIdx}
											<div class=" flex gap-2 w-full justify-between items-center">
												<div class=" text-sm flex-1 py-1 rounded-lg">
													{$models.find((model) => model.id === modelId)?.name}
												</div>
												<div class="shrink-0">
													<button
														type="button"
														on:click={() => {
															defaultModelIds = defaultModelIds.filter(
																(_, idx) => idx !== modelIdx
															);
														}}
													>
														<Minus strokeWidth="2" className="size-3.5" />
													</button>
												</div>
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-gray-500 text-xs text-center py-2">
										{$i18n.t('No models selected')}
									</div>
								{/if}
							</div>
						</div>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<!-- ============================================ -->
						<!-- [2024.12.30] 턴 및 토큰수 제약처리 - 모달 UI 시작 -->
						<!-- 역할: 모델 설정 모달에서 세션 제한 입력 UI -->
						<!-- ============================================ -->
						<!-- 세션 제한 설정 섹션 -->
						<div>
							<div class="flex flex-col w-full">
								<button
									class="mb-2 flex gap-2 items-center"
									type="button"
									on:click={() => {
										showLimitsSection = !showLimitsSection;
									}}
								>
									<div class="text-xs text-gray-500">{$i18n.t('Session Limits')}</div>
									<span class="font-normal self-center">
										{#if showLimitsSection}
											<ChevronUp className="size-3" />
										{:else}
											<ChevronDown className="size-3" />
										{/if}
									</span>
								</button>

								{#if showLimitsSection && limitsArray.length > 0}
									<div class="max-h-48 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg p-2">
										<table class="w-full text-xs">
											<thead>
												<tr class="text-gray-500">
													<th class="text-left py-1">모델</th>
													<th class="text-center py-1 w-20">Max Turns</th>
													<th class="text-center py-1 w-24">Max Tokens</th>
												</tr>
											</thead>
											<tbody>
												{#each limitsArray as item, i (item.id)}
													<tr class="border-t border-gray-100 dark:border-gray-700">
														<td class="py-1 truncate" title={item.name}>{item.name}</td>
														<td class="py-1 text-center">
															<input type="number" min="0" max="100"
																class="w-14 px-1 py-0.5 text-center border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
																bind:value={limitsArray[i].maxTurns}
															/>
														</td>
														<td class="py-1 text-center">
															<input type="number" min="0" step="100"
																class="w-20 px-1 py-0.5 text-center border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
																bind:value={limitsArray[i].maxTokens}
															/>
														</td>
													</tr>
												{/each}
											</tbody>
										</table>
									</div>
									<div class="text-xs text-gray-400 mt-1">* 0 = 무제한</div>
								{/if}
							</div>
						</div>
						<!-- [2024.12.30] 턴 및 토큰수 제약처리 - 모달 UI 완료 ============================================ -->

						<div class="flex justify-between pt-3 text-sm font-medium gap-1.5">
							<Tooltip content={$i18n.t('This will delete all models including custom models')}>
								<button
									class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-950 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
									type="button"
									on:click={() => {
										showResetModal = true;
									}}
								>
									<!-- {$i18n.t('Delete All Models')} -->
									{$i18n.t('Reset All Models')}
								</button>
							</Tooltip>

							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
									? ' cursor-not-allowed'
									: ''}"
								type="submit"
								disabled={loading}
							>
								{$i18n.t('Save')}

								{#if loading}
									<div class="ml-2 self-center">
										<Spinner />
									</div>
								{/if}
							</button>
						</div>
					</form>
				{:else}
					<div>
						<Spinner className="size-5" />
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
