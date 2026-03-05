<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let citation;
	export let showPercentage = false;
	export let showRelevance = true;

	let mergedDocuments = [];

	function calculatePercentage(distance: number) {
		if (typeof distance !== 'number') return null;
		if (distance < 0) return 0;
		if (distance > 1) return 100;
		return Math.round(distance * 10000) / 100;
	}

	function getRelevanceColor(percentage: number) {
		if (percentage >= 80)
			return 'bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200';
		if (percentage >= 60)
			return 'bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200';
		if (percentage >= 40)
			return 'bg-orange-200 dark:bg-orange-800 text-orange-800 dark:text-orange-200';
		return 'bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200';
	}

	$: if (citation) {
		mergedDocuments = citation.document?.map((c, i) => {
			return {
				source: citation.source,
				document: c,
				metadata: citation.metadata?.[i],
				distance: citation.distances?.[i]
			};
		});
		if (mergedDocuments.every((doc) => doc.distance !== undefined)) {
			mergedDocuments = mergedDocuments.sort(
				(a, b) => (b.distance ?? Infinity) - (a.distance ?? Infinity)
			);
		}
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};
</script>

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-4.5 pt-3 pb-2">
			<div class=" text-lg font-medium self-center flex items-center">
				{#if citation?.source?.name}
					{@const document = mergedDocuments?.[0]}
					{#if document?.metadata?.file_id || document.source?.url?.includes('http')}
						<div class="flex items-center gap-2">
							<Tooltip
								className="w-fit"
								content={document.source?.url?.includes('http')
									? $i18n.t('Open link')
									: $i18n.t('Open file')}
								placement="top-start"
								tippyOptions={{ duration: [500, 0] }}
							>
								<a
									class="hover:text-gray-500 dark:hover:text-gray-100 underline grow line-clamp-1"
									href={document?.metadata?.file_id
										? `${WEBUI_API_BASE_URL}/files/${document?.metadata?.file_id}/content${document?.metadata?.page !== undefined ? `#page=${document.metadata.page + 1}` : ''}`
										: document.source?.url?.includes('http')
											? document.source.url
											: `#`}
									target="_blank"
								>
									{decodeString(citation?.source?.name)}
								</a>
							</Tooltip>
							<!-- [2026-02-02] 보안 다운로드 버튼 추가 -->
							{#if document?.metadata?.file_id}
								<Tooltip
									content={$i18n.t('Secure Download')}
									placement="top"
								>
									<a
										class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
										href={`${WEBUI_API_BASE_URL}/configs/secure-download/${document.metadata.file_id}`}
										download
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
											<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
										</svg>
									</a>
								</Tooltip>
							{/if}
						</div>
					{:else}
						{decodeString(citation?.source?.name)}
					{/if}
				{:else}
					{$i18n.t('Citation')}
				{/if}
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

		<div class="flex flex-col md:flex-row w-full px-5 pb-5 md:space-x-4">
			<div
				class="flex flex-col w-full dark:text-gray-200 overflow-y-scroll max-h-[22rem] scrollbar-thin gap-1"
			>
				{#each mergedDocuments as document, documentIdx}
					<div class="flex flex-col w-full gap-2">
						{#if document.metadata?.parameters}
							<div>
								<div class="text-sm font-medium dark:text-gray-300 mb-1">
									{$i18n.t('Parameters')}
								</div>

								<Textarea readonly value={JSON.stringify(document.metadata.parameters, null, 2)}
								></Textarea>
							</div>
						{/if}

						<div>
							<div
								class=" text-sm font-medium dark:text-gray-300 flex items-center gap-2 w-fit mb-1"
							>
								{$i18n.t('Content')}

								{#if showRelevance && document.distance !== undefined}
									<Tooltip
										className="w-fit"
										content={$i18n.t('Relevance')}
										placement="top-start"
										tippyOptions={{ duration: [500, 0] }}
									>
										<div class="text-sm my-1 dark:text-gray-400 flex items-center gap-2 w-fit">
											{#if showPercentage}
												{@const percentage = calculatePercentage(document.distance)}

												{#if typeof percentage === 'number'}
													<span
														class={`px-1 rounded-sm font-medium ${getRelevanceColor(percentage)}`}
													>
														{percentage.toFixed(2)}%
													</span>
												{/if}
											{:else if typeof document?.distance === 'number'}
												<span class="text-gray-500 dark:text-gray-500">
													({(document?.distance ?? 0).toFixed(4)})
												</span>
											{/if}
										</div>
									</Tooltip>
								{/if}

								{#if Number.isInteger(document?.metadata?.page)}
									<span class="text-sm text-gray-500 dark:text-gray-400">
										({$i18n.t('page')}
										{document.metadata.page + 1})
									</span>
								{/if}
							</div>

							{#if document.metadata?.html}
								<iframe
									class="w-full border-0 h-auto rounded-none"
									sandbox="allow-scripts allow-forms allow-same-origin"
									srcdoc={document.document}
									title={$i18n.t('Content')}
								></iframe>
							{:else}
								<pre class="text-sm dark:text-gray-400 whitespace-pre-line">
                {document.document}
              </pre>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
</Modal>
