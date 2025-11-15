<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { getCodeExecutionConfig, setCodeExecutionConfig, getJupyterPresets } from '$lib/apis/configs';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let config = null;

	let engines = ['pyodide', 'jupyter'];
	let jupyterPresets = getJupyterPresets();
	let showExecutionPresets = false;
	let showInterpreterPresets = false;

	const submitHandler = async () => {
		const res = await setCodeExecutionConfig(localStorage.token, config);
	};

	const applyJupyterPreset = (preset: any, isInterpreter: boolean = false) => {
		if (isInterpreter) {
			config.CODE_INTERPRETER_ENGINE = 'jupyter';
			config.CODE_INTERPRETER_JUPYTER_URL = preset.url;
			config.CODE_INTERPRETER_JUPYTER_AUTH = preset.auth;
			config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN = preset.token;
			config.CODE_INTERPRETER_JUPYTER_TIMEOUT = preset.timeout;
			showInterpreterPresets = false;
		} else {
			config.CODE_EXECUTION_ENGINE = 'jupyter';
			config.CODE_EXECUTION_JUPYTER_URL = preset.url;
			config.CODE_EXECUTION_JUPYTER_AUTH = preset.auth;
			config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN = preset.token;
			config.CODE_EXECUTION_JUPYTER_TIMEOUT = preset.timeout;
			showExecutionPresets = false;
		}
		toast.success(`${preset.name} 설정이 적용되었습니다`);
	};

	onMount(async () => {
		const res = await getCodeExecutionConfig(localStorage.token);

		if (res) {
			config = res;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		await submitHandler();
		saveHandler();
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		{#if config}
			<div>
				<div class="mb-3.5">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="mb-2.5">
						<div class=" flex w-full justify-between">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('Enable Code Execution')}
							</div>

							<Switch bind:state={config.ENABLE_CODE_EXECUTION} />
						</div>
					</div>

					<div class="mb-2.5">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('Code Execution Engine')}</div>
							<div class="flex items-center relative">
								<select
									class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
									bind:value={config.CODE_EXECUTION_ENGINE}
									placeholder={$i18n.t('Select a engine')}
									required
								>
									<option disabled selected value="">{$i18n.t('Select a engine')}</option>
									{#each engines as engine}
										<option value={engine}>{engine}</option>
									{/each}
								</select>
							</div>
						</div>

						{#if config.CODE_EXECUTION_ENGINE === 'jupyter'}
							<div class="text-gray-500 text-xs">
								{$i18n.t(
									'Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.'
								)}
							</div>
						{/if}
					</div>

					{#if config.CODE_EXECUTION_ENGINE === 'jupyter'}
						<div class="mb-2.5 flex flex-col gap-1.5 w-full">
							<div class="flex justify-between items-center">
								<div class="text-xs font-medium">
									{$i18n.t('Jupyter URL')}
								</div>
								<button
									type="button"
									class="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition"
									on:click={() => showExecutionPresets = !showExecutionPresets}
								>
									🔧 프리셋 선택
								</button>
							</div>

							{#if showExecutionPresets}
								<div class="flex flex-col gap-1 p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-800">
									{#each jupyterPresets as preset}
										<button
											type="button"
											class="text-left text-xs px-3 py-2 {preset.recommended ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'} hover:bg-blue-100 dark:hover:bg-blue-800/40 rounded border transition"
											on:click={() => applyJupyterPreset(preset, false)}
										>
											<div class="font-medium {preset.recommended ? 'text-blue-700 dark:text-blue-300' : ''}">{preset.name}</div>
											<div class="text-gray-500 text-[10px] mt-0.5">{preset.url}</div>
											{#if preset.description}
												<div class="{preset.recommended ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'} text-[9px] mt-0.5 italic">{preset.description}</div>
											{/if}
										</button>
									{/each}
								</div>
							{/if}

							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full text-sm py-0.5 placeholder:text-gray-300 dark:placeholder:text-gray-700 bg-transparent outline-hidden"
										type="text"
										placeholder={$i18n.t('Enter Jupyter URL')}
										bind:value={config.CODE_EXECUTION_JUPYTER_URL}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>

						<div class="mb-2.5 flex flex-col gap-1.5 w-full">
							<div class=" flex gap-2 w-full items-center justify-between">
								<div class="text-xs font-medium">
									{$i18n.t('Jupyter Auth')}
								</div>

								<div>
									<select
										class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-left"
										bind:value={config.CODE_EXECUTION_JUPYTER_AUTH}
										placeholder={$i18n.t('Select an auth method')}
									>
										<option selected value="">{$i18n.t('None')}</option>
										<option value="token">{$i18n.t('Token')}</option>
										<option value="password">{$i18n.t('Password')}</option>
									</select>
								</div>
							</div>

							{#if config.CODE_EXECUTION_JUPYTER_AUTH}
								<div class="flex w-full gap-2">
									<div class="flex-1">
										{#if config.CODE_EXECUTION_JUPYTER_AUTH === 'password'}
											<SensitiveInput
												type="text"
												placeholder={$i18n.t('Enter Jupyter Password')}
												bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD}
												autocomplete="off"
											/>
										{:else}
											<SensitiveInput
												type="text"
												placeholder={$i18n.t('Enter Jupyter Token')}
												bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN}
												autocomplete="off"
											/>
										{/if}
									</div>
								</div>
							{/if}
						</div>

						<div class="flex gap-2 w-full items-center justify-between">
							<div class="text-xs font-medium">
								{$i18n.t('Code Execution Timeout')}
							</div>

							<div class="">
								<Tooltip content={$i18n.t('Enter timeout in seconds')}>
									<input
										class="dark:bg-gray-900 w-fit rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
										type="number"
										bind:value={config.CODE_EXECUTION_JUPYTER_TIMEOUT}
										placeholder={$i18n.t('e.g. 60')}
										autocomplete="off"
									/>
								</Tooltip>
							</div>
						</div>
					{/if}
				</div>

				<div class="mb-3.5">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('Code Interpreter')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="mb-2.5">
						<div class=" flex w-full justify-between">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('Enable Code Interpreter')}
							</div>

							<Switch bind:state={config.ENABLE_CODE_INTERPRETER} />
						</div>
					</div>

					{#if config.ENABLE_CODE_INTERPRETER}
						<div class="mb-2.5">
							<div class="  flex w-full justify-between">
								<div class=" self-center text-xs font-medium">
									{$i18n.t('Code Interpreter Engine')}
								</div>
								<div class="flex items-center relative">
									<select
										class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
										bind:value={config.CODE_INTERPRETER_ENGINE}
										placeholder={$i18n.t('Select a engine')}
										required
									>
										<option disabled selected value="">{$i18n.t('Select a engine')}</option>
										{#each engines as engine}
											<option value={engine}>{engine}</option>
										{/each}
									</select>
								</div>
							</div>

							{#if config.CODE_INTERPRETER_ENGINE === 'jupyter'}
								<div class="text-gray-500 text-xs">
									{$i18n.t(
										'Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.'
									)}
								</div>
							{/if}
						</div>

						{#if config.CODE_INTERPRETER_ENGINE === 'jupyter'}
							<div class="mb-2.5 flex flex-col gap-1.5 w-full">
								<div class="flex justify-between items-center">
									<div class="text-xs font-medium">
										{$i18n.t('Jupyter URL')}
									</div>
									<button
										type="button"
										class="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition"
										on:click={() => showInterpreterPresets = !showInterpreterPresets}
									>
										🔧 프리셋 선택
									</button>
								</div>

								{#if showInterpreterPresets}
									<div class="flex flex-col gap-1 p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-800">
										{#each jupyterPresets as preset}
											<button
												type="button"
												class="text-left text-xs px-3 py-2 {preset.recommended ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'} hover:bg-blue-100 dark:hover:bg-blue-800/40 rounded border transition"
												on:click={() => applyJupyterPreset(preset, true)}
											>
												<div class="font-medium {preset.recommended ? 'text-blue-700 dark:text-blue-300' : ''}">{preset.name}</div>
												<div class="text-gray-500 text-[10px] mt-0.5">{preset.url}</div>
												{#if preset.description}
													<div class="{preset.recommended ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'} text-[9px] mt-0.5 italic">{preset.description}</div>
												{/if}
											</button>
										{/each}
									</div>
								{/if}

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm py-0.5 placeholder:text-gray-300 dark:placeholder:text-gray-700 bg-transparent outline-hidden"
											type="text"
											placeholder={$i18n.t('Enter Jupyter URL')}
											bind:value={config.CODE_INTERPRETER_JUPYTER_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mb-2.5 flex flex-col gap-1.5 w-full">
								<div class="flex gap-2 w-full items-center justify-between">
									<div class="text-xs font-medium">
										{$i18n.t('Jupyter Auth')}
									</div>

									<div>
										<select
											class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-left"
											bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH}
											placeholder={$i18n.t('Select an auth method')}
										>
											<option selected value="">{$i18n.t('None')}</option>
											<option value="token">{$i18n.t('Token')}</option>
											<option value="password">{$i18n.t('Password')}</option>
										</select>
									</div>
								</div>

								{#if config.CODE_INTERPRETER_JUPYTER_AUTH}
									<div class="flex w-full gap-2">
										<div class="flex-1">
											{#if config.CODE_INTERPRETER_JUPYTER_AUTH === 'password'}
												<SensitiveInput
													type="text"
													placeholder={$i18n.t('Enter Jupyter Password')}
													bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD}
													autocomplete="off"
												/>
											{:else}
												<SensitiveInput
													type="text"
													placeholder={$i18n.t('Enter Jupyter Token')}
													bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN}
													autocomplete="off"
												/>
											{/if}
										</div>
									</div>
								{/if}
							</div>

							<div class="flex gap-2 w-full items-center justify-between">
								<div class="text-xs font-medium">
									{$i18n.t('Code Execution Timeout')}
								</div>

								<div class="">
									<Tooltip content={$i18n.t('Enter timeout in seconds')}>
										<input
											class="dark:bg-gray-900 w-fit rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
											type="number"
											bind:value={config.CODE_INTERPRETER_JUPYTER_TIMEOUT}
											placeholder={$i18n.t('e.g. 60')}
											autocomplete="off"
										/>
									</Tooltip>
								</div>
							</div>
						{/if}

						<hr class="border-gray-100 dark:border-gray-850 my-2" />

						<div>
							<div class="py-0.5 w-full">
								<div class=" mb-2.5 text-xs font-medium">
									{$i18n.t('Code Interpreter Prompt Template')}
								</div>

								<Tooltip
									content={$i18n.t(
										'Leave empty to use the default prompt, or enter a custom prompt'
									)}
									placement="top-start"
								>
									<Textarea
										bind:value={config.CODE_INTERPRETER_PROMPT_TEMPLATE}
										placeholder={$i18n.t(
											'Leave empty to use the default prompt, or enter a custom prompt'
										)}
									/>
								</Tooltip>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
