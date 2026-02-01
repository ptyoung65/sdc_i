<script lang="ts">
	import { marked } from 'marked';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, mobile, models as _models, settings, user } from '$lib/stores';
	import {
		createNewModel,
		deleteAllModels,
		getBaseModels,
		toggleModelById,
		updateModelById,
		importModels
	} from '$lib/apis/models';
	import { copyToClipboard } from '$lib/utils';
	import { page } from '$app/stores';

	import { getModels } from '$lib/apis';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import ModelEditor from '$lib/components/workspace/Models/ModelEditor.svelte';
	import { toast } from 'svelte-sonner';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ConfigureModelsModal from './Models/ConfigureModelsModal.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import ManageModelsModal from './Models/ManageModelsModal.svelte';
	import ModelMenu from '$lib/components/admin/Settings/Models/ModelMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getModelsConfig, setModelsConfig, getModelColors, setModelColors, syncConfigToAllServers, getClusterServers } from '$lib/apis/configs';
	// [2026.01.19] 모델 색상 설정 Store
	import { modelColors as modelColorsStore, AVAILABLE_COLORS, DEFAULT_MODEL_COLORS } from '$lib/stores';

	let shiftKey = false;

	// ============================================================================================================
	// [2025.01.05] 세션 제한 설정 저장 기능 (턴 및 토큰수 제약처리)
	// ============================================================================================================
	//
	// ■ 기능 개요:
	//   모델별로 Max Turns, Max Tokens, Max Input Tokens, Warning Turns 값을 설정하고 config DB에 저장
	//
	// ■ 설정 화면: /admin/settings/models
	//
	// ■ 데이터 구조:
	//   modelSessionLimits = {
	//     "모델ID": {
	//       maxTurns: 10,        // 최대 대화 턴수 (0=무제한)
	//       maxTokens: 50000,    // 세션 전체 최대 토큰수 (0=무제한)
	//       maxInputTokens: 4000, // 1턴당 입력 가능 토큰수 (0=무제한)
	//       warningTurns: 2      // Max Turns 이전 몇 턴부터 경고할지 (0=경고없음)
	//     }
	//   }
	//
	// ■ 저장 흐름 (상세):
	//   [프론트엔드]
	//   1. 관리자가 UI에서 값 입력 → setModelLimit() 호출 → modelSessionLimits 객체 업데이트
	//   2. "세션 제한 저장" 버튼 클릭 → saveSessionLimits() 호출
	//   3. getModelsConfig() → 기존 설정 조회 (src/lib/apis/configs/index.ts)
	//   4. setModelsConfig() → MODEL_SESSION_LIMITS 키로 저장 요청
	//
	//   [백엔드 API - configs.py]
	//   5. POST /api/v1/configs/models → set_models_config() 함수 실행
	//   6. get_config()로 기존 config 전체 조회
	//   7. config["MODEL_SESSION_LIMITS"] = 새로운 값 병합
	//   8. save_config(config) 호출
	//
	//   [DB 저장 - config.py]
	//   9. save_config() → save_to_db() 호출
	//   10. SQLAlchemy ORM으로 config 테이블 UPDATE
	//   11. data 컬럼(JSONB)에 전체 설정 JSON 저장
	//   12. CONFIG_DATA 전역 변수 업데이트 (메모리 캐시)
	//   13. PERSISTENT_CONFIG_REGISTRY 업데이트 트리거
	//
	// ■ DB 저장 위치:
	//   - 테이블: config
	//   - 컬럼: data (JSONB 타입)
	//   - 키: MODEL_SESSION_LIMITS
	//
	// ■ API 엔드포인트:
	//   - GET  /api/v1/configs/models → 설정 조회
	//   - POST /api/v1/configs/models → 설정 저장
	//
	// ■ 컨테이너 재시작: 불필요 (즉시 적용)
	//   - DB에 직접 저장되고 메모리 캐시도 동기화됨
	//   - 신규 채팅: 즉시 적용
	//   - 기존 채팅: 다음 메시지부터 적용
	//
	// ■ 관련 파일:
	//   - src/lib/components/admin/Settings/Models.svelte (현재 파일 - UI)
	//   - src/lib/apis/configs/index.ts (API 클라이언트)
	//   - backend/open_webui/routers/configs.py (백엔드 API)
	//   - backend/open_webui/config.py (DB 저장/조회 핵심 함수)
	//
	// ============================================================================================================
	// ----- [2025.01.05] 세션 제한 설정 저장 기능 시작 -----

	// ▼ 상태 변수 정의
	let modelSessionLimits = {};       // 모델별 세션 제한 설정 저장 객체
	let showSessionLimitsSection = true; // 세션 제한 섹션 표시 여부
	let sessionLimitsLoading = false;    // 저장 중 로딩 상태
	let limitsLoaded = false;            // 설정 로드 완료 여부

	// ▼ 설정 로드 함수 - config DB에서 MODEL_SESSION_LIMITS 조회
	const loadSessionLimits = async () => {
		try {
			// API 호출: GET /api/v1/configs/models
			const config = await getModelsConfig(localStorage.token);
			// config.MODEL_SESSION_LIMITS에서 모델별 제한 설정 추출
			if (config?.MODEL_SESSION_LIMITS) {
				modelSessionLimits = config.MODEL_SESSION_LIMITS;
			}
			limitsLoaded = true;
		} catch (e) {
			console.error('세션 제한 설정 로드 실패:', e);
			limitsLoaded = true;
		}
	};

	// ▼ 설정 저장 함수 - config DB에 MODEL_SESSION_LIMITS 저장
	const saveSessionLimits = async () => {
		sessionLimitsLoading = true;
		try {
			// 1. 기존 설정 조회 (다른 설정 유지를 위해)
			const config = await getModelsConfig(localStorage.token);

			// 2. MODEL_SESSION_LIMITS 키로 설정 저장
			// API 호출: POST /api/v1/configs/models
			// 요청 본문: { ...기존설정, MODEL_SESSION_LIMITS: modelSessionLimits }
			await setModelsConfig(localStorage.token, {
				...config,
				MODEL_SESSION_LIMITS: modelSessionLimits
			});

			toast.success($i18n.t('Session limits saved successfully'));
		} catch (e) {
			console.error('세션 제한 설정 저장 실패:', e);
			toast.error($i18n.t('Failed to save session limits'));
		}
		sessionLimitsLoading = false;
	};

	// ▼ 모델별 제한값 조회 헬퍼 함수
	const getModelLimit = (modelId, field) => {
		// modelSessionLimits[모델ID][필드명] 반환, 없으면 0
		return modelSessionLimits[modelId]?.[field] || 0;
	};

	// ▼ 모델별 제한값 설정 헬퍼 함수
	const setModelLimit = (modelId, field, value) => {
		// 해당 모델의 설정이 없으면 기본 구조 생성
		if (!modelSessionLimits[modelId]) {
			// 기본 구조: maxTurns, maxTokens, maxInputTokens, warningTurns
			modelSessionLimits[modelId] = {
				maxTurns: 0,        // 최대 대화 턴수
				maxTokens: 0,       // 세션 전체 최대 토큰수
				maxInputTokens: 0,  // 1턴당 입력 가능 토큰수
				warningTurns: 0     // 경고 시작 턴수 (Max Turns - warningTurns 도달 시 경고)
			};
		}
		// 입력값을 정수로 변환하여 저장
		modelSessionLimits[modelId][field] = parseInt(value) || 0;
	};
	// ----- [2025.01.05] 세션 제한 설정 저장 기능 종료 -----
	// ============================================================================================================
	// [2025.01.05] 세션 제한 설정 저장 기능 완료
	// ============================================================================================================

	// ============================================================================================================
	// ----- [2026-01-31] Active-Active 서버 동기화 기능 시작 -----
	// ============================================================================================================
	//
	// ■ 기능 개요:
	//   Active-Active 환경에서 설정 변경 후 모든 서버의 메모리 캐시를 동기화
	//
	// ■ 환경변수 설정 필요 (백엔드):
	//   CLUSTER_SERVER_URLS=http://192.168.122.178:8080,http://192.168.122.177:8080
	//
	// ============================================================================================================

	let syncLoading = false;           // 동기화 중 로딩 상태
	let clusterServers = [];           // 클러스터 서버 목록
	let clusterConfigured = false;     // 클러스터 설정 여부

	// ▼ 클러스터 서버 정보 로드
	const loadClusterServers = async () => {
		try {
			const result = await getClusterServers(localStorage.token);
			if (result) {
				clusterServers = result.servers || [];
				clusterConfigured = result.configured || false;
			}
		} catch (e) {
			console.error('클러스터 서버 정보 로드 실패:', e);
		}
	};

	// ▼ 모든 서버 동기화 함수
	const syncAllServers = async () => {
		syncLoading = true;
		try {
			const result = await syncConfigToAllServers(localStorage.token);
			if (result?.success) {
				toast.success($i18n.t(`서버 동기화 완료: ${result.successful_servers}/${result.total_servers}`));
			} else {
				// 부분 실패
				const failedServers = result?.results?.filter(r => !r.success).map(r => r.server).join(', ');
				toast.warning($i18n.t(`일부 서버 동기화 실패: ${failedServers}`));
			}
			console.log('[Sync] 동기화 결과:', result);
		} catch (e) {
			console.error('서버 동기화 실패:', e);
			toast.error($i18n.t('서버 동기화 실패'));
		}
		syncLoading = false;
	};

	// ----- [2026-01-31] Active-Active 서버 동기화 기능 종료 -----
	// ============================================================================================================

	// ============================================================================================================
	// [2026.01.19] 모델 색상 설정 기능
	// ============================================================================================================
	//
	// ■ 기능 개요:
	//   모델명에 포함된 키워드를 기반으로 채팅 화면에서 모델명을 색상으로 구분하여 표시
	//
	// ■ 데이터 구조:
	//   modelColorsList = [
	//     { keyword: "gpt", color: "emerald", label: "GPT (OpenAI)" },
	//     { keyword: "claude", color: "orange", label: "Claude (Anthropic)" },
	//     ...
	//   ]
	//
	// ■ API 엔드포인트:
	//   - GET  /api/v1/configs/model-colors → 설정 조회
	//   - POST /api/v1/configs/model-colors → 설정 저장
	//
	// ----- [2026.01.19] 모델 색상 설정 기능 시작 -----

	// ▼ 상태 변수 정의
	let modelColorsList = [...DEFAULT_MODEL_COLORS]; // 모델 색상 매핑 배열
	let showModelColorsSection = true;               // 색상 설정 섹션 표시 여부
	let modelColorsLoading = false;                  // 저장 중 로딩 상태
	let colorsLoaded = false;                        // 설정 로드 완료 여부

	// ▼ 설정 로드 함수 - config DB에서 MODEL_COLORS 조회
	const loadModelColors = async () => {
		try {
			const result = await getModelColors(localStorage.token);
			if (result?.colors && Array.isArray(result.colors)) {
				modelColorsList = result.colors;
				// Store도 업데이트
				modelColorsStore.set(result.colors);
			}
			colorsLoaded = true;
		} catch (e) {
			console.error('모델 색상 설정 로드 실패:', e);
			colorsLoaded = true;
		}
	};

	// ▼ 설정 저장 함수 - config DB에 MODEL_COLORS 저장
	const saveModelColors = async () => {
		modelColorsLoading = true;
		try {
			await setModelColors(localStorage.token, modelColorsList);
			// Store도 업데이트
			modelColorsStore.set(modelColorsList);
			toast.success($i18n.t('Model colors saved successfully'));
		} catch (e) {
			console.error('모델 색상 설정 저장 실패:', e);
			toast.error($i18n.t('Failed to save model colors'));
		}
		modelColorsLoading = false;
	};

	// ▼ 색상 매핑 추가
	const addColorMapping = () => {
		modelColorsList = [...modelColorsList, { keyword: '', color: 'gray', label: '' }];
	};

	// ▼ 색상 매핑 삭제
	const removeColorMapping = (index) => {
		modelColorsList = modelColorsList.filter((_, i) => i !== index);
	};

	// ▼ 색상 매핑 업데이트
	const updateColorMapping = (index, field, value) => {
		modelColorsList[index][field] = value;
		modelColorsList = [...modelColorsList]; // 반응성 트리거
	};

	// ▼ 기본값으로 초기화
	const resetModelColors = () => {
		modelColorsList = [...DEFAULT_MODEL_COLORS];
	};
	// ----- [2026.01.19] 모델 색상 설정 기능 종료 -----
	// ============================================================================================================

	let modelsImportInProgress = false;
	let importFiles;
	let modelsImportInputElement: HTMLInputElement;

	let models = null;

	let workspaceModels = null;
	let baseModels = null;

	let filteredModels = [];
	let selectedModelId = null;

	let showConfigModal = false;
	let showManageModal = false;

	$: if (models) {
		filteredModels = models
			.filter((m) => searchValue === '' || m.name.toLowerCase().includes(searchValue.toLowerCase()))
			.sort((a, b) => {
				// // Check if either model is inactive and push them to the bottom
				// if ((a.is_active ?? true) !== (b.is_active ?? true)) {
				// 	return (b.is_active ?? true) - (a.is_active ?? true);
				// }
				// If both models' active states are the same, sort alphabetically
				return (a?.name ?? a?.id ?? '').localeCompare(b?.name ?? b?.id ?? '');
			});
	}

	let searchValue = '';

	// 모델 타입 판단 함수 (내부/외부)
	// 내부: SDC 회사 내부 모델
	// 외부: MCP 서버를 통해 외부 LLM 서버로 연결
	const getModelType = (model) => {
		// meta에 model_type이 설정되어 있으면 그것 사용
		if (model?.meta?.model_type) {
			return model.meta.model_type;
		}
		// 기본값: 외부 모델
		return 'external';
	};

	const downloadModels = async (models) => {
		let blob = new Blob([JSON.stringify(models)], {
			type: 'application/json'
		});
		saveAs(blob, `models-export-${Date.now()}.json`);
	};

	const init = async () => {
		models = null;

		workspaceModels = await getBaseModels(localStorage.token);
		baseModels = await getModels(localStorage.token, null, true);

		models = baseModels.map((m) => {
			const workspaceModel = workspaceModels.find((wm) => wm.id === m.id);

			if (workspaceModel) {
				return {
					...m,
					...workspaceModel
				};
			} else {
				return {
					...m,
					id: m.id,
					name: m.name,

					is_active: true
				};
			}
		});
	};

	const upsertModelHandler = async (model) => {
		model.base_model_id = null;

		if (workspaceModels.find((m) => m.id === model.id)) {
			const res = await updateModelById(localStorage.token, model.id, model).catch((error) => {
				return null;
			});

			if (res) {
				toast.success($i18n.t('Model updated successfully'));
			}
		} else {
			const res = await createNewModel(localStorage.token, {
				meta: {},
				id: model.id,
				name: model.name,
				base_model_id: null,
				params: {},
				access_control: {},
				...model
			}).catch((error) => {
				return null;
			});

			if (res) {
				toast.success($i18n.t('Model updated successfully'));
			}
		}
		await init();

		_models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const toggleModelHandler = async (model) => {
		if (!Object.keys(model).includes('base_model_id')) {
			await createNewModel(localStorage.token, {
				id: model.id,
				name: model.name,
				base_model_id: null,
				meta: {},
				params: {},
				access_control: {},
				is_active: model.is_active
			}).catch((error) => {
				return null;
			});
		} else {
			await toggleModelById(localStorage.token, model.id);
		}

		// await init();
		_models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const hideModelHandler = async (model) => {
		model.meta = {
			...model.meta,
			hidden: !(model?.meta?.hidden ?? false)
		};

		console.debug(model);

		toast.success(
			model.meta.hidden
				? $i18n.t(`Model {{name}} is now hidden`, {
						name: model.id
					})
				: $i18n.t(`Model {{name}} is now visible`, {
						name: model.id
					})
		);

		upsertModelHandler(model);
	};

	const copyLinkHandler = async (model) => {
		const baseUrl = window.location.origin;
		const res = await copyToClipboard(`${baseUrl}/?model=${encodeURIComponent(model.id)}`);

		if (res) {
			toast.success($i18n.t('Copied link to clipboard'));
		} else {
			toast.error($i18n.t('Failed to copy link'));
		}
	};

	const exportModelHandler = async (model) => {
		let blob = new Blob([JSON.stringify([model])], {
			type: 'application/json'
		});
		saveAs(blob, `${model.id}-${Date.now()}.json`);
	};

	onMount(async () => {
		await init();
		await loadSessionLimits(); // 세션 제한 설정 로드
		await loadModelColors(); // [2026.01.19] 모델 색상 설정 로드
		await loadClusterServers(); // [2026-01-31] 클러스터 서버 정보 로드
		const id = $page.url.searchParams.get('id');

		if (id) {
			selectedModelId = id;
		}

		const onKeyDown = (event) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur-sm', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur-sm', onBlur);
		};
	});
</script>

<ConfigureModelsModal bind:show={showConfigModal} initHandler={init} />
<ManageModelsModal bind:show={showManageModal} />

{#if models !== null}
	{#if selectedModelId === null}
		<div class="flex flex-col gap-1 mt-1.5 mb-2">
			<div class="flex justify-between items-center">
				<div class="flex items-center md:self-center text-xl font-medium px-0.5">
					{$i18n.t('Models')}
					<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
					<span class="text-lg font-medium text-gray-500 dark:text-gray-300"
						>{filteredModels.length}</span
					>
				</div>

				<div class="flex items-center gap-1.5">
					<Tooltip content={$i18n.t('Manage Models')}>
						<button
							class=" p-1 rounded-full flex gap-1 items-center"
							type="button"
							on:click={() => {
								showManageModal = true;
							}}
						>
							<Download />
						</button>
					</Tooltip>

					<Tooltip content={$i18n.t('Settings')}>
						<button
							class=" p-1 rounded-full flex gap-1 items-center"
							type="button"
							on:click={() => {
								showConfigModal = true;
							}}
						>
							<Cog6 />
						</button>
					</Tooltip>
				</div>
			</div>

			<div class=" flex flex-1 items-center w-full space-x-2">
				<div class="flex flex-1 items-center">
					<div class=" self-center ml-1 mr-3">
						<Search className="size-3.5" />
					</div>
					<input
						class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={searchValue}
						placeholder={$i18n.t('Search Models')}
					/>
					{#if searchValue}
						<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
							<button
								class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
								on:click={() => {
									searchValue = '';
								}}
							>
								<XMark className="size-3" strokeWidth="2" />
							</button>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<!-- ============================================ -->
		<!-- [2024.12.30] 턴 및 토큰수 제약처리 - 관리자 UI 시작 -->
		<!-- 역할: 모델별 세션 제한 설정 UI (Max Turns/Tokens/Input Tokens/Warning) -->
		<!-- 설정 화면: /admin/settings/models -->
		<!-- ============================================ -->
		<!-- ----- 1225 maxInputTokens UI 추가 시작 ----- -->
		<!-- 세션 제한 설정 섹션 -->
		<div class="my-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
			<button
				class="w-full flex justify-between items-center text-left"
				on:click={() => { showSessionLimitsSection = !showSessionLimitsSection; }}
			>
				<div class="flex items-center gap-2">
					<span class="text-lg font-medium text-gray-900 dark:text-white">
						세션 제한 설정
					</span>
					<span class="text-xs text-gray-500">(모델별 최대 턴수/토큰수/입력토큰수)</span>
				</div>
				<svg class="w-5 h-5 transform transition-transform {showSessionLimitsSection ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</button>

			{#if showSessionLimitsSection}
				<div class="mt-4 space-y-3">
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
						* 0 = 무제한 또는 경고없음 / Warning = Max Turns 이전 몇 턴부터 경고할지 / Max Input = 1턴당 입력 가능 토큰수
					</div>

					<div class="max-h-80 overflow-y-auto space-y-2">
						{#if limitsLoaded}
						{#each filteredModels as model (model.id)}
							<div class="flex flex-wrap items-center gap-2 p-2 bg-white dark:bg-gray-700 rounded border border-gray-100 dark:border-gray-600">
								<div class="flex-1 min-w-0" style="min-width: 120px;">
									<div class="text-sm font-medium text-gray-700 dark:text-gray-200 truncate" title={model.name || model.id}>
										{model.name || model.id}
									</div>
								</div>
								<div class="flex items-center gap-1 shrink-0">
									<label class="text-xs text-gray-500 whitespace-nowrap">Max Turns:</label>
									<input
										type="number"
										min="0"
										max="100"
										class="w-14 px-1 py-1 text-sm border border-gray-300 dark:border-gray-500 rounded bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100"
										value={getModelLimit(model.id, 'maxTurns')}
										on:change={(e) => setModelLimit(model.id, 'maxTurns', e.target.value)}
										placeholder="0"
									/>
								</div>
								<div class="flex items-center gap-1 shrink-0">
									<label class="text-xs text-gray-500 whitespace-nowrap" title="Max Turns 이전 몇 턴부터 경고할지 (0=경고없음)">Warning:</label>
									<input
										type="number"
										min="0"
										max="10"
										class="w-12 px-1 py-1 text-sm border border-gray-300 dark:border-gray-500 rounded bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100"
										value={getModelLimit(model.id, 'warningTurns')}
										on:change={(e) => setModelLimit(model.id, 'warningTurns', e.target.value)}
										placeholder="0"
										title="Max Turns 이전 몇 턴부터 경고할지 (0=경고없음, 예: 2 입력 시 Max Turns-2 도달 시 경고)"
									/>
								</div>
								<div class="flex items-center gap-1 shrink-0">
									<label class="text-xs text-gray-500 whitespace-nowrap">Max Tokens:</label>
									<input
										type="number"
										min="0"
										step="1000"
										class="w-20 px-1 py-1 text-sm border border-gray-300 dark:border-gray-500 rounded bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100"
										value={getModelLimit(model.id, 'maxTokens')}
										on:change={(e) => setModelLimit(model.id, 'maxTokens', e.target.value)}
										placeholder="0"
									/>
								</div>
								<div class="flex items-center gap-1 shrink-0">
									<label class="text-xs text-gray-500 whitespace-nowrap">Max Input:</label>
									<input
										type="number"
										min="0"
										step="500"
										class="w-20 px-1 py-1 text-sm border border-gray-300 dark:border-gray-500 rounded bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100"
										value={getModelLimit(model.id, 'maxInputTokens')}
										on:change={(e) => setModelLimit(model.id, 'maxInputTokens', e.target.value)}
										placeholder="0"
										title="1턴당 입력 가능한 최대 토큰수"
									/>
								</div>
							</div>
						{/each}
						{/if}
					</div>

					<!-- [2026-01-31] 저장 및 동기화 버튼 영역 -->
					<div class="flex justify-between items-center pt-2">
						<!-- 클러스터 서버 정보 표시 -->
						<div class="text-xs text-gray-500 dark:text-gray-400">
							{#if clusterConfigured}
								<span class="text-green-600 dark:text-green-400">● 클러스터 구성됨 ({clusterServers.length}대)</span>
							{:else}
								<span class="text-yellow-600 dark:text-yellow-400">● 단일 서버 모드</span>
							{/if}
						</div>

						<div class="flex gap-2">
							<!-- 수동 동기화 버튼 -->
							<button
								class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500 rounded-lg transition-colors disabled:opacity-50"
								on:click={syncAllServers}
								disabled={syncLoading}
								title="모든 클러스터 서버의 설정 캐시를 동기화합니다"
							>
								{#if syncLoading}
									<span class="flex items-center gap-2">
										<Spinner className="size-4" />
										동기화 중...
									</span>
								{:else}
									<span class="flex items-center gap-2">
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
										</svg>
										서버 동기화
									</span>
								{/if}
							</button>

							<!-- 저장 버튼 -->
							<button
								class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
								on:click={saveSessionLimits}
								disabled={sessionLimitsLoading}
							>
								{#if sessionLimitsLoading}
									<span class="flex items-center gap-2">
										<Spinner className="size-4" />
										저장 중...
									</span>
								{:else}
									세션 제한 저장
								{/if}
							</button>
						</div>
					</div>
				</div>
			{/if}
		</div>
		<!-- ----- 1225 maxInputTokens UI 추가 종료 ----- -->
		<!-- [2024.12.30] 턴 및 토큰수 제약처리 - 관리자 UI 완료 ============================================ -->

		<!-- ============================================ -->
		<!-- [2026.01.19] 모델 색상 설정 - 관리자 UI 시작 -->
		<!-- 역할: 모델명 키워드별 색상 매핑 설정 UI -->
		<!-- ============================================ -->
		<div class="my-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
			<button
				class="w-full flex justify-between items-center text-left"
				on:click={() => { showModelColorsSection = !showModelColorsSection; }}
			>
				<div class="flex items-center gap-2">
					<span class="text-lg font-medium text-gray-900 dark:text-white">
						모델 색상 설정
					</span>
					<span class="text-xs text-gray-500">(모델명 키워드별 색상 지정)</span>
				</div>
				<svg class="w-5 h-5 transform transition-transform {showModelColorsSection ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</button>

			{#if showModelColorsSection}
				<div class="mt-4 space-y-3">
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
						* 모델명에 포함된 키워드를 기준으로 채팅 화면에서 모델명 색상이 적용됩니다. (위에서부터 우선순위 적용)
					</div>

					<div class="max-h-80 overflow-y-auto space-y-2">
						{#if colorsLoaded}
							{#each modelColorsList as colorItem, index (index)}
								<div class="flex flex-wrap items-center gap-2 p-2 bg-white dark:bg-gray-700 rounded border border-gray-100 dark:border-gray-600">
									<div class="flex items-center gap-1 shrink-0">
										<label class="text-xs text-gray-500 whitespace-nowrap">키워드:</label>
										<input
											type="text"
											class="w-24 px-2 py-1 text-sm border border-gray-300 dark:border-gray-500 rounded bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100"
											value={colorItem.keyword}
											on:change={(e) => updateColorMapping(index, 'keyword', e.target.value)}
											placeholder="gpt"
										/>
									</div>
									<div class="flex items-center gap-1 shrink-0">
										<label class="text-xs text-gray-500 whitespace-nowrap">라벨:</label>
										<input
											type="text"
											class="w-32 px-2 py-1 text-sm border border-gray-300 dark:border-gray-500 rounded bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100"
											value={colorItem.label}
											on:change={(e) => updateColorMapping(index, 'label', e.target.value)}
											placeholder="GPT (OpenAI)"
										/>
									</div>
									<div class="flex items-center gap-1 shrink-0">
										<label class="text-xs text-gray-500 whitespace-nowrap">색상:</label>
										<select
											class="w-36 px-2 py-1 text-sm border border-gray-300 dark:border-gray-500 rounded bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100"
											value={colorItem.color}
											on:change={(e) => updateColorMapping(index, 'color', e.target.value)}
										>
											{#each AVAILABLE_COLORS as color}
												<option value={color.value}>{color.label}</option>
											{/each}
										</select>
									</div>
									<div class="flex items-center gap-1 shrink-0">
										<!-- 색상 미리보기 -->
										<span class="px-2 py-0.5 rounded text-sm font-semibold {AVAILABLE_COLORS.find(c => c.value === colorItem.color)?.light || 'text-gray-700'} bg-gray-100 dark:bg-gray-600">
											{colorItem.label || colorItem.keyword || '미리보기'}
										</span>
									</div>
									<button
										class="p-1 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
										on:click={() => removeColorMapping(index)}
										title="삭제"
									>
										<XMark className="size-4" />
									</button>
								</div>
							{/each}
						{/if}
					</div>

					<div class="flex justify-between items-center pt-2">
						<div class="flex gap-2">
							<button
								class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500 rounded-lg transition-colors"
								on:click={addColorMapping}
							>
								+ 매핑 추가
							</button>
							<button
								class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500 rounded-lg transition-colors"
								on:click={resetModelColors}
							>
								기본값 복원
							</button>
						</div>
						<button
							class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
							on:click={saveModelColors}
							disabled={modelColorsLoading}
						>
							{#if modelColorsLoading}
								<span class="flex items-center gap-2">
									<Spinner className="size-4" />
									저장 중...
								</span>
							{:else}
								색상 설정 저장
							{/if}
						</button>
					</div>
				</div>
			{/if}
		</div>
		<!-- [2026.01.19] 모델 색상 설정 - 관리자 UI 종료 ============================================ -->

		<div class=" my-2 mb-5" id="model-list">
			{#if models.length > 0}
				{#each filteredModels as model, modelIdx (model.id)}
					<div
						class=" flex space-x-4 cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-lg transition {model
							?.meta?.hidden
							? 'opacity-50 dark:opacity-50'
							: ''}"
						id="model-item-{model.id}"
					>
						<button
							class=" flex flex-1 text-left space-x-3.5 cursor-pointer w-full"
							type="button"
							on:click={() => {
								selectedModelId = model.id;
							}}
						>
							<div class=" self-center w-8">
								<div
									class=" rounded-full object-cover {(model?.is_active ?? true)
										? ''
										: 'opacity-50 dark:opacity-50'} "
								>
									<img
										src={model?.meta?.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`}
										alt="modelfile profile"
										class=" rounded-full w-full h-auto object-cover"
									/>
								</div>
							</div>

							<div class=" flex-1 self-center {(model?.is_active ?? true) ? '' : 'text-gray-500'}">
								<Tooltip
									content={marked.parse(
										!!model?.meta?.description
											? model?.meta?.description
											: model?.ollama?.digest
												? `${model?.ollama?.digest} **(${model?.ollama?.modified_at})**`
												: model.id
									)}
									className=" w-fit"
									placement="top-start"
								>
									<div class="flex items-center gap-2">
										<div class="font-semibold line-clamp-1">{model.name}</div>
										{#if getModelType(model) === 'internal'}
											<span class="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full">
												내부
											</span>
										{:else}
											<span class="px-2 py-0.5 text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full">
												외부
											</span>
										{/if}
									</div>
								</Tooltip>
								<div class=" text-xs overflow-hidden text-ellipsis line-clamp-1 text-gray-500">
									<span class=" line-clamp-1">
										{!!model?.meta?.description
											? model?.meta?.description
											: model?.ollama?.digest
												? `${model.id} (${model?.ollama?.digest})`
												: model.id}
									</span>
								</div>
							</div>
						</button>
						<div class="flex flex-row gap-0.5 items-center self-center">
							{#if shiftKey}
								<Tooltip content={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}>
									<button
										class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
										type="button"
										on:click={() => {
											hideModelHandler(model);
										}}
									>
										{#if model?.meta?.hidden}
											<EyeSlash />
										{:else}
											<Eye />
										{/if}
									</button>
								</Tooltip>
							{:else}
								<button
									class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
									type="button"
									on:click={() => {
										selectedModelId = model.id;
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-4 h-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
										/>
									</svg>
								</button>

								<ModelMenu
									user={$user}
									{model}
									exportHandler={() => {
										exportModelHandler(model);
									}}
									hideHandler={() => {
										hideModelHandler(model);
									}}
									copyLinkHandler={() => {
										copyLinkHandler(model);
									}}
									onClose={() => {}}
								>
									<button
										class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
										type="button"
									>
										<EllipsisHorizontal className="size-5" />
									</button>
								</ModelMenu>

								<div class="ml-1">
									<Tooltip
										content={(model?.is_active ?? true) ? $i18n.t('Enabled') : $i18n.t('Disabled')}
									>
										<Switch
											bind:state={model.is_active}
											on:change={async () => {
												toggleModelHandler(model);
											}}
										/>
									</Tooltip>
								</div>
							{/if}
						</div>
					</div>
				{/each}
			{:else}
				<div class="flex flex-col items-center justify-center w-full h-20">
					<div class="text-gray-500 dark:text-gray-400 text-xs">
						{$i18n.t('No models found')}
					</div>
				</div>
			{/if}
		</div>

		{#if $user?.role === 'admin'}
			<div class=" flex justify-end w-full mb-3">
				<div class="flex space-x-1">
					<input
						id="models-import-input"
						bind:this={modelsImportInputElement}
						bind:files={importFiles}
						type="file"
						accept=".json"
						hidden
						on:change={() => {
							if (importFiles.length > 0) {
								const reader = new FileReader();
								reader.onload = async (event) => {
									try {
										const models = JSON.parse(String(event.target.result));
										modelsImportInProgress = true;
										const res = await importModels(localStorage.token, models);
										modelsImportInProgress = false;

										if (res) {
											toast.success($i18n.t('Models imported successfully'));
											await init();
										} else {
											toast.error($i18n.t('Failed to import models'));
										}
									} catch (e) {
										toast.error($i18n.t('Invalid JSON file'));
										console.error(e);
									}
								};
								reader.readAsText(importFiles[0]);
							}
						}}
					/>

					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
						disabled={modelsImportInProgress}
						on:click={() => {
							modelsImportInputElement.click();
						}}
					>
						{#if modelsImportInProgress}
							<Spinner className="size-3" />
						{/if}
						<div class=" self-center mr-2 font-medium line-clamp-1">
							{$i18n.t('Import Presets')}
						</div>

						<div class=" self-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-3.5 h-3.5"
							>
								<path
									fill-rule="evenodd"
									d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</button>

					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
						on:click={async () => {
							downloadModels(models);
						}}
					>
						<div class=" self-center mr-2 font-medium line-clamp-1">
							{$i18n.t('Export Presets')} ({models.length})
						</div>

						<div class=" self-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-3.5 h-3.5"
							>
								<path
									fill-rule="evenodd"
									d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</button>
				</div>
			</div>
		{/if}
	{:else}
		<ModelEditor
			edit
			model={models.find((m) => m.id === selectedModelId)}
			preset={false}
			onSubmit={(model) => {
				console.log(model);
				upsertModelHandler(model);
				selectedModelId = null;
			}}
			onBack={() => {
				selectedModelId = null;
			}}
		/>
	{/if}
{:else}
	<div class=" h-full w-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
