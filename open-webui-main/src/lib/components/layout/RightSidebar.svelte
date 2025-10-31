<script context="module" lang="ts">
	import { writable } from 'svelte/store';

	// 선택된 카테고리를 저장하는 store (모듈 레벨 export)
	export const selectedCategories = writable<string[]>([]);

	// 표시용 카테고리 정의 (다른 컴포넌트에서도 사용 가능)
	export const DISPLAY_CATEGORIES = [
		{
			id: 'edm',
			name: 'EDM 문서활용',
			color: 'bg-blue-500',
			description: '전자문서관리 시스템',
			actualIds: ['edm']
		},
		{
			id: 'daesawoo',
			name: '대사우 Assistant',
			color: 'bg-green-500',
			description: '회사생활가이드, IT Help Desk, 용어사전 등',
			actualIds: ['guide', 'helpdesk', 'dictionary', 'etc']
		}
	];

	// 선택된 카테고리 ID 배열을 표시용 카테고리 배열로 변환
	export function getDisplayCategoriesFromIds(categoryIds: string[]) {
		const displayCats = [];

		// EDM 체크
		if (categoryIds.includes('edm')) {
			displayCats.push(DISPLAY_CATEGORIES[0]); // EDM 문서활용
		}

		// 대사우 Assistant 체크 (guide, helpdesk, dictionary, etc 중 하나라도 있으면)
		const daesawooIds = ['guide', 'helpdesk', 'dictionary', 'etc'];
		if (daesawooIds.some(id => categoryIds.includes(id))) {
			displayCats.push(DISPLAY_CATEGORIES[1]); // 대사우 Assistant
		}

		return displayCats;
	}
</script>

<script lang="ts">
	import { slide, fade } from 'svelte/transition';
	import { showRightSidebar, modelType } from '$lib/stores';

	// 실제 카테고리 목록 (백엔드에서 사용)
	const actualCategories = [
		{ id: 'edm', name: 'EDM 검색', color: 'bg-blue-500' },
		{ id: 'guide', name: '회사생활가이드', color: 'bg-green-500' },
		{ id: 'helpdesk', name: 'IT Help Desk', color: 'bg-purple-500' },
		{ id: 'dictionary', name: '용어사전', color: 'bg-orange-500' },
		{ id: 'etc', name: '기타', color: 'bg-gray-500' }
	];

	// UI에 표시할 카테고리 (모듈에서 export된 것 사용)
	const displayCategories = DISPLAY_CATEGORIES;

	// $ 문법을 사용한 자동 구독으로 반응성 개선
	$: selected = $selectedCategories;

	// 카테고리 토글 함수 (통합된 카테고리 지원)
	const toggleCategory = (displayCategory: typeof displayCategories[0]) => {
		const { actualIds } = displayCategory;

		// 모든 실제 ID가 선택되어 있는지 확인
		const allSelected = actualIds.every(id => $selectedCategories.includes(id));

		console.log('🔵 카테고리 클릭:', displayCategory.name, '현재 선택:', allSelected);

		if (allSelected) {
			// 모두 선택 해제
			selectedCategories.update(cats => {
				const filtered = cats.filter(id => !actualIds.includes(id));
				console.log('❌ 선택 해제 후:', filtered);
				return filtered;
			});
		} else {
			// 모두 선택 (중복 제거)
			selectedCategories.update(cats => {
				const newCats = [...cats];
				actualIds.forEach(id => {
					if (!newCats.includes(id)) {
						newCats.push(id);
					}
				});
				console.log('✅ 선택 후:', newCats);
				return newCats;
			});
		}
	};

	// 표시 카테고리가 선택되었는지 확인하는 함수 (반응형으로 변경)
	$: isDisplayCategorySelected = (displayCategory: typeof displayCategories[0]) => {
		return displayCategory.actualIds.every(id => $selectedCategories.includes(id));
	};

	// 사이드바 토글 (내부 모델일 때만 가능)
	const toggleSidebar = () => {
		if ($modelType === 'internal') {
			showRightSidebar.set(!$showRightSidebar);
		}
	};
</script>

{#if $showRightSidebar}
<!-- Right sidebar panel -->
<div class="h-full w-full flex flex-col bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 shadow-2xl">
		<!-- 헤더 -->
		<div class="flex items-center justify-between px-3 py-3 border-b border-gray-200 dark:border-gray-800">
			<div class="flex items-center gap-2">
				<button
					on:click={toggleSidebar}
					class="p-1.5 rounded-lg transition {$modelType === 'internal' ? 'hover:bg-gray-100 dark:hover:bg-gray-800' : 'opacity-50 cursor-not-allowed'}"
					title={$modelType === 'internal' ? "사이드바 접기" : "외부 모델 사용 중에는 카테고리 선택이 불가능합니다"}
					disabled={$modelType !== 'internal'}
				>
					<!-- 햄버거 메뉴 아이콘 -->
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
						 stroke-width="2" stroke="currentColor" class="size-5">
						<path stroke-linecap="round" stroke-linejoin="round"
							  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"/>
					</svg>
				</button>
				<h2 class="text-sm font-semibold text-gray-800 dark:text-gray-100">
					카테고리
				</h2>
			</div>
		</div>

		<!-- 카테고리 카드 리스트 -->
		<div class="flex-1 overflow-y-auto px-3 py-4 space-y-3">
			{#each displayCategories as category}
				<button
					on:click={() => toggleCategory(category)}
					class="w-full p-4 rounded-xl border-2 transition-all duration-200 text-left
						{isDisplayCategorySelected(category)
							? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 shadow-md'
							: 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm'
						}"
				>
					<div class="flex items-start gap-3">
						<!-- 선택 체크박스 -->
						<div class="flex-shrink-0 pt-0.5">
							<div
								class="w-5 h-5 rounded border-2 flex items-center justify-center transition-all duration-200
									{isDisplayCategorySelected(category)
										? 'bg-blue-500 border-blue-500 scale-105'
										: 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800'
									}"
							>
								{#if isDisplayCategorySelected(category)}
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3.5 h-3.5 text-white" transition:fade={{duration: 150}}>
										<path fill-rule="evenodd" d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z" clip-rule="evenodd" />
									</svg>
								{/if}
							</div>
						</div>

						<!-- 카테고리 정보 -->
						<div class="flex-1 min-w-0">
							<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">
								{category.name}
							</h3>

							<!-- 설명 -->
							<p class="text-xs text-gray-500 dark:text-gray-400">
								{category.description}
							</p>
						</div>
					</div>
				</button>
			{/each}
		</div>

		<!-- 하단 정보 -->
		<div class="px-3 py-3 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
			{#if selected.length > 0}
				<p class="text-xs text-blue-600 dark:text-blue-400 text-center font-medium">
					✓ {selected.length}개 카테고리 선택됨
				</p>
			{:else}
				<p class="text-xs text-gray-500 dark:text-gray-400 text-center">
					카테고리를 선택하여 검색 범위를 설정하세요
				</p>
			{/if}
		</div>
</div>
{/if}

<!-- 사이드바가 닫혔을 때 보이는 토글 버튼 (오른쪽 상단) - 내부 모델일 때만 -->
{#if !$showRightSidebar && $modelType === 'internal'}
	<button
		on:click={toggleSidebar}
		class="fixed right-4 top-4 z-40 p-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-lg transition-all duration-200 hover:shadow-xl"
		title="카테고리 열기"
	>
		<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
			 stroke-width="2.5" stroke="currentColor" class="w-5 h-5">
			<path stroke-linecap="round" stroke-linejoin="round"
				  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"/>
		</svg>
	</button>
{/if}

<style>
	/* 스크롤바 스타일 */
	.overflow-y-auto::-webkit-scrollbar {
		width: 6px;
	}

	.overflow-y-auto::-webkit-scrollbar-track {
		background: transparent;
	}

	.overflow-y-auto::-webkit-scrollbar-thumb {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 3px;
	}

	.overflow-y-auto::-webkit-scrollbar-thumb:hover {
		background: rgba(156, 163, 175, 0.7);
	}

	:global(.dark) .overflow-y-auto::-webkit-scrollbar-thumb {
		background: rgba(75, 85, 99, 0.5);
	}

	:global(.dark) .overflow-y-auto::-webkit-scrollbar-thumb:hover {
		background: rgba(75, 85, 99, 0.7);
	}
</style>
