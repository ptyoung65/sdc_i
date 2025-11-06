<script>
	import { getContext } from 'svelte';

	export let title = '';
	export let content = '';
	export let showGuide = true;
	const i18n = getContext('i18n');
</script>

<div class="px-3 max-w-2xl">
	<div class="text-center dark:text-white text-2xl font-medium z-50">
		{#if title}
			{title}
		{:else}
			{$i18n.t('Add Files')}
		{/if}
	</div>

	<slot>
		<div class="px-2 mt-2 text-center text-gray-700 dark:text-gray-200 w-full">
			{#if content}
				{content}
			{:else}
				{$i18n.t('Drop any files here to upload')}
			{/if}
		</div>
	</slot>

	{#if showGuide}
		<div class="mt-6 text-left space-y-4">
			<!-- 파일 업로드 방법 -->
			<div class="bg-white dark:bg-gray-800/50 rounded-xl p-4 shadow-sm">
				<h3 class="font-semibold text-sm text-gray-800 dark:text-gray-200 mb-2 flex items-center gap-2">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
					</svg>
					{$i18n.t('How to Upload')}
				</h3>
				<ul class="text-xs text-gray-600 dark:text-gray-400 space-y-1.5">
					<li class="flex items-start gap-2">
						<span class="text-blue-500 mt-0.5">•</span>
						<span>{$i18n.t('Drag and drop files directly into this area')}</span>
					</li>
					<li class="flex items-start gap-2">
						<span class="text-blue-500 mt-0.5">•</span>
						<span>{$i18n.t('Click the attach button to browse and select files')}</span>
					</li>
					<li class="flex items-start gap-2">
						<span class="text-blue-500 mt-0.5">•</span>
						<span>{$i18n.t('Multiple files can be uploaded at once')}</span>
					</li>
				</ul>
			</div>

			<!-- 지원 파일 형식 -->
			<div class="bg-white dark:bg-gray-800/50 rounded-xl p-4 shadow-sm">
				<h3 class="font-semibold text-sm text-gray-800 dark:text-gray-200 mb-2 flex items-center gap-2">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
					</svg>
					{$i18n.t('Supported Formats')}
				</h3>
				<div class="text-xs text-gray-600 dark:text-gray-400 space-y-2">
					<div>
						<span class="font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Documents')}:</span>
						<span class="ml-1">PDF, DOC, DOCX, TXT, MD</span>
					</div>
					<div>
						<span class="font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Spreadsheets')}:</span>
						<span class="ml-1">XLS, XLSX, CSV</span>
					</div>
					<div>
						<span class="font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Presentations')}:</span>
						<span class="ml-1">PPT, PPTX</span>
					</div>
					<div>
						<span class="font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Images')}:</span>
						<span class="ml-1">PNG, JPG, JPEG, GIF, WEBP</span>
					</div>
					<div>
						<span class="font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Code')}:</span>
						<span class="ml-1">JS, PY, JSON, XML, HTML, CSS</span>
					</div>
				</div>
			</div>

			<!-- 제한사항 및 주의사항 -->
			<div class="bg-white dark:bg-gray-800/50 rounded-xl p-4 shadow-sm">
				<h3 class="font-semibold text-sm text-gray-800 dark:text-gray-200 mb-2 flex items-center gap-2">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
					</svg>
					{$i18n.t('Important Notes')}
				</h3>
				<ul class="text-xs text-gray-600 dark:text-gray-400 space-y-1.5">
					<li class="flex items-start gap-2">
						<span class="text-amber-500 mt-0.5">⚠️</span>
						<span>{$i18n.t('Maximum file size: 100MB per file')}</span>
					</li>
					<li class="flex items-start gap-2">
						<span class="text-amber-500 mt-0.5">⚠️</span>
						<span>{$i18n.t('Files are processed automatically for AI context')}</span>
					</li>
					<li class="flex items-start gap-2">
						<span class="text-amber-500 mt-0.5">⚠️</span>
						<span>{$i18n.t('Large files may take longer to process')}</span>
					</li>
					<li class="flex items-start gap-2">
						<span class="text-green-500 mt-0.5">✓</span>
						<span>{$i18n.t('Uploaded files are securely stored and can be referenced in chat')}</span>
					</li>
				</ul>
			</div>

			<!-- 사용 팁 -->
			<div class="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 shadow-sm border border-blue-200 dark:border-blue-800">
				<h3 class="font-semibold text-sm text-blue-800 dark:text-blue-200 mb-2 flex items-center gap-2">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
					</svg>
					{$i18n.t('Pro Tips')}
				</h3>
				<ul class="text-xs text-blue-700 dark:text-blue-300 space-y-1.5">
					<li class="flex items-start gap-2">
						<span class="mt-0.5">💡</span>
						<span>{$i18n.t('Upload reference documents before asking questions for better AI responses')}</span>
					</li>
					<li class="flex items-start gap-2">
						<span class="mt-0.5">💡</span>
						<span>{$i18n.t('PDF and DOCX files are best for document analysis')}</span>
					</li>
					<li class="flex items-start gap-2">
						<span class="mt-0.5">💡</span>
						<span>{$i18n.t('Images can be analyzed for content and text extraction')}</span>
					</li>
				</ul>
			</div>
		</div>
	{/if}
</div>
