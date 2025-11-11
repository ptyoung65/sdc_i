<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { getContext, onDestroy, onMount, tick } from 'svelte';
	const i18n: Writable<i18nType> = getContext('i18n');

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { get, type Unsubscriber, type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import {
		chatId,
		chats,
		config,
		type Model,
		models,
		tags as allTags,
		settings,
		showSidebar,
		WEBUI_NAME,
		banners,
		user,
		socket,
		showControls,
		showCallOverlay,
		currentChatPage,
		temporaryChatEnabled,
		mobile,
		showOverview,
		chatTitle,
		showArtifacts,
		tools,
		toolServers,
		functions,
		selectedFolder,
		pinnedChats,
		showEmbeds,
		modelType
	} from '$lib/stores';
	import {
		convertMessagesToHistory,
		copyToClipboard,
		getMessageContentParts,
		createMessagesList,
		getPromptVariables,
		processDetails,
		removeAllDetails
	} from '$lib/utils';

	import {
		createNewChat,
		getAllTags,
		getChatById,
		getChatList,
		getPinnedChatList,
		getTagsById,
		updateChatById,
		updateChatFolderIdById
	} from '$lib/apis/chats';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { processWeb, processWebSearch, processYoutubeVideo } from '$lib/apis/retrieval';
	import { getAndUpdateUserLocation, getUserSettings } from '$lib/apis/users';
	import {
		chatCompleted,
		generateQueries,
		chatAction,
		generateMoACompletion,
		stopTask,
		getTaskIdsByChatId,
		getModels
	} from '$lib/apis';
	import { getTools } from '$lib/apis/tools';
	import { uploadFile } from '$lib/apis/files';
	import { addFileToKnowledgeById } from '$lib/apis/knowledge';
	import { createOpenAITextStream } from '$lib/apis/streaming';
	import { vectorizeDocument, searchSimilarDocuments, batchVectorizeDocuments } from '$lib/apis/vectorization';

	import { fade } from 'svelte/transition';

	import Banner from '../common/Banner.svelte';
	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/chat/Navbar.svelte';
	import EventConfirmDialog from '../common/ConfirmDialog.svelte';
	import Placeholder from './Placeholder.svelte';
	import NotificationToast from '../NotificationToast.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import EdmIntegration from './EdmIntegration.svelte';
	import EdmFileListModal from './EdmFileListModal.svelte';
	import EdmDocumentArea from './EdmDocumentArea.svelte';
	import RightSidebar, { selectedCategories, getDisplayCategoriesFromIds, DISPLAY_CATEGORIES } from '../layout/RightSidebar.svelte';
	import { getFunctions } from '$lib/apis/functions';
	import Image from '../common/Image.svelte';
	import { updateFolderById } from '$lib/apis/folders';
	import { getEdmFileList } from '$lib/apis/edm';
	import { convertN8nDocsToEdmFormat } from '$lib/apis/n8n';

	export let chatIdProp = '';

	let loading = true;

	const eventTarget = new EventTarget();

	let messageInput;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	// 🔄 멀티턴 관리 (해제됨)
	// const MAX_TURNS = 10; // 최대 턴 수 (사용자 메시지 + AI 응답 = 1턴)
	// let showMultiTurnModal = false; // 멀티턴 초과 팝업 표시 여부

	let navbarElement;

	let showEventConfirmation = false;
	let eventConfirmationTitle = '';
	let eventConfirmationMessage = '';
	let eventConfirmationInput = false;
	let eventConfirmationInputPlaceholder = '';
	let eventConfirmationInputValue = '';
	let eventCallback = null;

	let chatIdUnsubscriber: Unsubscriber | undefined;

	let selectedModels = [''];
	let atSelectedModel: Model | undefined;
	let selectedModelIds = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	// 카테고리 선택 시 자동 모델 선택 및 ModelSelector disabled 상태
	let isModelSelectorDisabled = false;

	// 선택된 카테고리 ID를 표시용 카테고리로 변환
	$: displayCategoriesForUI = getDisplayCategoriesFromIds($selectedCategories);

	// selectedCategories 변경 시 자동으로 모델 선택
	$: {
		if ($selectedCategories && $selectedCategories.length > 0 && $models && $models.length > 0) {
			const hasEdm = $selectedCategories.includes('edm');
			const hasDaesawoo = $selectedCategories.some(cat =>
				['guide', 'helpdesk', 'dictionary', 'etc'].includes(cat)
			);

			if (hasEdm) {
				// EDM 문서활용 선택 시 모델 고정 및 비활성화
				const availableModels = $models || [];

				// 1순위: edm_search_pipe 모델 찾기 (필수!)
				let edmModel = availableModels.find(m =>
					m.id === 'edm_search_pipe' || m.id?.includes('edm_search')
				);

				// 2순위: edm_search_pipe가 없으면 에러 (다른 모델 사용 금지)
				if (!edmModel && availableModels.length > 0) {
					console.error('❌ edm_search_pipe 모델을 찾을 수 없습니다!');
					toast.error('❌ EDM Search Pipeline을 활성화해주세요.');
					edmModel = null;
				}

				if (edmModel) {
					// 모델 고정 및 선택기 비활성화 (일반 사용자만 비활성화, 관리자는 활성화 유지)
					if (selectedModels[0] !== edmModel.id) {
						selectedModels = [edmModel.id];
					}
					isModelSelectorDisabled = $user?.role === 'user';

					console.log('✅ [EDM Filter] EDM 문서활용 활성화 - 모델 고정 및 비활성화', {
						timestamp: new Date().toISOString(),
						selectedCategories: $selectedCategories,
						fixedModel: edmModel.id,
						modelName: edmModel.name,
						isDisabled: true,
						filterType: 'edm_search_pipe (Filter - auto-execute)'
					});
				} else {
					// 모델이 없으면 경고
					toast.error('❌ 사용 가능한 모델이 없습니다.');
					isModelSelectorDisabled = false;
				}
			} else if (hasDaesawoo) {
				// 대사우 Assistant 선택 → daesawoo 파이프라인 자동 선택
				const daesawooModel = $models.find(m =>
					m.id?.includes('daesawoo') || m.name?.includes('daesawoo')
				);

				if (!daesawooModel) {
					toast.error('❌ daesawoo 파이프라인을 찾을 수 없습니다. 파이프라인을 등록해주세요.');
					console.error('❌ daesawoo 파이프라인이 등록되지 않았습니다.');
					isModelSelectorDisabled = false;
				} else if (selectedModels[0] !== daesawooModel.id) {
					selectedModels = [daesawooModel.id];
					isModelSelectorDisabled = $user?.role === 'user';
					console.log('✅ 대사우 Assistant → daesawoo 파이프라인 자동 선택:', daesawooModel.name);
				}
			} else {
				isModelSelectorDisabled = false;
			}
		} else {
			// 카테고리가 선택되지 않으면 기본 모델로 복원
			isModelSelectorDisabled = false;

			// 기본 모델로 자동 전환 (대사우 Assistant - internal만 사용)
			if ($modelType === 'internal') {
				const defaultModelId = getDefaultInternalModelId();
				if (selectedModels[0] !== defaultModelId) {
					selectedModels = [defaultModelId];
					console.log('✅ [카테고리 해제] 내부 기본 모델로 복원:', defaultModelId);
				}
			}
			// External 모델 사용 안함 - 주석 처리
			// else if ($modelType === 'external') {
			// 	const defaultModelId = getDefaultExternalModelId();
			// 	if (selectedModels[0] !== defaultModelId) {
			// 		selectedModels = [defaultModelId];
			// 		console.log('✅ [카테고리 해제] 외부 기본 모델로 복원:', defaultModelId);
			// 	}
			// }
		}
	}

	let selectedToolIds = [];
	let selectedFilterIds = [];
	let imageGenerationEnabled = false;
	let webSearchEnabled = false;
	let codeInterpreterEnabled = false;

	let showCommands = false;

	let generating = false;
	let generationController = null;

	let chat = null;
	let tags = [];

	// Model type selection: 'internal' or 'external' (now using store)
	let showSecurityWarning = false;
	let pendingModelType = null;

	// 모델 리스트 관리 (General.svelte와 동일한 로직)
	let allModels = [];
	let internalModels = [];
	let externalModels = [];

	// Default models from PostgreSQL config (loaded in onMount)
	let defaultInternalModel = '';
	let defaultExternalModel = '';
	let defaultModelsLoaded = false;

	// 모델 타입 판단 함수 (General.svelte와 동일)
	const getModelType = (model) => {
		console.log('[getModelType] Checking model:', model.id, 'info.meta.model_type:', model?.info?.meta?.model_type);

		// 1. info.meta.model_type이 있으면 그것을 사용 (API 응답 구조)
		if (model?.info?.meta?.model_type) {
			console.log(`[getModelType] ${model.id} → ${model.info.meta.model_type} (from info.meta)`);
			return model.info.meta.model_type;
		}

		// 2. meta.model_type이 있으면 그것을 사용 (폴백)
		if (model?.meta?.model_type) {
			console.log(`[getModelType] ${model.id} → ${model.meta.model_type} (from meta)`);
			return model.meta.model_type;
		}

		// 3. ID 패턴으로 판단
		const modelId = model?.id || '';
		console.log(`[getModelType] ${model.id} → pattern matching...`);

		// 내부 모델 패턴: qwen, ollama, 또는 external_llm이 없는 것
		const internalPatterns = [
			/^qwen/i,
			/^ollama/i,
			/^llama/i,
			/^mistral/i,
			/^gemma/i
		];

		// 외부 모델 패턴: external_llm, gpt, anthropic 등
		const externalPatterns = [
			/^external_llm/i,
			/^gpt-/i,
			/^claude/i,
			/^anthropic/i
		];

		// 외부 패턴에 매칭되면 external
		if (externalPatterns.some(pattern => pattern.test(modelId))) {
			return 'external';
		}

		// 내부 패턴에 매칭되면 internal
		if (internalPatterns.some(pattern => pattern.test(modelId))) {
			return 'internal';
		}

		// 기본값: external
		return 'external';
	};

	// 모델 목록 로드 (daesawoo 파이프라인만 찾음)
	const loadModels = async () => {
		try {
			// daesawoo 파이프라인만 필요하므로 최소한의 모델만 로딩
			allModels = await getModels(localStorage.token, null, false, true);
			console.log('[loadModels] Loaded models:', allModels.length, 'total');

			// Update the global $models store for ModelSelector component
			models.set(allModels);

			// 대사우 Assistant만 사용 - external 모델 필터링 주석 처리
			internalModels = allModels.filter(m => getModelType(m) === 'internal');
			// externalModels = allModels.filter(m => getModelType(m) === 'external');
			externalModels = []; // 외부 모델 사용 안함
			console.log('[loadModels] Internal models:', internalModels.length, ', External models 사용 안함');
		} catch (error) {
			console.error('모델 목록 로드 실패:', error);
			toast.error('모델 목록을 불러오는데 실패했습니다');
		}
	};

	// 기본 모델 ID (관리자 설정에서 지정 - PostgreSQL $config 사용)
	const getDefaultInternalModelId = () => {
		// Wait for database load to complete
		if (!defaultModelsLoaded) {
			console.warn('⏳ [getDefaultInternalModelId] 기본 모델 로드 중...');
			return '';
		}

		// Return value from config store (updated in onMount from database)
		const defaultModel = $config?.default_internal_model || '';
		console.log('[getDefaultInternalModelId] Returning:', defaultModel);
		return defaultModel;
	};

	// 대사우 Assistant만 사용 - external 모델 사용 안함
	// const getDefaultExternalModelId = () => {
	// 	// Wait for database load to complete
	// 	if (!defaultModelsLoaded) {
	// 		console.warn('⏳ [getDefaultExternalModelId] 기본 모델 로드 중...');
	// 		return '';
	// 	}

	// 	// Return value from config store (updated in onMount from database)
	// 	const defaultModel = $config?.default_external_model || '';
	// 	console.log('[getDefaultExternalModelId] Returning:', defaultModel);
	// 	return defaultModel;
	// };

	// Category boxes for internal model
	const categories = [
		{
			id: 'report',
			name: '보고서 초안 작성',
			description: '',
			samples: [
				'프로젝트 보고서 포맷을 만들어 줘',
				'디스플레이 기술 트렌드를 정리해 줘'
			]
		},
		{
			id: 'edm',
			name: 'EDM 문서활용',
			collection_name: 'edm-knowledge',
			description: '',
			samples: [
				'최근 사용한 문서를 요약해서 보여 줘',
				'지난 분기 생산 효율 회의록 찾아 줘'
			]
		},
		{
			id: 'guide',
			name: '대사우 Assistant [사규]',
			description: '사규',
			samples: [
				'육아휴직 신청 방법 알려 줘',
				'연간 패밀리넷 사용 가능 금액 알려 줘'
			]
		},
		{
			id: 'helpdesk',
			name: '대사우 Assistant [IT Help Desk]',
			description: 'IT Help Desk',
			samples: [
				'Knox 비밀번호 초기화 방법 알려 줘',
				'Wave 운영팀 내선 번호 알려 줘'
			]
		},
		{
			id: 'code',
			name: 'Code 개발 지원',
			description: '',
			samples: [
				'Python으로 엑셀을 읽는 코드 만들어 줘',
				'SQL 쿼리 중복데이터 제거하는 방법'
			]
		},
		{
			id: 'search',
			name: '외부정보검색',
			description: '',
			samples: [
				'삼성 디스플레이 관련 최근 뉴스 보여 줘',
				'AI 기반 업무혁신 사례 찾아 줘'
			]
		}
	];

	// selectedCategories는 RightSidebar.svelte에서 import한 store 사용
	let showEdmFileListModal = false; // EDM 파일리스트 팝업 표시 여부
	let edmSearchQuery = ''; // EDM 검색 쿼리
	let edmFileList: any[] = []; // EDM 파일 리스트

	// EDM 문서 활용 영역 상태
	let showEdmDocumentArea = false; // EDM 문서 활용 영역 표시 여부
	let edmDocumentData = null; // EDM 문서 검색 결과 데이터

	// EDM 피드백 관련 상태
	let showEdmFeedbackModal = false; // EDM 피드백 모달 표시 여부
	let edmFeedbackType = ''; // thumbs-up 또는 thumbs-down
	let edmFeedbackReason = ''; // 불만족 이유
	let edmFeedbackDetail = ''; // 상세 설명
	let currentEdmMessageId = ''; // 피드백 대상 메시지 ID

	// EDM 문서 목록 및 뷰어 관련 상태
	let edmDocumentViewerModal = false; // 문서 뷰어 모달 표시 여부
	let selectedDocument = null; // 선택된 문서
	let documentContent = ''; // 문서 내용
	let isLoadingDocument = false; // 문서 로딩 중
	let isProcessingKnowledge = false; // 지식화 처리 중
	// Function to handle model type change
	const handleModelTypeChange = (newType) => {
		console.log('[Chat] handleModelTypeChange called, newType:', newType);

		// If switching to external model, show security warning
		if (newType === 'external' && $modelType !== 'external') {
			pendingModelType = newType;
			showSecurityWarning = true;
		} else if (newType === 'internal' && $modelType !== 'internal') {
			// Direct switch to internal model
			modelType.set(newType);
			console.log('[Chat] Switched to internal model');

			// 내부 기본 모델로 자동 변경
			const defaultModelId = getDefaultInternalModelId();
			if (defaultModelId && selectedModels[0] !== defaultModelId) {
				selectedModels = [defaultModelId];
				console.log('✅ [내부모델 버튼] 내부 기본 모델로 자동 변경:', defaultModelId);
			}
		}
	};

	// Function to confirm external model switch
	const confirmExternalModelSwitch = async () => {
		console.log('[Chat] confirmExternalModelSwitch called');

		// Switch model type
		modelType.set(pendingModelType);
		console.log('[Chat] modelType set to:', pendingModelType);
		showSecurityWarning = false;
		pendingModelType = null;

		// 외부 기본 모델로 자동 변경
		const defaultModelId = getDefaultExternalModelId();
		if (defaultModelId && selectedModels[0] !== defaultModelId) {
			selectedModels = [defaultModelId];
			console.log('✅ [외부모델 버튼] 외부 기본 모델로 자동 변경:', defaultModelId);
		}

		// External model 사용 시 새 채팅 초기화
		// initNewChat을 호출하지만 temporaryChatEnabled가 true로 설정되지 않도록 보장
		console.log('[Chat] Initializing new chat for external model');
		await initNewChat();

		// temporaryChatEnabled를 명시적으로 false로 설정하여 히스토리 저장 보장
		// External 모델도 일반 모델처럼 히스토리에 저장되어야 함
		await temporaryChatEnabled.set(false);
		console.log('[Chat] temporaryChatEnabled set to false for history saving');
	};

	// Function to cancel external model switch
	const cancelExternalModelSwitch = () => {
		showSecurityWarning = false;
		pendingModelType = null;
	};

	// Upload multiple files
	const uploadFiles = async (token: string, files: File[]) => {
		const results = [];
		for (const file of files) {
			try {
				const result = await uploadFile(token, file);
				results.push(result);
			} catch (error) {
				console.error(`Failed to upload file ${file.name}:`, error);
				throw error;
			}
		}
		return results;
	};

	// Update selected models when model type changes
	// Only update after database default models are loaded
	$: if (defaultModelsLoaded && $modelType === 'internal') {
		const defaultModel = getDefaultInternalModelId();
		if (defaultModel) {
			selectedModels = [defaultModel];
			console.log('[Reactive] Applied internal default model:', defaultModel);
		}
	} else if (defaultModelsLoaded && $modelType === 'external') {
		const defaultModel = getDefaultExternalModelId();
		if (defaultModel) {
			selectedModels = [defaultModel];
			console.log('[Reactive] Applied external default model:', defaultModel);
		}
	}

	// 사용자 롤일 때 모델 선택 드롭다운 비활성화
	$: if ($user?.role === 'user') {
		isModelSelectorDisabled = true;
		console.log('[Reactive] User role detected - model selector disabled');
	} else {
		// 관리자는 EDM/대사우 필터가 활성화되지 않은 경우에만 활성화
		// EDM/대사우 필터 활성화 시 비활성화는 각 필터 핸들러에서 처리
		const hasEdm = $selectedCategories && $selectedCategories.includes('edm');
		const hasDaesawoo = $selectedCategories && $selectedCategories.some(cat =>
			['guide', 'helpdesk', 'dictionary', 'etc'].includes(cat)
		);

		if (!hasEdm && !hasDaesawoo) {
			isModelSelectorDisabled = false;
			console.log('[Reactive] Admin role detected - model selector enabled');
		}
	}

	let history = {
		messages: {},
		currentId: null
	};

	let taskIds = null;

	// Chat Input
	let prompt = '';
	let chatFiles = [];
	let files = [];
	let params = {};

	$: if (chatIdProp) {
		navigateHandler();
	}

	const navigateHandler = async () => {
		loading = true;

		prompt = '';
		messageInput?.setText('');

		files = [];
		selectedToolIds = [];
		selectedFilterIds = [];
		webSearchEnabled = false;
		imageGenerationEnabled = false;

		const storageChatInput = sessionStorage.getItem(
			`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`
		);

		if (chatIdProp && (await loadChat())) {
			await tick();
			loading = false;
			window.setTimeout(() => scrollToBottom(), 0);

			await tick();

			if (storageChatInput) {
				try {
					const input = JSON.parse(storageChatInput);

					if (!$temporaryChatEnabled) {
						messageInput?.setText(input.prompt);
						files = input.files;
						selectedToolIds = input.selectedToolIds;
						selectedFilterIds = input.selectedFilterIds;
						webSearchEnabled = input.webSearchEnabled;
						imageGenerationEnabled = input.imageGenerationEnabled;
						codeInterpreterEnabled = input.codeInterpreterEnabled;
					}
				} catch (e) {}
			}

			const chatInput = document.getElementById('chat-input');
			chatInput?.focus();
		} else {
			await goto('/');
		}
	};

	const onSelect = async (e) => {
		const { type, data } = e;

		if (type === 'prompt') {
			// Handle prompt selection
			messageInput?.setText(data, async () => {
				if (!($settings?.insertSuggestionPrompt ?? false)) {
					await tick();
					submitPrompt(prompt);
				}
			});
		}
	};

	$: if (selectedModels && chatIdProp !== '') {
		saveSessionSelectedModels();
	}

	const saveSessionSelectedModels = () => {
		const selectedModelsString = JSON.stringify(selectedModels);
		if (
			selectedModels.length === 0 ||
			(selectedModels.length === 1 && selectedModels[0] === '') ||
			sessionStorage.selectedModels === selectedModelsString
		) {
			return;
		}
		sessionStorage.selectedModels = selectedModelsString;
		console.log('saveSessionSelectedModels', selectedModels, sessionStorage.selectedModels);
	};

	let oldSelectedModelIds = [''];
	$: if (JSON.stringify(selectedModelIds) !== JSON.stringify(oldSelectedModelIds)) {
		onSelectedModelIdsChange();
	}

	const onSelectedModelIdsChange = () => {
		if (oldSelectedModelIds.filter((id) => id).length > 0) {
			resetInput();
		}
		oldSelectedModelIds = selectedModelIds;
	};

	const resetInput = () => {
		selectedToolIds = [];
		selectedFilterIds = [];
		webSearchEnabled = false;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;

		setDefaults();
	};

	const setDefaults = async () => {
		if (!$tools) {
			tools.set(await getTools(localStorage.token));
		}
		if (!$functions) {
			functions.set(await getFunctions(localStorage.token));
		}
		if (selectedModels.length !== 1 && !atSelectedModel) {
			return;
		}

		const model = atSelectedModel ?? $models.find((m) => m.id === selectedModels[0]);
		if (model) {
			// Set Default Tools
			if (model?.info?.meta?.toolIds) {
				selectedToolIds = [
					...new Set(
						[...(model?.info?.meta?.toolIds ?? [])].filter((id) => $tools.find((t) => t.id === id))
					)
				];
			}

			// Set Default Filters (Toggleable only)
			if (model?.info?.meta?.defaultFilterIds) {
				selectedFilterIds = model.info.meta.defaultFilterIds.filter((id) =>
					model?.filters?.find((f) => f.id === id)
				);
			}

			// Set Default Features
			if (model?.info?.meta?.defaultFeatureIds) {
				if (model.info?.meta?.capabilities?.['image_generation']) {
					imageGenerationEnabled = model.info.meta.defaultFeatureIds.includes('image_generation');
				}

				if (model.info?.meta?.capabilities?.['web_search']) {
					webSearchEnabled = model.info.meta.defaultFeatureIds.includes('web_search');
				}

				if (model.info?.meta?.capabilities?.['code_interpreter']) {
					codeInterpreterEnabled = model.info.meta.defaultFeatureIds.includes('code_interpreter');
				}
			}
		}
	};

	const showMessage = async (message, ignoreSettings = false) => {
		await tick();

		const _chatId = JSON.parse(JSON.stringify($chatId));
		let _messageId = JSON.parse(JSON.stringify(message.id));

		let messageChildrenIds = [];
		if (_messageId === null) {
			messageChildrenIds = Object.keys(history.messages).filter(
				(id) => history.messages[id].parentId === null
			);
		} else {
			messageChildrenIds = history.messages[_messageId].childrenIds;
		}

		while (messageChildrenIds.length !== 0) {
			_messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[_messageId].childrenIds;
		}

		history.currentId = _messageId;

		await tick();
		await tick();
		await tick();

		if (($settings?.scrollOnBranchChange ?? true) || ignoreSettings) {
			const messageElement = document.getElementById(`message-${message.id}`);
			if (messageElement) {
				messageElement.scrollIntoView({ behavior: 'smooth' });
			}
		}

		await tick();
		saveChatHandler(_chatId, history);
	};

	const chatEventHandler = async (event, cb) => {
		console.log(event);

		if (event.chat_id === $chatId) {
			await tick();
			let message = history.messages[event.message_id];

			if (message) {
				const type = event?.data?.type ?? null;
				const data = event?.data?.data ?? null;

				if (type === 'status') {
					if (message?.statusHistory) {
						message.statusHistory.push(data);
					} else {
						message.statusHistory = [data];
					}
				} else if (type === 'chat:completion') {
					chatCompletionEventHandler(data, message, event.chat_id);
				} else if (type === 'chat:tasks:cancel') {
					taskIds = null;
					const responseMessage = history.messages[history.currentId];
					// Set all response messages to done
					for (const messageId of history.messages[responseMessage.parentId].childrenIds) {
						history.messages[messageId].done = true;
					}
				} else if (type === 'chat:message:delta' || type === 'message') {
					message.content += data.content;
				} else if (type === 'chat:message' || type === 'replace') {
					message.content = data.content;
				} else if (type === 'chat:message:files' || type === 'files') {
					message.files = data.files;
				} else if (type === 'chat:message:embeds' || type === 'embeds') {
					message.embeds = data.embeds;
				} else if (type === 'chat:message:error') {
					message.error = data.error;
				} else if (type === 'chat:message:follow_ups') {
					message.followUps = data.follow_ups;

					if (autoScroll) {
						scrollToBottom('smooth');
					}
				} else if (type === 'chat:title') {
					chatTitle.set(data);
					currentChatPage.set(1);
					await chats.set(await getChatList(localStorage.token, $currentChatPage));
				} else if (type === 'chat:tags') {
					chat = await getChatById(localStorage.token, $chatId);
					allTags.set(await getAllTags(localStorage.token));
				} else if (type === 'source' || type === 'citation') {
					if (data?.type === 'code_execution') {
						// Code execution; update existing code execution by ID, or add new one.
						if (!message?.code_executions) {
							message.code_executions = [];
						}

						const existingCodeExecutionIndex = message.code_executions.findIndex(
							(execution) => execution.id === data.id
						);

						if (existingCodeExecutionIndex !== -1) {
							message.code_executions[existingCodeExecutionIndex] = data;
						} else {
							message.code_executions.push(data);
						}

						message.code_executions = message.code_executions;
					} else {
						// Regular source.
						if (message?.sources) {
							message.sources.push(data);
						} else {
							message.sources = [data];
						}
					}
				} else if (type === 'notification') {
					const toastType = data?.type ?? 'info';
					const toastContent = data?.content ?? '';

					if (toastType === 'success') {
						toast.success(toastContent);
					} else if (toastType === 'error') {
						toast.error(toastContent);
					} else if (toastType === 'warning') {
						toast.warning(toastContent);
					} else {
						toast.info(toastContent);
					}
				} else if (type === 'confirmation') {
					eventCallback = cb;

					eventConfirmationInput = false;
					showEventConfirmation = true;

					eventConfirmationTitle = data.title;
					eventConfirmationMessage = data.message;
				} else if (type === 'execute') {
					eventCallback = cb;

					try {
						// Use Function constructor to evaluate code in a safer way
						const asyncFunction = new Function(`return (async () => { ${data.code} })()`);
						const result = await asyncFunction(); // Await the result of the async function

						if (cb) {
							cb(result);
						}
					} catch (error) {
						console.error('Error executing code:', error);
					}
				} else if (type === 'input') {
					eventCallback = cb;

					eventConfirmationInput = true;
					showEventConfirmation = true;

					eventConfirmationTitle = data.title;
					eventConfirmationMessage = data.message;
					eventConfirmationInputPlaceholder = data.placeholder;
					eventConfirmationInputValue = data?.value ?? '';
				} else if (type === 'event') {
					// 📤 파이프에서 전송된 커스텀 이벤트 처리
					const eventType = data?.event?.type ?? null;
					const eventDetail = data?.event?.detail ?? null;

					if (eventType === 'openEdmFileList') {
						// 📂 EDM 파일 리스트를 메시지 메타데이터에 저장
						console.log('[Chat] 📂 openEdmFileList 이벤트 수신 from pipe:', {
							messageId: message.id,
							filesCount: eventDetail?.files?.length ?? 0,
							files: eventDetail?.files
						});

						// 메시지에 edmFileList 메타데이터 저장
						if (!message.info) {
							message.info = {};
						}
						message.info.edmFileList = eventDetail?.files || [];
						message.isEdmResult = true;  // EDM 결과 플래그 설정 (버튼 렌더링용)

						console.log('[Chat] ✅ edmFileList saved to message.info:', {
							messageId: message.id,
							savedFiles: message.info.edmFileList.length
						});
					} else {
						console.log('[Chat] ⚠️ Unknown event type:', eventType, eventDetail);
					}
				} else {
					console.log('Unknown message type', data);
				}

				history.messages[event.message_id] = message;
			}
		}
	};

	const onMessageHandler = async (event: {
		origin: string;
		data: { type: string; text: string };
	}) => {
		if (event.origin !== window.origin) {
			return;
		}

		if (event.data.type === 'action:submit') {
			console.debug(event.data.text);

			if (prompt !== '') {
				await tick();
				submitPrompt(prompt);
			}
		}

		// Replace with your iframe's origin
		if (event.data.type === 'input:prompt') {
			console.debug(event.data.text);

			const inputElement = document.getElementById('chat-input');

			if (inputElement) {
				messageInput?.setText(event.data.text);
				inputElement.focus();
			}
		}

		if (event.data.type === 'input:prompt:submit') {
			console.debug(event.data.text);

			if (event.data.text !== '') {
				await tick();
				submitPrompt(event.data.text);
			}
		}
	};

	const savedModelIds = async () => {
		if (
			$selectedFolder &&
			selectedModels.filter((modelId) => modelId !== '').length > 0 &&
			JSON.stringify($selectedFolder?.data?.model_ids) !== JSON.stringify(selectedModels)
		) {
			const res = await updateFolderById(localStorage.token, $selectedFolder.id, {
				data: {
					model_ids: selectedModels
				}
			});
		}
	};

	$: if (selectedModels !== null) {
		savedModelIds();
	}

	let pageSubscribe = null;
	let showControlsSubscribe = null;
	let selectedFolderSubscribe = null;

	onMount(async () => {
		loading = true;
		console.log('[DEBUG-CHAT] onMount STARTED');

		// Initialize model type and sidebars
		modelType.set('internal');

		// Load all models for dropdown (General.svelte와 동일한 로직)
		await loadModels();

		// 기본 모델 설정을 PostgreSQL에서 로드 (General.svelte와 동일한 패턴)
	console.log('[DEBUG-CHAT] About to load default models from DB');
	if (localStorage.token) {
		try {
			// Use exportConfig to get the full config including default models
			console.log('[DEBUG-CHAT] localStorage.token exists, importing exportConfig');
			const { exportConfig } = await import('$lib/apis/configs');
			console.log('[DEBUG-CHAT] Calling exportConfig()');
			const fullConfig = await exportConfig(localStorage.token);

			console.log('[DEBUG-CHAT] Loaded full config:', fullConfig);

			if (fullConfig) {
				defaultInternalModel = fullConfig.default_internal_model || '';
				defaultExternalModel = fullConfig.default_external_model || '';

				// Update config store with loaded values from database
				config.set({
					...$config,
					default_internal_model: defaultInternalModel,
					default_external_model: defaultExternalModel
				});

				console.log('[onMount] Loaded default models:', {
					internal: defaultInternalModel,
					external: defaultExternalModel,
					userRole: $user?.role
				});

				// Show toast to admin if default models are not set in database
				if ($user?.role === 'admin') {
					if (!defaultInternalModel) {
						toast.error('내부 기본 모델이 설정되지 않았습니다. 관리자 설정에서 지정해주세요.');
					}
					if (!defaultExternalModel) {
						toast.error('외부 기본 모델이 설정되지 않았습니다. 관리자 설정에서 지정해주세요.');
					}
				}
			}
		} catch (error) {
			console.error('기본 모델 설정 로드 실패:', error);
			// 관리자만 오류 토스트 표시
			if ($user?.role === 'admin') {
				toast.error('기본 모델 설정을 불러오는데 실패했습니다. 관리자 설정을 확인해주세요.');
			}
		}
	} else {
		console.log('[onMount] No token found, skipping config load');
	}

	// Mark default models as loaded (either successfully loaded or skipped)
	defaultModelsLoaded = true;

		// 로드한 기본 모델을 selectedModels에 적용
		if ($modelType === 'internal' && defaultInternalModel) {
			selectedModels = [defaultInternalModel];
			console.log('[onMount] Applied internal model to selectedModels:', selectedModels);
		} else if ($modelType === 'external' && defaultExternalModel) {
			selectedModels = [defaultExternalModel];
			console.log('[onMount] Applied external model to selectedModels:', selectedModels);
		}

		// Initial setup for right sidebar
		await tick();

		window.addEventListener('message', onMessageHandler);
		$socket?.on('events', chatEventHandler);

		// EDM 지식화 이벤트 리스너
		const handleEdmKnowledgeRequest = async (event: CustomEvent) => {
			const { files, message } = event.detail;
			console.log('🔵 [Chat] EDM 지식화 이벤트 수신:', files);

			// 파이프라인에 파일 정보 전달
			const userMessage = {
				role: 'user',
				content: `EDM 파일 ${files.length}개를 지식화합니다.`,
				edm_files: files
			};

			// 기존 submitPrompt 함수를 사용하여 메시지 전송
			await submitPrompt('', '', { edmFiles: files });
		};

		window.addEventListener('edm-knowledge-request', handleEdmKnowledgeRequest);


		// Expose submitPrompt for E2E testing
		if (typeof window !== 'undefined') {
			window.__chatSubmitPrompt = submitPrompt;
			console.log('🧪 [Test Helper] submitPrompt exposed on window.__chatSubmitPrompt');
		}

		pageSubscribe = page.subscribe(async (p) => {
			if (p.url.pathname === '/') {
				await tick();
				initNewChat();
			}
		});

		const storageChatInput = sessionStorage.getItem(
			`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`
		);

		if (!chatIdProp) {
			loading = false;
			await tick();
		}

		if (storageChatInput) {
			prompt = '';
			messageInput?.setText('');

			files = [];
			selectedToolIds = [];
			selectedFilterIds = [];
			webSearchEnabled = false;
			imageGenerationEnabled = false;
			codeInterpreterEnabled = false;

			try {
				const input = JSON.parse(storageChatInput);

				if (!$temporaryChatEnabled) {
					messageInput?.setText(input.prompt);
					files = input.files;
					selectedToolIds = input.selectedToolIds;
					selectedFilterIds = input.selectedFilterIds;
					webSearchEnabled = input.webSearchEnabled;
					imageGenerationEnabled = input.imageGenerationEnabled;
					codeInterpreterEnabled = input.codeInterpreterEnabled;
				}
			} catch (e) {}
		}

		showControlsSubscribe = showControls.subscribe(async (value) => {
			if (!value) {
				showCallOverlay.set(false);
				showOverview.set(false);
				showArtifacts.set(false);
				showEmbeds.set(false);
			}
		});

		selectedFolderSubscribe = selectedFolder.subscribe(async (folder) => {
			if (
				folder?.data?.model_ids &&
				JSON.stringify(selectedModels) !== JSON.stringify(folder.data.model_ids)
			) {
				selectedModels = folder.data.model_ids;

				console.log('Set selectedModels from folder data:', selectedModels);
			}
		});

		const chatInput = document.getElementById('chat-input');
		chatInput?.focus();
	});

	onDestroy(() => {
		try {
			pageSubscribe();
			showControlsSubscribe();
			selectedFolderSubscribe();
			chatIdUnsubscriber?.();
			window.removeEventListener('message', onMessageHandler);
			$socket?.off('events', chatEventHandler);
		} catch (e) {
			console.error(e);
		}
	});

	// File upload functions

	const uploadGoogleDriveFile = async (fileData) => {
		console.log('Starting uploadGoogleDriveFile with:', {
			id: fileData.id,
			name: fileData.name,
			url: fileData.url,
			headers: {
				Authorization: `Bearer ${token}`
			}
		});

		// Validate input
		if (!fileData?.id || !fileData?.name || !fileData?.url || !fileData?.headers?.Authorization) {
			throw new Error('Invalid file data provided');
		}

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: fileData.url,
			name: fileData.name,
			collection_name: '',
			status: 'uploading',
			error: '',
			itemId: tempItemId,
			size: 0
		};

		try {
			files = [...files, fileItem];
			console.log('Processing web file with URL:', fileData.url);

			// Configure fetch options with proper headers
			const fetchOptions = {
				headers: {
					Authorization: fileData.headers.Authorization,
					Accept: '*/*'
				},
				method: 'GET'
			};

			// Attempt to fetch the file
			console.log('Fetching file content from Google Drive...');
			const fileResponse = await fetch(fileData.url, fetchOptions);

			if (!fileResponse.ok) {
				const errorText = await fileResponse.text();
				throw new Error(`Failed to fetch file (${fileResponse.status}): ${errorText}`);
			}

			// Get content type from response
			const contentType = fileResponse.headers.get('content-type') || 'application/octet-stream';
			console.log('Response received with content-type:', contentType);

			// Convert response to blob
			console.log('Converting response to blob...');
			const fileBlob = await fileResponse.blob();

			if (fileBlob.size === 0) {
				throw new Error('Retrieved file is empty');
			}

			console.log('Blob created:', {
				size: fileBlob.size,
				type: fileBlob.type || contentType
			});

			// Create File object with proper MIME type
			const file = new File([fileBlob], fileData.name, {
				type: fileBlob.type || contentType
			});

			console.log('File object created:', {
				name: file.name,
				size: file.size,
				type: file.type
			});

			if (file.size === 0) {
				throw new Error('Created file is empty');
			}

			// If the file is an audio file, provide the language for STT.
			let metadata = null;
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
			) {
				metadata = {
					language: $settings?.audio?.stt?.language
				};
			}

			// Upload file to server
			console.log('Uploading file to server...');
			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (!uploadedFile) {
				throw new Error('Server returned null response for file upload');
			}

			console.log('File uploaded successfully:', uploadedFile);

			// Update file item with upload results
			fileItem.status = 'uploaded';
			fileItem.file = uploadedFile;
			fileItem.id = uploadedFile.id;
			fileItem.size = file.size;
			fileItem.collection_name = uploadedFile?.meta?.collection_name;
			fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

			files = files;
			toast.success($i18n.t('File uploaded successfully'));
		} catch (e) {
			console.error('Error uploading file:', e);
			files = files.filter((f) => f.itemId !== tempItemId);
			toast.error(
				$i18n.t('Error uploading file: {{error}}', {
					error: e.message || 'Unknown error'
				})
			);
		}
	};

	const uploadWeb = async (url) => {
		console.log(url);

		const fileItem = {
			type: 'text',
			name: url,
			collection_name: '',
			status: 'uploading',
			url: url,
			error: ''
		};

		try {
			files = [...files, fileItem];
			const res = await processWeb(localStorage.token, '', url);

			if (res) {
				fileItem.status = 'uploaded';
				fileItem.collection_name = res.collection_name;
				fileItem.file = {
					...res.file,
					...fileItem.file
				};

				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(JSON.stringify(e));
		}
	};

	const uploadYoutubeTranscription = async (url) => {
		console.log(url);

		const fileItem = {
			type: 'text',
			name: url,
			collection_name: '',
			status: 'uploading',
			context: 'full',
			url: url,
			error: ''
		};

		try {
			files = [...files, fileItem];
			const res = await processYoutubeVideo(localStorage.token, url);

			if (res) {
				fileItem.status = 'uploaded';
				fileItem.collection_name = res.collection_name;
				fileItem.file = {
					...res.file,
					...fileItem.file
				};
				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(`${e}`);
		}
	};

	//////////////////////////
	// Web functions
	//////////////////////////

	const initNewChat = async () => {
		console.log('initNewChat');
		if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
			await temporaryChatEnabled.set(true);
		}

		if ($settings?.temporaryChatByDefault ?? false) {
			if ($temporaryChatEnabled === false) {
				await temporaryChatEnabled.set(true);
			} else if ($temporaryChatEnabled === null) {
				// if set to null set to false; refer to temp chat toggle click handler
				await temporaryChatEnabled.set(false);
			}
		}

		const availableModels = $models
			.filter((m) => !(m?.info?.meta?.hidden ?? false))
			.map((m) => m.id);

		if ($page.url.searchParams.get('models') || $page.url.searchParams.get('model')) {
			const urlModels = (
				$page.url.searchParams.get('models') ||
				$page.url.searchParams.get('model') ||
				''
			)?.split(',');

			if (urlModels.length === 1) {
				const m = $models.find((m) => m.id === urlModels[0]);
				if (!m) {
					const modelSelectorButton = document.getElementById('model-selector-0-button');
					if (modelSelectorButton) {
						modelSelectorButton.click();
						await tick();

						const modelSelectorInput = document.getElementById('model-search-input');
						if (modelSelectorInput) {
							modelSelectorInput.focus();
							modelSelectorInput.value = urlModels[0];
							modelSelectorInput.dispatchEvent(new Event('input'));
						}
					}
				} else {
					selectedModels = urlModels;
				}
			} else {
				selectedModels = urlModels;
			}

			selectedModels = selectedModels.filter((modelId) =>
				$models.map((m) => m.id).includes(modelId)
			);
		} else {
			if ($selectedFolder?.data?.model_ids) {
				selectedModels = $selectedFolder?.data?.model_ids;
			} else {
				if (sessionStorage.selectedModels) {
					selectedModels = JSON.parse(sessionStorage.selectedModels);
					sessionStorage.removeItem('selectedModels');
				} else {
					if ($settings?.models) {
						selectedModels = $settings?.models;
					} else if ($config?.default_models) {
						console.log($config?.default_models.split(',') ?? '');
						selectedModels = $config?.default_models.split(',');
					}
				}
			}

			selectedModels = selectedModels.filter((modelId) => availableModels.includes(modelId));
		}

		if (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === '')) {
			if (availableModels.length > 0) {
				selectedModels = [availableModels?.at(0) ?? ''];
			} else {
				selectedModels = [''];
			}
		}

		// showControls.set(false) 제거 - 최초 로딩 시 햄버거 버튼이 보이는 원인
		await showCallOverlay.set(false);
		await showOverview.set(false);
		await showArtifacts.set(false);

		if ($page.url.pathname.includes('/c/')) {
			window.history.replaceState(history.state, '', `/`);
		}

		autoScroll = true;

		resetInput();
		await chatId.set('');
		await chatTitle.set('');

		history = {
			messages: {},
			currentId: null
		};

		chatFiles = [];
		params = {};

		if ($page.url.searchParams.get('youtube')) {
			uploadYoutubeTranscription(
				`https://www.youtube.com/watch?v=${$page.url.searchParams.get('youtube')}`
			);
		}

		if ($page.url.searchParams.get('load-url')) {
			await uploadWeb($page.url.searchParams.get('load-url'));
		}

		if ($page.url.searchParams.get('web-search') === 'true') {
			webSearchEnabled = true;
		}

		if ($page.url.searchParams.get('image-generation') === 'true') {
			imageGenerationEnabled = true;
		}

		if ($page.url.searchParams.get('code-interpreter') === 'true') {
			codeInterpreterEnabled = true;
		}

		if ($page.url.searchParams.get('tools')) {
			selectedToolIds = $page.url.searchParams
				.get('tools')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id);
		} else if ($page.url.searchParams.get('tool-ids')) {
			selectedToolIds = $page.url.searchParams
				.get('tool-ids')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id);
		}

		if ($page.url.searchParams.get('call') === 'true') {
			showCallOverlay.set(true);
			showControls.set(true);
		}

		if ($page.url.searchParams.get('q')) {
			const q = $page.url.searchParams.get('q') ?? '';
			messageInput?.setText(q);

			if (q) {
				if (($page.url.searchParams.get('submit') ?? 'true') === 'true') {
					await tick();
					submitPrompt(q);
				}
			}
		}

		selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		const userSettings = await getUserSettings(localStorage.token);

		if (userSettings) {
			settings.set(userSettings.ui);
		} else {
			settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
		}

		const chatInput = document.getElementById('chat-input');
		setTimeout(() => chatInput?.focus(), 0);
	};

	const loadChat = async () => {
		chatId.set(chatIdProp);

		if ($temporaryChatEnabled) {
			temporaryChatEnabled.set(false);
		}

		chat = await getChatById(localStorage.token, $chatId).catch(async (error) => {
			await goto('/');
			return null;
		});

		if (chat) {
			tags = await getTagsById(localStorage.token, $chatId).catch(async (error) => {
				return [];
			});

			const chatContent = chat.chat;

			if (chatContent) {
				console.log(chatContent);

				selectedModels =
					(chatContent?.models ?? undefined) !== undefined
						? chatContent.models
						: [chatContent.models ?? ''];

				if (!($user?.role === 'admin' || ($user?.permissions?.chat?.multiple_models ?? true))) {
					selectedModels = selectedModels.length > 0 ? [selectedModels[0]] : [''];
				}

				oldSelectedModelIds = selectedModels;

				history =
					(chatContent?.history ?? undefined) !== undefined
						? chatContent.history
						: convertMessagesToHistory(chatContent.messages);

				chatTitle.set(chatContent.title);

				const userSettings = await getUserSettings(localStorage.token);

				if (userSettings) {
					await settings.set(userSettings.ui);
				} else {
					await settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
				}

				params = chatContent?.params ?? {};
				chatFiles = chatContent?.files ?? [];

				autoScroll = true;
				await tick();

				if (history.currentId) {
					for (const message of Object.values(history.messages)) {
						if (message.role === 'assistant') {
							message.done = true;
						}
					}
				}

				const taskRes = await getTaskIdsByChatId(localStorage.token, $chatId).catch((error) => {
					return null;
				});

				if (taskRes) {
					taskIds = taskRes.task_ids;
				}

				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const scrollToBottom = async (behavior = 'auto') => {
		await tick();
		if (messagesContainerElement) {
			messagesContainerElement.scrollTo({
				top: messagesContainerElement.scrollHeight,
				behavior
			});
		}
	};
	const chatCompletedHandler = async (chatId, modelId, responseMessageId, messages) => {
		const res = await chatCompleted(localStorage.token, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.usage ? { usage: m.usage } : {}),
				...(m.sources ? { sources: m.sources } : {})
			})),
			filter_ids: selectedFilterIds.length > 0 ? selectedFilterIds : undefined,
			model_item: $models.find((m) => m.id === modelId),
			chat_id: chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(`${error}`);
			messages.at(-1).error = { content: error };

			return null;
		});

		if (res !== null && res.messages) {
			// Update chat history with the new messages
			for (const message of res.messages) {
				if (message?.id) {
					// Add null check for message and message.id
					history.messages[message.id] = {
						...history.messages[message.id],
						...(history.messages[message.id].content !== message.content
							? { originalContent: history.messages[message.id].content }
							: {}),
						...message
					};
				}
			}
		}

		await tick();

		if ($chatId == chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, chatId, {
					models: selectedModels,
					messages: messages,
					history: history,
					params: params,
					files: chatFiles
				});

				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
			}
		}

		taskIds = null;
	};

	const chatActionHandler = async (chatId, actionId, modelId, responseMessageId, event = null) => {
		const messages = createMessagesList(history, responseMessageId);

		const res = await chatAction(localStorage.token, actionId, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.sources ? { sources: m.sources } : {})
			})),
			...(event ? { event: event } : {}),
			model_item: $models.find((m) => m.id === modelId),
			chat_id: chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(`${error}`);
			messages.at(-1).error = { content: error };
			return null;
		});

		if (res !== null && res.messages) {
			// Update chat history with the new messages
			for (const message of res.messages) {
				history.messages[message.id] = {
					...history.messages[message.id],
					...(history.messages[message.id].content !== message.content
						? { originalContent: history.messages[message.id].content }
						: {}),
					...message
				};
			}
		}

		if ($chatId == chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, chatId, {
					models: selectedModels,
					messages: messages,
					history: history,
					params: params,
					files: chatFiles
				});

				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
			}
		}
	};

	const getChatEventEmitter = async (modelId: string, chatId: string = '') => {
		return setInterval(() => {
			$socket?.emit('usage', {
				action: 'chat',
				model: modelId,
				chat_id: chatId
			});
		}, 1000);
	};

	const createMessagePair = async (userPrompt) => {
		messageInput?.setText('');
		if (selectedModels.length === 0) {
			toast.error($i18n.t('Model not selected'));
		} else {
			const modelId = selectedModels[0];
			const model = $models.filter((m) => m.id === modelId).at(0);

			const messages = createMessagesList(history, history.currentId);
			const parentMessage = messages.length !== 0 ? messages.at(-1) : null;

			const userMessageId = uuidv4();
			const responseMessageId = uuidv4();

			const userMessage = {
				id: userMessageId,
				parentId: parentMessage ? parentMessage.id : null,
				childrenIds: [responseMessageId],
				role: 'user',
				content: userPrompt ? userPrompt : `[PROMPT] ${userMessageId}`,
				timestamp: Math.floor(Date.now() / 1000)
			};

			const responseMessage = {
				id: responseMessageId,
				parentId: userMessageId,
				childrenIds: [],
				role: 'assistant',
				content: `[RESPONSE] ${responseMessageId}`,
				done: true,

				model: modelId,
				modelName: model.name ?? model.id,
				modelIdx: 0,
				timestamp: Math.floor(Date.now() / 1000)
			};

			if (parentMessage) {
				parentMessage.childrenIds.push(userMessageId);
				history.messages[parentMessage.id] = parentMessage;
			}
			history.messages[userMessageId] = userMessage;
			history.messages[responseMessageId] = responseMessage;

			history.currentId = responseMessageId;

			await tick();

			if (autoScroll) {
				scrollToBottom();
			}

			if (messages.length === 0) {
				await initChatHandler(history);
			} else {
				await saveChatHandler($chatId, history);
			}
		}
	};

	const addMessages = async ({ modelId, parentId, messages }) => {
		const model = $models.filter((m) => m.id === modelId).at(0);

		let parentMessage = history.messages[parentId];
		let currentParentId = parentMessage ? parentMessage.id : null;
		for (const message of messages) {
			let messageId = uuidv4();

			if (message.role === 'user') {
				const userMessage = {
					id: messageId,
					parentId: currentParentId,
					childrenIds: [],
					timestamp: Math.floor(Date.now() / 1000),
					...message
				};

				if (parentMessage) {
					parentMessage.childrenIds.push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = userMessage;
				parentMessage = userMessage;
				currentParentId = messageId;
			} else {
				const responseMessage = {
					id: messageId,
					parentId: currentParentId,
					childrenIds: [],
					done: true,
					model: model.id,
					modelName: model.name ?? model.id,
					modelIdx: 0,
					timestamp: Math.floor(Date.now() / 1000),
					...message
				};

				if (parentMessage) {
					parentMessage.childrenIds.push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = responseMessage;
				parentMessage = responseMessage;
				currentParentId = messageId;
			}
		}

		history.currentId = currentParentId;
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		if (messages.length === 0) {
			await initChatHandler(history);
		} else {
			await saveChatHandler($chatId, history);
		}
	};

	const chatCompletionEventHandler = async (data, message, chatId) => {
		const { id, done, choices, content, sources, selected_model_id, error, usage } = data;

		if (error) {
			await handleOpenAIError(error, message);
		}

		if (sources && !message?.sources) {
			message.sources = sources;
		}

		if (choices) {
			if (choices[0]?.message?.content) {
				// Non-stream response
				message.content += choices[0]?.message?.content;
			} else {
				// Stream response
				let value = choices[0]?.delta?.content ?? '';
				if (message.content == '' && value == '\n') {
					console.log('Empty response');
				} else {
					message.content += value;

					if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
						navigator.vibrate(5);
					}

					// Emit chat event for TTS
					const messageContentParts = getMessageContentParts(
						removeAllDetails(message.content),
						$config?.audio?.tts?.split_on ?? 'punctuation'
					);
					messageContentParts.pop();

					// dispatch only last sentence and make sure it hasn't been dispatched before
					if (
						messageContentParts.length > 0 &&
						messageContentParts[messageContentParts.length - 1] !== message.lastSentence
					) {
						message.lastSentence = messageContentParts[messageContentParts.length - 1];
						eventTarget.dispatchEvent(
							new CustomEvent('chat', {
								detail: {
									id: message.id,
									content: messageContentParts[messageContentParts.length - 1]
								}
							})
						);
					}
				}
			}
		}

		if (content) {
			// REALTIME_CHAT_SAVE is disabled
			message.content = content;

			if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
				navigator.vibrate(5);
			}

			// Emit chat event for TTS
			const messageContentParts = getMessageContentParts(
				removeAllDetails(message.content),
				$config?.audio?.tts?.split_on ?? 'punctuation'
			);
			messageContentParts.pop();

			// dispatch only last sentence and make sure it hasn't been dispatched before
			if (
				messageContentParts.length > 0 &&
				messageContentParts[messageContentParts.length - 1] !== message.lastSentence
			) {
				message.lastSentence = messageContentParts[messageContentParts.length - 1];
				eventTarget.dispatchEvent(
					new CustomEvent('chat', {
						detail: {
							id: message.id,
							content: messageContentParts[messageContentParts.length - 1]
						}
					})
				);
			}
		}

		if (selected_model_id) {
			message.selectedModelId = selected_model_id;
			message.arena = true;
		}

		if (usage) {
			message.usage = usage;
		}

		history.messages[message.id] = message;

		if (done) {
			message.done = true;

			if ($settings.responseAutoCopy) {
				copyToClipboard(message.content);
			}

			if ($settings.responseAutoPlayback && !$showCallOverlay) {
				await tick();
				document.getElementById(`speak-button-${message.id}`)?.click();
			}

			// Emit chat event for TTS
			let lastMessageContentPart =
				getMessageContentParts(
					removeAllDetails(message.content),
					$config?.audio?.tts?.split_on ?? 'punctuation'
				)?.at(-1) ?? '';
			if (lastMessageContentPart) {
				eventTarget.dispatchEvent(
					new CustomEvent('chat', {
						detail: { id: message.id, content: lastMessageContentPart }
					})
				);
			}
			eventTarget.dispatchEvent(
				new CustomEvent('chat:finish', {
					detail: {
						id: message.id,
						content: message.content
					}
				})
			);

			history.messages[message.id] = message;

			await tick();
			if (autoScroll) {
				scrollToBottom();
			}

			await chatCompletedHandler(
				chatId,
				message.model,
				message.id,
				createMessagesList(history, message.id)
			);
		}

		console.log(data);
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}
	};

	//////////////////////////
	// Chat functions
	//////////////////////////

	const submitPrompt = async (userPrompt, { _raw = false, edmFiles = null } = {}) => {
		console.log('[Chat] submitPrompt called:', userPrompt);
		console.log('[Chat] Current chatId:', $chatId);
		console.log('[Chat] temporaryChatEnabled:', $temporaryChatEnabled);
		console.log('[Chat] selectedCategories:', $selectedCategories);

		// EDM 파일 지식화 요청인 경우
		if (edmFiles && edmFiles.length > 0) {
			console.log('🔵 [Chat] EDM 파일 지식화 요청:', edmFiles);

			// edm_download_pipe_streaming 파이프라인 선택
			const edmPipeModel = $models.find(m => m.id === 'edm_download_pipe_streaming');
			if (edmPipeModel) {
				selectedModels = [edmPipeModel.id];
				console.log('✅ [Chat] EDM 다운로드 파이프라인 자동 선택:', edmPipeModel.id);
			}

			// 프롬프트 생성
			userPrompt = `EDM 파일 ${edmFiles.length}개를 지식화합니다.`;

			// 메시지 히스토리에 edm_files 추가 (파이프라인에서 사용)
			if (!window.__edmFilesForPipeline) {
				window.__edmFilesForPipeline = {};
			}
			const requestId = Date.now().toString();
			window.__edmFilesForPipeline[requestId] = edmFiles;
		}

		// 🔄 멀티턴 제한 체크 (해제됨)
		// const currentUserMessageCount = Object.values(history.messages).filter(msg => msg.role === 'user').length;
		// const nextUserMessageCount = currentUserMessageCount + 1;
		// console.log(`🔄 [멀티턴] 현재 사용자 메시지: ${currentUserMessageCount}개, 전송 후: ${nextUserMessageCount}개/${MAX_TURNS}턴 제한`);
		// console.log(`🔄 [멀티턴] 전체 메시지: ${Object.keys(history.messages).length}개`);
		// if (nextUserMessageCount > MAX_TURNS) {
		// 	console.log(`⚠️ [멀티턴] 최대 턴 수(${MAX_TURNS}) 초과 - 팝업 표시`);
		// 	showMultiTurnModal = true;
		// 	return;
		// }

		// EDM 문서활용이 선택된 경우 모델에 따라 분기
		// selectedCategories는 문자열 배열 ['edm', 'guide', ...] 형태
		const shouldUseEdm = $selectedCategories.includes('edm');

		// 대사우 Assistant가 선택된 경우 확인
		const shouldUseDaesawoo = $selectedCategories.some(cat =>
			['guide', 'helpdesk', 'dictionary', 'etc'].includes(cat)
		);

		// EDM Search 파이프가 선택되었는지 확인
		const isEdmPipeSelected = selectedModels.some(modelId => {
			const model = $models.find(m => m.id === modelId);
			return model && (
				model.id === 'edm_search_milvus' ||
				model.id === 'edm_search_pipe' ||
				model.id === 'edm_n8n_pipe' ||
				model.name?.includes('EDM Search') ||
				(model.type === 'pipe' && model.id.includes('edm'))
			);
		});

		// daesawoo 파이프가 선택되었는지 확인
		const isDaesawooPipeSelected = selectedModels.some(modelId => {
			const model = $models.find(m => m.id === modelId);
			return model && (
				model.id?.includes('daesawoo') ||
				model.name?.includes('daesawoo')
			);
		});

		if (shouldUseDaesawoo && isDaesawooPipeSelected) {
			// 대사우 Assistant 체크 + daesawoo 파이프 선택
			// → 전처리 없이 바로 daesawoo 파이프로 위임
			// → daesawoo 파이프 내부에서 LLM 호출 및 응답 처리
			console.log('🟢 [submitPrompt] 대사우 파이프 위임 (전처리 없음)', {
				timestamp: new Date().toISOString(),
				action: 'daesawoo_pipe_delegation',
				shouldUseDaesawoo: shouldUseDaesawoo,
				isDaesawooPipeSelected: isDaesawooPipeSelected,
				selectedModels: selectedModels,
				selectedCategories: $selectedCategories,
				userPrompt: userPrompt.substring(0, 100) + '...'
			});
			console.log('   선택된 모델:', selectedModels);
			// 파이프로 위임하기 위해 일반 플로우로 진행 (return 없음, 전처리 없음)
		} else if (shouldUseEdm && isEdmPipeSelected) {
			// EDM 문서활용 체크 + edm_search_pipe 선택
			// → 전처리 없이 바로 edm_search_pipe로 위임
			// → 파이프 내부에서:
			//   1. /tmp/download/imsi 폴더에 파일 다운로드
			//   2. 파싱 - 청킹 - 임베딩 - 벡터 저장
			//   3. RAG를 통해 응답
			console.log('🔵 [submitPrompt] EDM 파이프 위임 (전처리 없음)', {
				timestamp: new Date().toISOString(),
				action: 'edm_pipe_delegation',
				shouldUseEdm: shouldUseEdm,
				isEdmPipeSelected: isEdmPipeSelected,
				selectedModels: selectedModels,
				selectedCategories: $selectedCategories,
				userPrompt: userPrompt.substring(0, 100) + '...'
			});
			console.log('   선택된 모델:', selectedModels);
			console.log('   📁 파이프 내부에서 /tmp/download/imsi 폴더 처리 예정');
			// 파이프로 위임하기 위해 일반 플로우로 진행 (return 없음, 전처리 없음)
		}

		// ========================================
		// 기존 EDM 전용 플로우는 제거됨
		// EDM 파이프: 파이프 내부에서 n8n + Milvus 처리
		// 일반 모델: 아래 일반 RAG 플로우에서 처리
		// ========================================

		/* 기존 EDM 전용 플로우 제거 시작 (line 1650-1897)
		if (shouldUseEdm) {
			console.log('📂 EDM 문서활용 영역 - 검색 실행 (테스트 모드 강제)');
			edmSearchQuery = userPrompt;  // 검색어 저장

			// 첫 번째 EDM 사용 시 환영 메시지 표시
			// EDM 안내 메시지 표시 조건 (현재 채팅에 edm-welcome 메시지가 없을 때만)
			const hasEdmWelcomeMessage = history.messages &&
				Object.values(history.messages).some(msg => msg.model === 'edm-welcome');
			const showEdmWelcome = !hasEdmWelcomeMessage;

			if (showEdmWelcome) {
				console.log('🎉 첫 번째 EDM 사용 - 환영 메시지 추가');

				// 시스템 메시지로 EDM 안내 추가 (마크다운 형식)
				const edmInitMessage = {
					id: uuidv4(),
					parentId: history.currentId,
					childrenIds: [],
					role: 'assistant',
					content: `## 📚 EDM 문서활용 영역

**EDM 문서활용**은 이미 학습된 문서를 참고하여 AI 답변을 생성하고, 추가로 키워드 기반으로 EDM 문서 검색 결과를 제공합니다.

### 🔍 사용 방법
1. 질문을 입력하면 AI가 학습된 문서를 참고하여 답변을 생성합니다
2. 관련 문서 목록이 함께 제공됩니다
3. 답변 하단의 **"문서 검색결과 보기"** 버튼을 눌러 추가 문서를 확인할 수 있습니다
4. 원하는 문서를 선택하여 첨부 등록할 수 있습니다

### 📄 지원 형식
텍스트, 표, 차트, PDF, Word, Excel, PowerPoint 등 다양한 문서 형식을 지원합니다.`,
					model: 'edm-welcome',
					timestamp: Math.floor(Date.now() / 1000),
					done: true
				};

				history.messages[edmInitMessage.id] = edmInitMessage;

				// parentId의 childrenIds에 추가 (메시지 트리 구조 유지)
				if (history.messages[history.currentId]) {
					if (!history.messages[history.currentId].childrenIds) {
						history.messages[history.currentId].childrenIds = [];
					}
					history.messages[history.currentId].childrenIds.push(edmInitMessage.id);
				}

				history.currentId = edmInitMessage.id;

				await tick();
				if (autoScroll) {
					scrollToBottom();
				}
			}

			try {
				// n8n 연동 모드 활성화 여부 (환경변수로 제어)
				const useN8nIntegration = true; // TODO: 환경변수로 변경 가능

				console.log('🔍 EDM 문서활용 처리 시작:', {
					selectedModels,
					models: $models,
					user: $user,
					useN8nIntegration
				});

				// edmFileList는 컴포넌트 레벨 변수 사용 (line 222)
				edmFileList = []; // 초기화
				let learnedDocsCount = 0;
				let sources = [];
				let n8nDocuments = [];

// 1️⃣ EDM Search 파이프 호출하여 문서 검색
				if (useN8nIntegration) {
					console.log('📡 EDM Search 파이프 호출 중...');
					toast.info('EDM 문서 검색 중...');

					try {
						// EDM Search 파이프 호출
						const pipeName = 'edm_search_pipe'; // 실제 파이프명으로 변경 필요
						const pipePayload = {
							query: userPrompt,
							categories: $selectedCategories || ['edm'],
							chatId: $chatId,
							userId: $user?.id
						};

						const pipeResponse = await fetch(`/api/pipelines/${pipeName}`, {
							method: 'POST',
							headers: {
								'Content-Type': 'application/json',
								'Authorization': `Bearer ${localStorage.token}`
							},
							body: JSON.stringify(pipePayload)
						});

						if (!pipeResponse.ok) {
							console.error("🔴 EDM Search 파이프 호출 실패:", pipeResponse.status, pipeResponse.statusText);
						toast.error(`EDM 문서 검색 실패: ${pipeResponse.status}`);
						edmFileList = [];
						// 에러 발생 시에도 계속 진행 (빈 결과로)
					} else {
						const pipeResult = await pipeResponse.json();
						console.log('✅ EDM Search 파이프 응답:', pipeResult);

						// 파이프 결과가 List[dict] 형태로 반환됨
						const pipeDocuments = pipeResult.documents || pipeResult.data || pipeResult || [];

						if (Array.isArray(pipeDocuments) && pipeDocuments.length > 0) {
							// 파이프 결과를 EDM 포맷으로 변환
							edmFileList = convertN8nDocsToEdmFormat(pipeDocuments);
							console.log(`✅ EDM 파일 리스트 변환 완료: ${edmFileList.length}개 파일`);
							console.log('📋 변환된 파일 리스트:', edmFileList);

							learnedDocsCount = edmFileList.length;
							sources = edmFileList.slice(0, 3).map(file => file.FILE_NAME);
						} else {
							console.log('📭 파이프 결과 없음 - edmFileList는 빈 배열 유지');
							edmFileList = [];
						}
					}
					} catch (error) {
						console.error('❌ EDM Search 파이프 호출 실패:', error);
						edmFileList = [];
						// 에러는 아래 catch 블록에서 처리
					toast.error('EDM 문서 검색 중 오류가 발생했습니다.');
					edmFileList = [];
					// 에러 발생 시에도 계속 진행 (빈 결과로)
					}
				}

				// n8n 연동만 사용 - Mock 데이터 제거됨

				// edmFileList가 비어있으면 그대로 유지 (파일없음 표시용)

				// AI 답변 생성 - 실제 LLM 호출
				let aiAnswerContent = '';

				// 실제 LLM API 호출하여 답변 생성
				console.log('🤖 실제 LLM API 호출 시작...');
				console.log('   선택된 모델:', selectedModels);
				console.log('   검색어:', edmSearchQuery);
				console.log('   검색된 문서:', edmFileList.length, '건');

				try {
					// EDM 파일 목록을 컨텍스트로 변환
					let contextDocs = '';
					if (edmFileList.length > 0) {
						contextDocs = '\n\n참고 문서:\n';
						edmFileList.forEach((file, idx) => {
							contextDocs += `${idx + 1}. ${file.FILE_NAME} (작성자: ${file.AUTHOR}, 날짜: ${file.CREATE_DATE})\n`;
						});
					}

					// LLM에게 전달할 프롬프트 구성
					const llmPrompt = `사용자 질문: ${edmSearchQuery}${contextDocs}\n\n위 문서들을 참고하여 사용자의 질문에 답변해주세요.`;

					// createMessagePair를 통해 실제 LLM 호출 (기존 채팅 로직 재사용)
					// 하지만 EDM 모드이므로 history에 추가하지 않고 응답만 받음

					// 임시로 간단한 답변 생성 (실제 구현에서는 API 호출)
					aiAnswerContent = `"${edmSearchQuery}"에 대한 검색 결과입니다.\n\n검색된 ${edmFileList.length}건의 문서를 분석한 결과:\n\n• 프로젝트 기획과 관련된 주요 문서들이 확인되었습니다.\n• 아래 문서 검색 결과 버튼을 클릭하여 상세 정보를 확인하실 수 있습니다.\n• 필요하신 문서를 선택하여 자세한 내용을 검토해주세요.`;

					console.log('✅ LLM 답변 생성 완료');
				} catch (error) {
					console.error('❌ LLM API 호출 실패:', error);
					aiAnswerContent = `죄송합니다. 답변 생성 중 오류가 발생했습니다.\n\n검색된 ${edmFileList.length}건의 문서가 있습니다. 아래 문서 검색 결과 버튼을 클릭하여 확인해주세요.`;
				}

				// LLM 응답을 마크다운 박스로 감싸기 (원본 내용은 그대로, 추가 가공 없음)
				let markdownContent = '';

				// LLM 원본 응답 (마크다운 박스 형식)
				aiAnswerContent.split('\n').forEach(line => {
					markdownContent += `> ${line}\n`;
				});

				// n8n 문서 수 요약 추가 (LLM 응답 아래)
				console.log('🔍 edmFileList 길이:', edmFileList.length);
				console.log('🔍 edmFileList 내용:', edmFileList);

				markdownContent += '\n---\n\n';
				if (edmFileList.length > 0) {
					console.log('✅ 파일 있음 - 문서 수 표시');
					markdownContent += `> 📂 **EDM 검색결과: ${edmFileList.length}건**\n`;
				} else {
					console.log('❌ 파일 없음 - 파일없음 표시');
					markdownContent += `> 📂 **EDM 검색결과: 파일없음**\n`;
				}

				console.log('📄 최종 markdownContent:', markdownContent);

				// EDM 검색 결과 메시지 생성
				const edmResultMessage = {
					id: uuidv4(),
					parentId: history.currentId,
					childrenIds: [],
					role: 'assistant',
					content: markdownContent,
					model: isTestMode ? 'edm-test-mode' : 'edm-search',
					timestamp: Math.floor(Date.now() / 1000),
					done: true, // 메시지 완료 상태 (버튼 표시를 위해 필수)
					edmData: edmFileList,
					testMode: isTestMode,
					isEdmResult: true, // EDM 검색 결과임을 표시
					edmFileList: edmFileList, // 파일 목록 저장 (버튼 컴포넌트에서 사용)
					aiAnswer: aiAnswerContent, // AI 답변 저장
					edmQuery: edmSearchQuery // 검색어 저장
				};

				history.messages[edmResultMessage.id] = edmResultMessage;
				history.currentId = edmResultMessage.id;

				await tick();
				if (autoScroll) {
					scrollToBottom();
				}

				toast.success(isTestMode ? `테스트 모드: Mock AI 답변 + ${edmFileList.length}건의 샘플 문서` : `${edmFileList.length}건의 문서를 찾았습니다.`);
			} catch (error) {
				console.error('❌ EDM API 호출 실패:', error);
				
				// 에러 메시지 생성 (Markdown 형식)
				const errorMessage = error?.message || '알 수 없는 오류 발생';
				const errorStack = error?.stack || '스택 정보 없음';

				const errorContent = `> ## ❌ EDM 문서 검색 실패
>
> **오류 내용**: ${errorMessage}
>
> **상세 정보**:
> \`\`\`
> ${errorStack}
> \`\`\`
>
> ---
>
> 다시 시도하거나 관리자에게 문의하세요.`;

				const edmResultMessage = {
					id: uuidv4(),
					parentId: history.currentId,
					childrenIds: [],
					role: 'assistant',
					content: errorContent, // Markdown 형식 에러 메시지
					model: 'edm-error',
					timestamp: Math.floor(Date.now() / 1000),
					done: true,
					edmData: [],
					testMode: false,
					isEdmResult: true,
					edmFileList: [],
					error: true,
					errorMessage: errorMessage, // 오류 메시지 저장
					errorStack: errorStack // 스택 정보 저장
				};

				history.messages[edmResultMessage.id] = edmResultMessage;
				history.currentId = edmResultMessage.id;

				await tick();
				if (autoScroll) {
					scrollToBottom();
				}

				toast.error('EDM 문서 검색 중 오류가 발생했습니다.');
			}

			// EDM 모드에서도 채팅 히스토리 저장
			if ($chatId) {
				try {
					await updateChatById(localStorage.token, $chatId, {
						messages: messages,
						history: history
					});
					console.log('✅ EDM 채팅 히스토리 저장 완료');
				} catch (error) {
					console.error('❌ EDM 채팅 저장 실패:', error);
				}
			}

			return;  // 여기서 중단 (파일 선택 후 임베딩 요청으로 이어짐)
		}
		기존 EDM 전용 플로우 제거 끝 */

		// 대사우 Assistant: 사용자 의도 분석 및 자동 분류
		// 이전 의도 분석 로직 제거 - 파이프라인이 모든 처리를 담당
		console.log('🚀 [submitPrompt] 대사우 파이프라인으로 직접 전달');


		// 다른 모델 체크 주석 처리 - 기본 모델만 사용
		// const _selectedModels = selectedModels.map((modelId) =>
		// 	$models.map((m) => m.id).includes(modelId) ? modelId : ''
		// );
		// if (JSON.stringify(selectedModels) !== JSON.stringify(_selectedModels)) {
		// 	selectedModels = _selectedModels;
		// }

		// 빈 프롬프트 체크만 유지
		if (userPrompt === '') {
			toast.error($i18n.t('Please enter a prompt'));
			return;
		}

		// 모델 선택 체크 제거 - 기본 모델 자동 사용
		// if (selectedModels.includes('')) {
		// 	toast.error($i18n.t('Model not selected'));
		// 	return;
		// }

		// 파일 업로드 체크 제거
		// if (
		// 	files.length > 0 &&
		// 	files.filter((file) => file.type !== 'image' && file.status === 'uploading').length > 0
		// ) {
		// 	toast.error(
		// 		$i18n.t(`Oops! There are files still uploading. Please wait for the upload to complete.`)
		// 	);
		// 	return;
		// }

		// 파일 개수 제한 체크 제거
		// if (
		// 	($config?.file?.max_count ?? null) !== null &&
		// 	files.length + chatFiles.length > $config?.file?.max_count
		// ) {
		// 	toast.error(
		// 		$i18n.t(`You can only chat with a maximum of {{maxCount}} file(s) at a time.`, {
		// 			maxCount: $config?.file?.max_count
		// 		})
		// 	);
		// 	return;
		// }

		if (history?.currentId) {
			const lastMessage = history.messages[history.currentId];
			if (lastMessage.done != true) {
				// Response not done
				return;
			}

			if (lastMessage.error && !lastMessage.content) {
				// Error in response
				toast.error($i18n.t(`Oops! There was an error in the previous response.`));
				return;
			}
		}

		messageInput?.setText('');
		prompt = '';

		const messages = createMessagesList(history, history.currentId);
		const _files = JSON.parse(JSON.stringify(files));

		chatFiles.push(
			..._files.filter((item) =>
				['doc', 'text', 'file', 'note', 'chat', 'folder', 'collection'].includes(item.type)
			)
		);

		// Knowledge Base 추가 기능 주석 처리 - 기본 모델만 사용
		// if ($selectedCategories.length > 0) {
		// 	const hasEdm = $selectedCategories.includes("edm");
		// 	if (hasEdm) {
		// 		console.log("🔵 [EDM 선택됨] metadata로 전달");
		// 	}
		// 	$selectedCategories.filter(id => id !== "edm").forEach(categoryId => {
		// 		const collectionName = categoryId;
		// 		chatFiles.push({
		// 			type: 'collection',
		// 			id: categoryId,
		// 			name: categoryId,
		// 			collection_name: collectionName
		// 		});
		// 		console.log('🔵 [Knowledge Base 추가]', {
		// 			timestamp: new Date().toISOString(),
		// 			action: 'add_collection',
		// 			categoryId: categoryId,
		// 			categoryName: categoryId,
		// 			collectionName: collectionName,
		// 			totalChatFiles: chatFiles.length
		// 		});
		// 	});
		// }

		chatFiles = chatFiles.filter(
			// Remove duplicates
			(item, index, array) =>
				array.findIndex((i) => JSON.stringify(i) === JSON.stringify(item)) === index
		);

		files = [];
		messageInput?.setText('');

		// Create user message
		let userMessageId = uuidv4();
		let userMessage = {
			id: userMessageId,
			parentId: messages.length !== 0 ? messages.at(-1).id : null,
			childrenIds: [],
			role: 'user',
			content: userPrompt,
			files: _files.length > 0 ? _files : undefined,
			timestamp: Math.floor(Date.now() / 1000), // Unix epoch
			models: selectedModels
		};

		// Add message to history and Set currentId to messageId
		history.messages[userMessageId] = userMessage;
		history.currentId = userMessageId;

		// Append messageId to childrenIds of parent message
		if (messages.length !== 0) {
			history.messages[messages.at(-1).id].childrenIds.push(userMessageId);
		}

		// focus on chat input
		const chatInput = document.getElementById('chat-input');
		chatInput?.focus();

		saveSessionSelectedModels();

		console.log('[Chat] About to call sendMessage with newChat=true');
		console.log('[Chat] User message parentId:', userMessage.parentId);
		await sendMessage(history, userMessageId, { newChat: true });
		console.log('[Chat] sendMessage completed');
	};

	const sendMessage = async (
		_history,
		parentId: string,
		{
			messages = null,
			modelId = null,
			modelIdx = null,
			newChat = false
		}: {
			messages?: any[] | null;
			modelId?: string | null;
			modelIdx?: number | null;
			newChat?: boolean;
		} = {}
	) => {
		console.log('🔵 [sendMessage 시작]', {
			timestamp: new Date().toISOString(),
			action: 'send_message_start',
			parentId: parentId,
			newChat: newChat,
			modelId: modelId,
			modelIdx: modelIdx
		});

		if (autoScroll) {
			scrollToBottom();
		}

		let _chatId = JSON.parse(JSON.stringify($chatId));
		_history = JSON.parse(JSON.stringify(_history));

		const responseMessageIds: Record<PropertyKey, string> = {};
		// If modelId is provided, use it, else use selected model
		let selectedModelIds = modelId
			? [modelId]
			: atSelectedModel !== undefined
				? [atSelectedModel.id]
				: selectedModels;

		// Create response messages for each selected model
		for (const [_modelIdx, modelId] of selectedModelIds.entries()) {
			const model = $models.filter((m) => m.id === modelId).at(0);

			if (model) {
				let responseMessageId = uuidv4();
				let responseMessage = {
					parentId: parentId,
					id: responseMessageId,
					childrenIds: [],
					role: 'assistant',
					content: '',
					model: model.id,
					modelName: model.name ?? model.id,
					modelIdx: modelIdx ? modelIdx : _modelIdx,
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				// Add message to history and Set currentId to messageId
				history.messages[responseMessageId] = responseMessage;
				history.currentId = responseMessageId;

				// Append messageId to childrenIds of parent message
				if (parentId !== null && history.messages[parentId]) {
					// Add null check before accessing childrenIds
					history.messages[parentId].childrenIds = [
						...history.messages[parentId].childrenIds,
						responseMessageId
					];
				}

				responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`] = responseMessageId;
			}
		}
		history = history;

		// Create new chat if newChat is true and first user message
		console.log('[Chat] sendMessage - newChat check:', {
			newChat,
			currentId: _history.currentId,
			hasMessage: !!_history.messages[_history.currentId],
			parentId: _history.messages[_history.currentId]?.parentId,
			willCreateChat: newChat && _history.messages[_history.currentId]?.parentId === null
		});

		if (newChat && _history.messages[_history.currentId].parentId === null) {
			console.log('[Chat] Creating new chat with initChatHandler');
			_chatId = await initChatHandler(_history);
			console.log('[Chat] New chat created, chatId:', _chatId);
		}

		await tick();

		_history = JSON.parse(JSON.stringify(history));
		// Save chat after all messages have been created
		await saveChatHandler(_chatId, _history);

		await Promise.all(
			selectedModelIds.map(async (modelId, _modelIdx) => {
				console.log('modelId', modelId);
				const model = $models.filter((m) => m.id === modelId).at(0);

				if (model) {
					// If there are image files, check if model is vision capable
					const hasImages = createMessagesList(_history, parentId).some((message) =>
						message.files?.some((file) => file.type === 'image')
					);

					if (hasImages && !(model.info?.meta?.capabilities?.vision ?? true)) {
						toast.error(
							$i18n.t('Model {{modelName}} is not vision capable', {
								modelName: model.name ?? model.id
							})
						);
					}

					let responseMessageId =
						responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`];
					const chatEventEmitter = await getChatEventEmitter(model.id, _chatId);

					scrollToBottom();
					await sendMessageSocket(
						model,
						messages && messages.length > 0
							? messages
							: createMessagesList(_history, responseMessageId),
						_history,
						responseMessageId,
						_chatId
					);

					if (chatEventEmitter) clearInterval(chatEventEmitter);
				} else {
					toast.error($i18n.t(`Model {{modelId}} not found`, { modelId }));
				}
			})
		);

		currentChatPage.set(1);
		chats.set(await getChatList(localStorage.token, $currentChatPage));
	};

	const getFeatures = () => {
		let features = {};

		if ($config?.features)
			features = {
				image_generation:
					$config?.features?.enable_image_generation &&
					($user?.role === 'admin' || $user?.permissions?.features?.image_generation)
						? imageGenerationEnabled
						: false,
				code_interpreter:
					$config?.features?.enable_code_interpreter &&
					($user?.role === 'admin' || $user?.permissions?.features?.code_interpreter)
						? codeInterpreterEnabled
						: false,
				web_search:
					$config?.features?.enable_web_search &&
					($user?.role === 'admin' || $user?.permissions?.features?.web_search)
						? webSearchEnabled
						: false
			};

		const currentModels = atSelectedModel?.id ? [atSelectedModel.id] : selectedModels;
		if (
			currentModels.filter(
				(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.web_search ?? true
			).length === currentModels.length
		) {
			if ($config?.features?.enable_web_search && ($settings?.webSearch ?? false) === 'always') {
				features = { ...features, web_search: true };
			}
		}

		if ($settings?.memory ?? false) {
			features = { ...features, memory: true };
		}

		return features;
	};

	const sendMessageSocket = async (model, _messages, _history, responseMessageId, _chatId) => {
		const responseMessage = _history.messages[responseMessageId];
		const userMessage = _history.messages[responseMessage.parentId];

		const chatMessageFiles = _messages
			.filter((message) => message.files)
			.flatMap((message) => message.files);

		// Filter chatFiles to only include files that are in the chatMessageFiles
		// BUT: Always keep collection type (Knowledge Base) files
		chatFiles = chatFiles.filter((item) => {
			// collection 타입(Knowledge Base)은 항상 유지
			if (item.type === 'collection') {
				return true;
			}
			const fileExists = chatMessageFiles.some((messageFile) => messageFile.id === item.id);
			return fileExists;
		});

		// EDM 선택 여부 확인
		const hasEdm = $selectedCategories.includes("edm");

		// EDM 선택 시: collection 타입 파일 제외 (middleware 에러 방지)
		let files = JSON.parse(JSON.stringify(chatFiles));
		if (hasEdm) {
			// EDM 선택 시에는 collection 타입 파일 모두 제외
			files = files.filter(item => item.type !== 'collection');
			console.log("🔵 [EDM 선택됨] collection 타입 파일 제외:", files.length);
		}

		files.push(
			...(userMessage?.files ?? []).filter((item) =>
				hasEdm
					? ['doc', 'text', 'file', 'note', 'chat'].includes(item.type) // EDM: collection 제외
					: ['doc', 'text', 'file', 'note', 'chat', 'collection'].includes(item.type) // 일반: collection 포함
			)
		);
		// Remove duplicates
		files = files.filter(
			(item, index, array) =>
				array.findIndex((i) => JSON.stringify(i) === JSON.stringify(item)) === index
		);

		scrollToBottom();
		eventTarget.dispatchEvent(
			new CustomEvent('chat:start', {
				detail: {
					id: responseMessageId
				}
			})
		);
		await tick();

		let userLocation;
		if ($settings?.userLocation) {
			userLocation = await getAndUpdateUserLocation(localStorage.token).catch((err) => {
				console.error(err);
				return undefined;
			});
		}

		const stream =
			model?.info?.params?.stream_response ??
			$settings?.params?.stream_response ??
			params?.stream_response ??
			true;

		let messages = [
			params?.system || $settings.system
				? {
						role: 'system',
						content: `${params?.system ?? $settings?.system ?? ''}`
					}
				: undefined,
			..._messages.map((message) => ({
				...message,
				content: processDetails(message.content)
			}))
		].filter((message) => message);

		messages = messages
			.map((message, idx, arr) => ({
				role: message.role,
				...((message.files?.filter((file) => file.type === 'image').length > 0 ?? false) &&
				message.role === 'user'
					? {
							content: [
								{
									type: 'text',
									text: message?.merged?.content ?? message.content
								},
								...message.files
									.filter((file) => file.type === 'image')
									.map((file) => ({
										type: 'image_url',
										image_url: {
											url: file.url
										}
									}))
							]
						}
					: {
							content: message?.merged?.content ?? message.content
						})
			}))
			.filter((message) => message?.role === 'user' || message?.content?.trim());

		const toolIds = [];
		const toolServerIds = [];

		for (const toolId of selectedToolIds) {
			if (toolId.startsWith('direct_server:')) {
				let serverId = toolId.replace('direct_server:', '');
				// Check if serverId is a number
				if (!isNaN(parseInt(serverId))) {
					toolServerIds.push(parseInt(serverId));
				} else {
					toolServerIds.push(serverId);
				}
			} else {
				toolIds.push(toolId);
			}
		}

		// EDM 선택 시 EDM Search Pipeline을 모델로 설정
		if (hasEdm) {
			selectedModels = ['edm_search_pipe'];
			console.log('🔵 [EDM 선택됨] EDM Search Pipeline 모델로 설정:', selectedModels);
		}

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				stream: stream,
				model: hasEdm ? 'edm_search_pipe' : model.id,
				messages: messages,
				params: {
					...$settings?.params,
					...params,
					stop:
						(params?.stop ?? $settings?.params?.stop ?? undefined)
							? (params?.stop.split(',').map((token) => token.trim()) ?? $settings.params.stop).map(
									(str) => decodeURIComponent(JSON.parse('"' + str.replace(/\"/g, '\\"') + '"'))
								)
							: undefined
				},

				files: (files?.length ?? 0) > 0 ? files : undefined,

				filter_ids: selectedFilterIds.length > 0 ? selectedFilterIds : undefined,
				tool_ids: toolIds.length > 0 ? toolIds : undefined,
				tool_servers: ($toolServers ?? []).filter(
					(server, idx) => toolServerIds.includes(idx) || toolServerIds.includes(server?.id)
				),
				features: getFeatures(),
				variables: {
					...getPromptVariables($user?.name, $settings?.userLocation ? userLocation : undefined)
				},
				model_item: $models.find((m) => m.id === model.id),

				session_id: $socket?.id,
				chat_id: $chatId,
				id: responseMessageId,

				background_tasks: {
					...(!$temporaryChatEnabled &&
					(messages.length == 1 ||
						(messages.length == 2 &&
							messages.at(0)?.role === 'system' &&
							messages.at(1)?.role === 'user')) &&
					(selectedModels[0] === model.id || atSelectedModel !== undefined)
						? {
								title_generation: $settings?.title?.auto ?? true,
								tags_generation: $settings?.autoTags ?? true
							}
						: {}),
					follow_up_generation: $settings?.autoFollowUps ?? false
				},

				...(stream && (model.info?.meta?.capabilities?.usage ?? false)
					? {
							stream_options: {
								include_usage: true
							}
						}
					: {})
			},
			`${WEBUI_BASE_URL}/api`
		).catch(async (error) => {
			console.log(error);

			let errorMessage = error;
			if (error?.error?.message) {
				errorMessage = error.error.message;
			} else if (error?.message) {
				errorMessage = error.message;
			}

			if (typeof errorMessage === 'object') {
				errorMessage = $i18n.t(`Uh-oh! There was an issue with the response.`);
			}

			toast.error(`${errorMessage}`);
			responseMessage.error = {
				content: error
			};

			responseMessage.done = true;

			history.messages[responseMessageId] = responseMessage;
			history.currentId = responseMessageId;

			return null;
		});

		if (res) {
			if (res.error) {
				await handleOpenAIError(res.error, responseMessage);
			} else {
				if (taskIds) {
					taskIds.push(res.task_id);
				} else {
					taskIds = [res.task_id];
				}
			}
		}

		await tick();
		scrollToBottom();
	};

	const handleOpenAIError = async (error, responseMessage) => {
		let errorMessage = '';
		let innerError;

		if (error) {
			innerError = error;
		}

		console.error(innerError);
		if ('detail' in innerError) {
			// FastAPI error
			toast.error(innerError.detail);
			errorMessage = innerError.detail;
		} else if ('error' in innerError) {
			// OpenAI error
			if ('message' in innerError.error) {
				toast.error(innerError.error.message);
				errorMessage = innerError.error.message;
			} else {
				toast.error(innerError.error);
				errorMessage = innerError.error;
			}
		} else if ('message' in innerError) {
			// OpenAI error
			toast.error(innerError.message);
			errorMessage = innerError.message;
		}

		responseMessage.error = {
			content: $i18n.t(`Uh-oh! There was an issue with the response.`) + '\n' + errorMessage
		};
		responseMessage.done = true;

		if (responseMessage.statusHistory) {
			responseMessage.statusHistory = responseMessage.statusHistory.filter(
				(status) => status.action !== 'knowledge_search'
			);
		}

		history.messages[responseMessage.id] = responseMessage;
	};

	const stopResponse = async () => {
		if (taskIds) {
			for (const taskId of taskIds) {
				const res = await stopTask(localStorage.token, taskId).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			}

			taskIds = null;

			const responseMessage = history.messages[history.currentId];
			// Set all response messages to done
			for (const messageId of history.messages[responseMessage.parentId].childrenIds) {
				history.messages[messageId].done = true;
			}

			history.messages[history.currentId] = responseMessage;

			if (autoScroll) {
				scrollToBottom();
			}
		}

		if (generating) {
			generating = false;
			generationController?.abort();
			generationController = null;
		}
	};

	const submitMessage = async (parentId, prompt) => {
		let userPrompt = prompt;
		let userMessageId = uuidv4();

		let userMessage = {
			id: userMessageId,
			parentId: parentId,
			childrenIds: [],
			role: 'user',
			content: userPrompt,
			models: selectedModels,
			timestamp: Math.floor(Date.now() / 1000) // Unix epoch
		};

		if (parentId !== null) {
			history.messages[parentId].childrenIds = [
				...history.messages[parentId].childrenIds,
				userMessageId
			];
		}

		history.messages[userMessageId] = userMessage;
		history.currentId = userMessageId;

		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		await sendMessage(history, userMessageId);
	};

	const regenerateResponse = async (message, suggestionPrompt = null) => {
		console.log('regenerateResponse');

		if (history.currentId) {
			let userMessage = history.messages[message.parentId];

			if (autoScroll) {
				scrollToBottom();
			}

			await sendMessage(history, userMessage.id, {
				...(suggestionPrompt
					? {
							messages: [
								...createMessagesList(history, message.id),
								{
									role: 'user',
									content: suggestionPrompt
								}
							]
						}
					: {}),
				...((userMessage?.models ?? [...selectedModels]).length > 1
					? {
							// If multiple models are selected, use the model from the message
							modelId: message.model,
							modelIdx: message.modelIdx
						}
					: {})
			});
		}
	};

	const continueResponse = async () => {
		console.log('continueResponse');
		const _chatId = JSON.parse(JSON.stringify($chatId));

		if (history.currentId && history.messages[history.currentId].done == true) {
			const responseMessage = history.messages[history.currentId];
			responseMessage.done = false;
			await tick();

			const model = $models
				.filter((m) => m.id === (responseMessage?.selectedModelId ?? responseMessage.model))
				.at(0);

			if (model) {
				await sendMessageSocket(
					model,
					createMessagesList(history, responseMessage.id),
					history,
					responseMessage.id,
					_chatId
				);
			}
		}
	};

	const mergeResponses = async (messageId, responses, _chatId) => {
		console.log('mergeResponses', messageId, responses);
		const message = history.messages[messageId];
		const mergedResponse = {
			status: true,
			content: ''
		};
		message.merged = mergedResponse;
		history.messages[messageId] = message;

		try {
			generating = true;
			const [res, controller] = await generateMoACompletion(
				localStorage.token,
				message.model,
				history.messages[message.parentId].content,
				responses
			);

			if (res && res.ok && res.body && generating) {
				generationController = controller;
				const textStream = await createOpenAITextStream(res.body, $settings.splitLargeChunks);
				for await (const update of textStream) {
					const { value, done, sources, error, usage } = update;
					if (error || done) {
						generating = false;
						generationController = null;
						break;
					}

					if (mergedResponse.content == '' && value == '\n') {
						continue;
					} else {
						mergedResponse.content += value;
						history.messages[messageId] = message;
					}

					if (autoScroll) {
						scrollToBottom();
					}
				}

				await saveChatHandler(_chatId, history);
			} else {
				console.error(res);
			}
		} catch (e) {
			console.error(e);
		}
	};

	const initChatHandler = async (history) => {
		let _chatId = $chatId;

		if (!$temporaryChatEnabled) {
			chat = await createNewChat(
				localStorage.token,
				{
					id: _chatId,
					title: $i18n.t('New Chat'),
					models: selectedModels,
					system: $settings.system ?? undefined,
					params: params,
					history: history,
					messages: createMessagesList(history, history.currentId),
					tags: [],
					timestamp: Date.now()
				},
				$selectedFolder?.id
			);

			_chatId = chat.id;
			await chatId.set(_chatId);

			window.history.replaceState(history.state, '', `/c/${_chatId}`);

			await tick();

			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			currentChatPage.set(1);

			selectedFolder.set(null);
		} else {
			_chatId = `local:${$socket?.id}`; // Use socket id for temporary chat
			await chatId.set(_chatId);
		}
		await tick();

		return _chatId;
	};

	const saveChatHandler = async (_chatId, history) => {
		if ($chatId == _chatId) {
			if (!$temporaryChatEnabled) {
				// 🎯 자동 제목 생성: 제목이 "새 채팅"이면 첫 메시지로 교체
				let titleToUpdate = chat?.title;
				const isDefaultTitle = !titleToUpdate ||
					titleToUpdate === $i18n.t('New Chat') ||
					titleToUpdate === 'New Chat' ||
					titleToUpdate === '새 채팅';

				if (isDefaultTitle && history?.messages) {
					// 첫 번째 사용자 메시지 찾기
					const firstUserMessage = Object.values(history.messages).find(msg => msg.role === 'user');

					if (firstUserMessage?.content) {
						// 제목 생성: 첫 50자 사용, 줄바꿈 제거, 공백 정리
						titleToUpdate = (firstUserMessage.content || '')
							.substring(0, 50)
							.replace(/\n/g, ' ')
							.replace(/\s+/g, ' ')
							.trim();

						if (titleToUpdate) {
							console.log('🎯 [자동 제목] 생성:', titleToUpdate);
							chatTitle.set(titleToUpdate);
						}
					}
				}

				chat = await updateChatById(localStorage.token, _chatId, {
					models: selectedModels,
					history: history,
					messages: createMessagesList(history, history.currentId),
					params: params,
					files: chatFiles,
					...(titleToUpdate && titleToUpdate !== chat?.title ? { title: titleToUpdate } : {})
				});
				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
			}
		}
	};

	const MAX_DRAFT_LENGTH = 5000;
	let saveDraftTimeout = null;

	const saveDraft = async (draft, chatId = null) => {
		if (saveDraftTimeout) {
			clearTimeout(saveDraftTimeout);
		}

		if (draft.prompt !== null && draft.prompt.length < MAX_DRAFT_LENGTH) {
			saveDraftTimeout = setTimeout(async () => {
				await sessionStorage.setItem(
					`chat-input${chatId ? `-${chatId}` : ''}`,
					JSON.stringify(draft)
				);
			}, 500);
		} else {
			sessionStorage.removeItem(`chat-input${chatId ? `-${chatId}` : ''}`);
		}
	};

	const clearDraft = async (chatId = null) => {
		if (saveDraftTimeout) {
			clearTimeout(saveDraftTimeout);
		}
		await sessionStorage.removeItem(`chat-input${chatId ? `-${chatId}` : ''}`);
	};

	const moveChatHandler = async (chatId, folderId) => {
		if (chatId && folderId) {
			const res = await updateChatFolderIdById(localStorage.token, chatId, folderId).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
				await pinnedChats.set(await getPinnedChatList(localStorage.token));

				toast.success($i18n.t('Chat moved successfully'));
			}
		} else {
			toast.error($i18n.t('Failed to move chat'));
		}
	};

	// ===== EDM 문서 목록 및 뷰어 관련 함수 =====


	// 문서 뷰어 모달 열기
	const openDocumentViewer = async (document) => {
		console.log('🔵 문서 뷰어 열기:', document.title);
		selectedDocument = document;
		edmDocumentViewerModal = true;
		isLoadingDocument = true;
		documentContent = '';

		try {
			// 문서 내용 로드
			const response = await fetch(document.path);
			if (!response.ok) {
				throw new Error(`Failed to load document: ${response.status}`);
			}
			documentContent = await response.text();
			console.log('✅ 문서 로드 완료:', document.title);
		} catch (error) {
			console.error('❌ 문서 로드 실패:', error);
			toast.error('문서를 불러오는데 실패했습니다.');
			documentContent = '문서를 불러올 수 없습니다.';
		} finally {
			isLoadingDocument = false;
		}
	};

	// 문서 뷰어 모달 닫기
	const closeDocumentViewer = () => {
		console.log('🔵 문서 뷰어 닫기');
		edmDocumentViewerModal = false;
		selectedDocument = null;
		documentContent = '';
	};

	// 문서 선택/선택 해제
</script>

<svelte:head>
	<title>
		{$settings.showChatTitleInTab !== false && $chatTitle
			? `${$chatTitle.length > 30 ? `${$chatTitle.slice(0, 30)}...` : $chatTitle} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

<audio id="audioElement" src="" style="display: none;" />

<EventConfirmDialog
	bind:show={showEventConfirmation}
	title={eventConfirmationTitle}
	message={eventConfirmationMessage}
	input={eventConfirmationInput}
	inputPlaceholder={eventConfirmationInputPlaceholder}
	inputValue={eventConfirmationInputValue}
	on:confirm={(e) => {
		if (e.detail) {
			eventCallback(e.detail);
		} else {
			eventCallback(true);
		}
	}}
	on:cancel={() => {
		eventCallback(false);
	}}
/>

<!-- 🔄 멀티턴 초과 팝업 (해제됨) -->
<!-- <EventConfirmDialog
	bind:show={showMultiTurnModal}
	title="대화 턴 제한 초과"
	message={`대화 턴이 ${MAX_TURNS}회를 초과했습니다.\n\n새 채팅 세션을 시작하시겠습니까?`}
	input={false}
	on:confirm={() => {
		console.log('🔄 [멀티턴 팝업] 확인 버튼 클릭 - 새 채팅 세션 시작');
		showMultiTurnModal = false;
		window.location.href = '/';
	}}
	on:cancel={() => {
		console.log('🔄 [멀티턴 팝업] 취소 버튼 클릭');
		showMultiTurnModal = false;
	}}
/> -->

<div
	class="h-screen max-h-[100dvh] w-full flex flex-col"
	id="chat-container"
>
	{#if !loading}
		<div in:fade={{ duration: 50 }} class="w-full h-full flex flex-col">
			{#if $selectedFolder && $selectedFolder?.meta?.background_image_url}
				<div
				class="absolute top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({$selectedFolder?.meta?.background_image_url})  "
				/>

				<div
					class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"
				/>
			{:else if $settings?.backgroundImageUrl ?? $config?.license_metadata?.background_image_url ?? null}
				<div
				class="absolute top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({$settings?.backgroundImageUrl ??
						$config?.license_metadata?.background_image_url})  "
				/>

				<div
					class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"
				/>
			{/if}

			<PaneGroup direction="horizontal" class="w-full h-full" autoSaveId="chat-panes">
				<Pane defaultSize={100} minSize={70} class="h-full flex relative max-w-full flex-col">
					<Navbar
						bind:this={navbarElement}
						chat={{
							id: $chatId,
							chat: {
								title: $chatTitle,
								models: selectedModels,
								system: $settings.system ?? undefined,
								params: params,
								history: history,
								timestamp: Date.now()
							}
						}}
						{history}
						title={$chatTitle}
						bind:selectedModels
						shareEnabled={!!history.currentId}
						{initNewChat}
						archiveChatHandler={() => {}}
						{moveChatHandler}
						modelSelectorDisabled={isModelSelectorDisabled}
						onSaveTempChat={async () => {
							try {
								if (!history?.currentId || !Object.keys(history.messages).length) {
									toast.error($i18n.t('No conversation to save'));
									return;
								}
								const messages = createMessagesList(history, history.currentId);
								const title =
									messages.find((m) => m.role === 'user')?.content ?? $i18n.t('New Chat');

								const savedChat = await createNewChat(
									localStorage.token,
									{
										id: uuidv4(),
										title: title.length > 50 ? `${title.slice(0, 50)}...` : title,
										models: selectedModels,
										history: history,
										messages: messages,
										timestamp: Date.now()
									},
									null
								);

								if (savedChat) {
									temporaryChatEnabled.set(false);
									chatId.set(savedChat.id);
									chats.set(await getChatList(localStorage.token, $currentChatPage));

									await goto(`/c/${savedChat.id}`);
									toast.success($i18n.t('Conversation saved successfully'));
								}
							} catch (error) {
								console.error('Error saving conversation:', error);
								toast.error($i18n.t('Failed to save conversation'));
							}
						}}
					/>

					<!-- 2분할 레이아웃: 중앙 콘텐츠 - 하단 입력 -->
					<div class="flex flex-col h-full w-full">

						<!-- 중앙 콘텐츠 영역 (flex-1로 남은 공간 차지) -->
						<div class="flex-1 overflow-hidden relative">
						{#if ($settings?.landingPageMode === 'chat' && !$selectedFolder) || createMessagesList(history, history.currentId).length > 0}
							<!-- 채팅 메시지 영역 (스크롤 가능) -->
							<div
								class="h-full w-full overflow-y-auto overflow-x-hidden scrollbar-hidden"
								id="messages-container"
								bind:this={messagesContainerElement}
								on:scroll={(e) => {
									autoScroll =
										messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
										messagesContainerElement.clientHeight + 5;
								}}
							>
								<div class="w-full max-w-5xl mx-auto flex flex-col pb-4">
									<Messages
										chatId={$chatId}
										bind:history
										bind:autoScroll
										bind:prompt
										setInputText={(text) => {
											messageInput?.setText(text);
										}}
										{selectedModels}
										{atSelectedModel}
										{sendMessage}
										{showMessage}
										{submitMessage}
										{continueResponse}
										{regenerateResponse}
										{mergeResponses}
										{chatActionHandler}
										{addMessages}
										topPadding={true}
										bottomPadding={files.length > 0}
										{onSelect}
										on:openEdmFileList={(e) => {
											console.log('[Chat] 📂 EDM 파일 리스트 열기 이벤트 수신, 파일:', e.detail?.files);
										edmFileList = e.detail?.files || [];
											showEdmFileListModal = true;
										}}
										on:edmFeedback={(e) => {
											const { messageId, type } = e.detail;
											console.log('[Chat] 👍👎 EDM 피드백 이벤트 수신:', { messageId, type });
											currentEdmMessageId = messageId;
											edmFeedbackType = type;
											showEdmFeedbackModal = true;
										}}
									/>
								</div>
							</div>




						{:else}
							<!-- 초기 화면 (카테고리 선택) -->
							<div class="h-full w-full overflow-y-auto flex items-center justify-center">
								{#if $modelType === 'internal'}
									<!-- 대사우 Assistant 선택 시: 3개 카테고리 카드 -->
									{#if ['guide', 'helpdesk', 'dictionary', 'etc'].some(id => $selectedCategories.includes(id))}
										<div class="w-full max-w-6xl p-6">
											<!-- 헤더 메시지 -->
											<div class="mb-6 text-center">
												<h3 class="text-lg font-medium text-gray-700 dark:text-gray-300">
													다음과 같은 질문을 물어볼 수 있어요
												</h3>
											</div>

											<!-- 3개 카테고리 카드 -->
											<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
												<!-- 회사생활가이드 -->
												<div class="flex flex-col gap-2 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
													<div class="flex items-center gap-2 mb-2">
														<span class="text-2xl">📋</span>
														<h4 class="text-sm font-semibold text-gray-800 dark:text-gray-200">
															회사생활가이드
														</h4>
													</div>
													<div class="flex flex-col gap-2">
														<button
															class="text-left px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200 group"
															on:click={async () => {
																const sampleText = '육아휴직 신청 방법 알려 줘.';
																prompt = sampleText;
																await tick();
																if (messageInput) { await messageInput.setText(sampleText); }
															}}
														>
															<div class="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-blue-300 line-clamp-2">
																육아휴직 신청 방법 알려 줘.
															</div>
														</button>
														<button
															class="text-left px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200 group"
															on:click={async () => {
																const sampleText = '연간 패밀리넷 사용 가능 금액 알려 줘';
																prompt = sampleText;
																await tick();
																if (messageInput) { await messageInput.setText(sampleText); }
															}}
														>
															<div class="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-blue-300 line-clamp-2">
																연간 패밀리넷 사용 가능 금액 알려 줘
															</div>
														</button>
													</div>
												</div>

												<!-- IT Help Desk -->
												<div class="flex flex-col gap-2 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
													<div class="flex items-center gap-2 mb-2">
														<span class="text-2xl">💻</span>
														<h4 class="text-sm font-semibold text-gray-800 dark:text-gray-200">
															IT Help Desk
														</h4>
													</div>
													<div class="flex flex-col gap-2">
														<button
															class="text-left px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200 group"
															on:click={async () => {
																const sampleText = 'Knox 비밀번호 초기화 방법 알려 줘.';
																prompt = sampleText;
																await tick();
																if (messageInput) { await messageInput.setText(sampleText); }
															}}
														>
															<div class="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-blue-300 line-clamp-2">
																Knox 비밀번호 초기화 방법 알려 줘.
															</div>
														</button>
														<button
															class="text-left px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200 group"
															on:click={async () => {
																const sampleText = 'Wave 운영팀 내선 번호 알려 줘.';
																prompt = sampleText;
																await tick();
																if (messageInput) { await messageInput.setText(sampleText); }
															}}
														>
															<div class="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-blue-300 line-clamp-2">
																Wave 운영팀 내선 번호 알려 줘.
															</div>
														</button>
													</div>
												</div>

												<!-- 지식용어 사전 -->
												<div class="flex flex-col gap-2 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
													<div class="flex items-center gap-2 mb-2">
														<span class="text-2xl">📚</span>
														<h4 class="text-sm font-semibold text-gray-800 dark:text-gray-200">
															지식용어 사전
														</h4>
													</div>
													<div class="flex flex-col gap-2">
														<button
															class="text-left px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200 group"
															on:click={async () => {
																const sampleText = '우리회사 PCCB 절차는 어떻게 돼';
																prompt = sampleText;
																await tick();
																if (messageInput) { await messageInput.setText(sampleText); }
															}}
														>
															<div class="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-blue-300 line-clamp-2">
																우리회사 PCCB 절차는 어떻게 돼
															</div>
														</button>
														<button
															class="text-left px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200 group"
															on:click={async () => {
																const sampleText = 'Rfzen, Rpsc와 관련된 WSD는 어떤 뜻이야';
																prompt = sampleText;
																await tick();
																if (messageInput) { await messageInput.setText(sampleText); }
															}}
														>
															<div class="text-sm text-gray-700 dark:text-gray-300 group-hover:text-blue-700 dark:group-hover:text-blue-300 line-clamp-2">
																Rfzen, Rpsc와 관련된 WSD는 어떤 뜻이야
															</div>
														</button>
													</div>
												</div>
											</div>
										</div>
									{:else}
										<!-- 기존 6개 카테고리 카드 -->
										<div class="w-full max-w-6xl p-6">
											<div class="w-full">
												<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
													{#each categories as category}
													<div
														class="bg-white dark:bg-gray-800 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-200 dark:border-gray-700"
													>
														<div class="p-6">
															<!-- Category header -->
															<div class="flex items-center gap-3 mb-4">
																<!-- 카테고리 아이콘 -->
																<div class="bg-gray-50 dark:bg-gray-800 p-2 rounded-lg shadow-sm flex-shrink-0">
																	{#if category.id === 'edm'}
																		<svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
																		</svg>
																	{:else if category.id === 'guide'}
																		<svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
																		</svg>
																	{:else if category.id === 'helpdesk'}
																		<svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"></path>
																		</svg>
																	{/if}
																</div>

																<h3 class="text-xl font-bold text-gray-800 dark:text-gray-100">
																	{#if category.name.includes('[')}
																		{category.name.split('[')[0].trim()}
																	{:else}
																		{category.name}
																	{/if}
																</h3>
															</div>


															<!-- Action button -->
															<div class="mt-4">
																{#if category.id === 'edm-file-search-hidden'}
																	<!-- EDM 전용 파일 검색 버튼 (기능 보존, 현재 숨김) -->
																	<button
																		class="w-full px-4 py-3 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-md hover:shadow-lg"
																		on:click={() => {
																			console.log('🔵 EDM 파일 검색 버튼 클릭 - 카테고리 선택됨');
																			selectedCategories.set([category]);
																			console.log('✅ EDM 모드 활성화 - 이제 메시지를 입력하고 전송하세요');
																		}}
																	>
																		EDM 파일 검색
																	</button>
																{:else}
																	<!-- 샘플 질문 표시 (모든 카테고리 동일) -->
																	<div class="space-y-2">
																		{#each category.samples as sample}
																			<button
																				class="w-full text-left px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700"
																				on:click={async () => {
																	// 🎯 카테고리별 처리 - 항상 첫번째 처리로 동작
																	if (category.id === 'edm' || category.id === 'guide' || category.id === 'helpdesk') {
																		// EDM 문서활용 또는 대사우 Assistant 카테고리
																		console.log('🔵 EDM/대사우 샘플 질문 클릭 - 카테고리:', category.name);

																		// 카테고리에 맞는 displayCategory 찾기
																		let displayCategory = null;
																		if (category.id === 'edm') {
																			displayCategory = DISPLAY_CATEGORIES[0];  // EDM 문서활용
																		} else if (category.id === 'guide' || category.id === 'helpdesk') {
																			displayCategory = DISPLAY_CATEGORIES[1];  // 대사우 Assistant
																		}

																		// selectedCategories 무조건 업데이트 (reactive statement가 모델 변경)
																		if (displayCategory) {
																			const { actualIds } = displayCategory;
																			selectedCategories.set(actualIds);  // 직접 설정 (기존 카테고리 초기화)
																			console.log('✅ 카테고리 설정:', actualIds);
																		}

																		// 메시지 입력창에 샘플 질문 채우기
																		prompt = sample;
																		await tick();
																		if (messageInput) {
																			await messageInput.setText(sample);
																		}
																	} else {
																		// 그 이외 카드 버튼 (보고서 초안 작성, Code 개발 지원, 외부정보검색 등)
																		console.log('🔵 일반 카테고리 샘플 질문 클릭 - 카테고리:', category.name);

																		// selectedCategories 초기화 (카테고리 선택 해제)
																		selectedCategories.set([]);
																		console.log('✅ 카테고리 초기화 (선택 해제)');

																		// 내부 기본 모델로 무조건 설정
																		const defaultModelId = getDefaultInternalModelId();
																		if (defaultModelId) {
																			selectedModels = [defaultModelId];
																			console.log('✅ 내부 기본 모델 설정:', defaultModelId);
																		}

																		// 메시지 입력창에 샘플 질문 채우기
																		prompt = sample;
																		await tick();
																		if (messageInput) {
																			await messageInput.setText(sample);
																		}
																	}
																				}}
																			>
																				<span class="text-gray-700 dark:text-gray-300">{sample}</span>
																			</button>
																		{/each}
																	</div>
																{/if}
															</div>
														</div>
													</div>
												{/each}
											</div>
										</div>
									</div>
									{/if}
								{:else}
									<!-- 외부모델: 외부정보검색 카테고리 카드 표시 -->
									<div class="w-full max-w-6xl p-6 mx-auto">
										<div class="w-full">
											<div class="grid grid-cols-1 md:grid-cols-1 gap-6 max-w-md mx-auto">
												{#each categories.filter(c => c.id === 'search') as category}
												<div
													class="bg-white dark:bg-gray-800 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-200 dark:border-gray-700"
												>
													<div class="p-6">
														<!-- Category header -->
														<div class="flex items-center gap-3 mb-4">
															<!-- 카테고리 아이콘 -->
															<div class="bg-gray-50 dark:bg-gray-800 p-2 rounded-lg shadow-sm flex-shrink-0">
																{#if category.id === 'edm'}
																	<svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
																	</svg>
																{:else if category.id === 'guide'}
																	<svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
																	</svg>
																{:else if category.id === 'helpdesk'}
																	<svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"></path>
																	</svg>
																{/if}
															</div>

															<h3 class="text-xl font-bold text-gray-800 dark:text-gray-100">
																{#if category.name.includes('[')}
																	{category.name.split('[')[0].trim()}
																{:else}
																	{category.name}
																{/if}
															</h3>
														</div>


														<!-- Sample questions -->
														<div class="space-y-2">
															{#each category.samples as sample}
																<button
																	class="w-full text-left px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-700"
																	on:click={async () => {
																		selectedCategories.set([category]);
																		console.log('🔵 외부모델 샘플 질문 클릭 - 카테고리:', category.name);

																		// 입력창에 샘플 질문 채우기
																		prompt = sample;
																		await tick();
																		if (messageInput) {
																			await messageInput.setText(sample);
																		}
																	}}
																>
																	<span class="text-gray-700 dark:text-gray-300">{sample}</span>
																</button>
															{/each}
														</div>
													</div>
												</div>
												{/each}
											</div>
										</div>
									</div>
								{/if}
							</div>
						{/if}
						</div>

						<!-- 하단 고정 입력 영역 (내부/외부 모델 모두 표시) -->
						<div class="flex-shrink-0 border-t border-gray-300 dark:border-gray-700">
							<MessageInput
								bind:this={messageInput}
								{history}
								{taskIds}
								bind:selectedModels
								bind:files
								bind:prompt
								bind:autoScroll
								bind:selectedToolIds
								bind:selectedFilterIds
								bind:imageGenerationEnabled
								bind:codeInterpreterEnabled
								bind:webSearchEnabled
								bind:atSelectedModel
								bind:showCommands
								toolServers={$toolServers}
								{generating}
								{stopResponse}
								{createMessagePair}
								modelSelectorDisabled={isModelSelectorDisabled}
								onChange={(data) => {
									if (!$temporaryChatEnabled) {
										saveDraft(data, $chatId);
									}
								}}
								on:upload={async (e) => {
									const _response = await uploadFiles(
										localStorage.token,
										e.detail.files
									).catch((error) => {
										toast.error(error);
										return null;
									});

									if (_response) {
										files = [
											...files,
											..._response.map((file) => ({
												type: 'file',
												...file
											}))
										];
									}
								}}
								on:submit={async (e) => {
									await submitPrompt(
										e.detail.prompt,
										e.detail.systemPrompt
									);
								}}
							/>
						</div>

						<!-- Model type toggle buttons (항상 표시) -->
						<div class="flex justify-between gap-2 px-4 py-2 border-t border-gray-200 dark:border-gray-700">
						<!-- Selected category display -->
						{#if displayCategoriesForUI.length > 0}
							<div class="flex items-center gap-2 overflow-x-auto scrollbar-hidden flex-1 max-w-[60%]">
								{#each displayCategoriesForUI as cat}
									<div class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-full border border-blue-300 dark:border-blue-700 whitespace-nowrap flex-shrink-0">
										<span class="text-xs font-medium text-blue-700 dark:text-blue-300">{cat.name}</span>
									</div>
								{/each}
							</div>
						{:else}
							<div></div> <!-- Spacer when no category selected -->
						{/if}

						<!-- Toggle buttons container -->
						<div class="flex gap-2">
							<button
								class="px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm {$modelType === 'internal'
									? 'bg-gray-700 dark:bg-gray-600 text-white'
									: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-200 dark:hover:bg-gray-750'}"
								on:click={() => handleModelTypeChange('internal')}
							>
								내부모델
							</button>
							<button
								class="px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm {$modelType === 'external'
									? 'bg-gray-700 dark:bg-gray-600 text-white'
									: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-200 dark:hover:bg-gray-750'}"
								on:click={() => handleModelTypeChange('external')}
							>
								외부모델
							</button>
						</div>
						</div>

							</div>
				</Pane>

				<!-- Right Sidebar Pane (Category Selection) - 내부모델일 때만 표시 -->
				{#if $modelType === 'internal'}
				<PaneResizer class="w-1 hover:bg-gray-300 dark:hover:bg-gray-700 transition-colors" />
				<Pane defaultSize={20} minSize={15} maxSize={30} class="h-full">
					<RightSidebar />
				</Pane>
				{/if}
			</PaneGroup>
		</div>
	{:else if loading}
		<div class=" flex items-center justify-center h-full w-full">
			<div class="m-auto">
				<Spinner className="size-5" />
			</div>
		</div>
	{/if}

	<!-- Security Warning Modal for External Model -->
	{#if showSecurityWarning}
		<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
			<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
				<!-- 아이콘 -->
				<div class="flex justify-center mb-4 pt-6">
					<div class="flex items-center justify-center w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30">
						<svg class="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
						</svg>
					</div>
				</div>

				<!-- 제목 -->
				<h3 class="text-center text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 px-6">
					외부모델로 전환
				</h3>

				<!-- 메시지 -->
				<div class="px-6 pb-6 space-y-2 text-sm text-gray-600 dark:text-gray-400 text-center">
					<p class="font-medium text-amber-700 dark:text-amber-400">
						외부 검색 전용 공간입니다.
					</p>
					<p>내부 데이터와 분리됩니다.</p>
					<p>내부모델의 채팅내역은 외부모델에서 사용할 수 없습니다.</p>
				</div>

				<!-- 버튼 -->
				<div class="px-6 pb-6 flex gap-3 justify-center">
					<button
						class="px-6 py-2 rounded-lg text-sm font-medium
						       bg-gray-100 dark:bg-gray-700
						       text-gray-700 dark:text-gray-300
						       hover:bg-gray-200 dark:hover:bg-gray-600
						       transition-colors duration-200"
						on:click={cancelExternalModelSwitch}
					>
						취소
					</button>
					<button
						class="px-6 py-2 rounded-lg text-sm font-medium
						       bg-blue-600 hover:bg-blue-700
						       text-white
						       transition-colors duration-200"
						on:click={confirmExternalModelSwitch}
					>
						동의 후 이동
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<!-- EDM 파일리스트 모달 -->
{#if showEdmFileListModal}
	<EdmFileListModal
		files={edmFileList}
		show={showEdmFileListModal}
		on:close={() => {
			showEdmFileListModal = false;
		}}
		on:embed={async (event) => {
			console.log('🔵 [on:embed 핸들러 시작]', {
				timestamp: new Date().toISOString(),
				action: 'embed_handler_start',
				filesCount: event.detail.files.length,
				files: event.detail.files.map(f => ({
					objid: f.objid,
					fileName: f.fileName || f.objtNm,
					filePath: f.filePath
				}))
			});
			const selectedFiles = event.detail.files;

			showEdmFileListModal = false;

			try {
				const token = localStorage.getItem('token') || '';
				let successCount = 0;
				let failCount = 0;

				// EDM 지식 베이스 ID (없으면 생성)
				let knowledgeBaseId = 'edm-knowledge-base';

				// 각 파일 처리 - 실제 벡터화 파이프 사용
				for (let i = 0; i < selectedFiles.length; i++) {
					const file = selectedFiles[i];
					const fileNum = i + 1;
					const totalFiles = selectedFiles.length;

					try {
						// 📂 [Chat.svelte:3827] 벡터화 시작 로그
						console.log("=" + "=".repeat(79));
						console.log('📂 [COMPONENT] Chat.svelte:3827');
						console.log('📂 [ACTION] 파일 벡터화 시작');
						console.log(`📂 [FILE_INFO] ${fileNum}/${totalFiles} - ${file.objtNm}`);
						console.log(`📂 [FILE_NAME] ${file.fileName || file.objtNm}`);
						console.log(`📂 [FILE_PATH] ${file.filePath}`);
						console.log(`📂 [OBJID] ${file.objid}`);
						console.log("=" + "=".repeat(79));

						// 1단계: 파일 파싱 시작
						toast.info(`[${fileNum}/${totalFiles}] ${file.objtNm} - 파일을 읽고 있습니다...`);
						console.log(`📄 벡터화 처리 중: ${file.objtNm}`, {
							fileName: file.fileName,
							filePath: file.filePath,
							objid: file.objid
						});

						// 2단계: 파싱, 청킹, 임베딩 파이프라인 호출
						toast.info(`[${fileNum}/${totalFiles}] ${file.objtNm} - 파싱 및 청킹 중...`);

						const vectorizePipeName = 'edm_embedding_pipe';
						const vectorizePayload = {
							file_id: file.objid,
							file_name: file.fileName || file.objtNm,
							file_path: file.filePath,  // edm_download_pipe에서 받은 로컬 파일 경로
							file_type: 'application/octet-stream',
							user_id: $user?.id,
							chat_id: $chatId,
							collection_name: 'edm-knowledge'  // Milvus collection
						};

						// 🔌 [Chat.svelte:3858] 벡터화 파이프 호출 로그
						console.log("=" + "=".repeat(79));
						console.log('🔌 [PIPELINE] edm_embedding_pipe');
						console.log('🔌 [COMPONENT] Chat.svelte:3858');
						console.log('🔌 [ACTION] 벡터화 파이프 호출');
						console.log(`🔌 [FILE_PATH] ${vectorizePayload.file_path}`);
						console.log(`🔌 [COLLECTION] ${vectorizePayload.collection_name}`);
						console.log(`🔌 [PAYLOAD]`, vectorizePayload);
						console.log("=" + "=".repeat(79));

						console.log('🔵 [벡터화 파이프 호출]', {
						timestamp: new Date().toISOString(),
						action: 'vectorization_pipe_call',
						pipeName: vectorizePipeName,
						fileNum: fileNum,
						totalFiles: totalFiles,
						payload: vectorizePayload
					});

						const vectorizeResponse = await fetch(`/api/pipelines/${vectorizePipeName}`, {
							method: 'POST',
							headers: {
								'Content-Type': 'application/json',
								'Authorization': `Bearer ${localStorage.token}`
							},
							body: JSON.stringify(vectorizePayload)
						});

						if (!vectorizeResponse.ok) {
							throw new Error(`벡터화 파이프 실패: ${vectorizeResponse.status}`);
						}

						const vectorizeResult = await vectorizeResponse.json();
						console.log('🟢 [벡터화 파이프 응답 성공]', {
						timestamp: new Date().toISOString(),
						action: 'vectorization_pipe_response',
						fileNum: fileNum,
						fileName: file.objtNm,
						success: vectorizeResult.success || vectorizeResult.status === 'success',
						doc_id: vectorizeResult.doc_id || vectorizeResult.document_id,
						chunks_count: vectorizeResult.chunks_count || vectorizeResult.total_chunks,
						embeddings_count: vectorizeResult.embeddings_count || vectorizeResult.total_embeddings,
						response: vectorizeResult
					});

						// 3단계: 벡터 임베딩 처리
						toast.info(`[${fileNum}/${totalFiles}] ${file.objtNm} - 벡터 임베딩 생성 중...`);

						if (vectorizeResult.success || vectorizeResult.status === 'success') {
							console.log(`✅ 벡터화 성공: ${file.objtNm}`);
							console.log(`   - 문서 ID: ${vectorizeResult.doc_id || vectorizeResult.document_id}`);
							console.log(`   - 청크 수: ${vectorizeResult.chunks_count || vectorizeResult.total_chunks}`);
							console.log(`   - 임베딩 수: ${vectorizeResult.embeddings_count || vectorizeResult.total_embeddings}`);

							// 4단계: Milvus DB 저장 완료
							toast.info(`[${fileNum}/${totalFiles}] ${file.objtNm} - Milvus DB에 저장 완료`);

							// 5단계: 완료
							const chunkCount = vectorizeResult.chunks_count || vectorizeResult.total_chunks || 0;
							toast.success(`[${fileNum}/${totalFiles}] ${file.objtNm} - 지식화 완료! (${chunkCount}개 청크)`);
							successCount++;
						} else {
							throw new Error(vectorizeResult.error || vectorizeResult.message || '벡터화 실패');
						}
					} catch (fileError) {
						console.error(`❌ 파일 처리 실패: ${file.objtNm}`, fileError);
						toast.error(`[${fileNum}/${totalFiles}] ${file.objtNm} - 처리 실패: ${fileError.message}`);
						failCount++;
					}

					// 파일 간 짧은 대기 (UI 업데이트 및 서버 부하 방지)
					await new Promise(resolve => setTimeout(resolve, 500));
				}

				// 최종 결과 표시
				if (successCount > 0 && failCount === 0) {
					toast.success(`🎉 모든 파일(${successCount}개) 지식화 완료! 이제 채팅에서 문서 내용을 검색할 수 있습니다.`);
				} else if (successCount > 0 && failCount > 0) {
					toast.info(`✅ ${successCount}개 지식화 성공, ❌ ${failCount}개 실패`);
				} else {
					toast.error(`모든 파일 지식화 실패 (${failCount}개)`);
				}

			} catch (error) {
				console.error('❌ EDM 파일 지식화 실패:', error);
				toast.error('파일 지식화 중 오류 발생: ' + error.message);
			}
		}}
	/>
{/if}

<!-- EDM 피드백 모달 -->
{#if showEdmFeedbackModal}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
		on:click={() => {
			showEdmFeedbackModal = false;
			edmFeedbackReason = '';
			edmFeedbackDetail = '';
		}}
	>
		<div
			class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
			on:click|stopPropagation
		>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
				{edmFeedbackType === 'thumbs-down' ? '어떤 점이 마음에 들지 않으셨나요?' : '피드백 감사합니다!'}
			</h3>

			{#if edmFeedbackType === 'thumbs-down'}
				<!-- 불만족 이유 선택 -->
				<div class="space-y-3 mb-4">
					<label class="flex items-center space-x-2 cursor-pointer">
						<input
							type="radio"
							name="edmFeedbackReason"
							value="irrelevant"
							bind:group={edmFeedbackReason}
							class="w-4 h-4"
						/>
						<span class="text-sm text-gray-700 dark:text-gray-300">질문과 답변의 관련성이 낮음</span>
					</label>

					<label class="flex items-center space-x-2 cursor-pointer">
						<input
							type="radio"
							name="edmFeedbackReason"
							value="incorrect"
							bind:group={edmFeedbackReason}
							class="w-4 h-4"
						/>
						<span class="text-sm text-gray-700 dark:text-gray-300">사실과 다르거나 오류가 있음</span>
					</label>

					<label class="flex items-center space-x-2 cursor-pointer">
						<input
							type="radio"
							name="edmFeedbackReason"
							value="ignored-instruction"
							bind:group={edmFeedbackReason}
							class="w-4 h-4"
						/>
						<span class="text-sm text-gray-700 dark:text-gray-300">지시한 조건이나 형식을 무시함</span>
					</label>

					<label class="flex items-center space-x-2 cursor-pointer">
						<input
							type="radio"
							name="edmFeedbackReason"
							value="not-helpful"
							bind:group={edmFeedbackReason}
							class="w-4 h-4"
						/>
						<span class="text-sm text-gray-700 dark:text-gray-300">도움이 되지 않음</span>
					</label>
				</div>

				<!-- 상세 의견 입력 -->
				<div class="mb-4">
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						기타 의견 입력
					</label>
					<textarea
						bind:value={edmFeedbackDetail}
						placeholder="선택한 불만족 유형에 대한 상세한 설명을 작성해주세요"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
							   bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
							   focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
						rows="4"
					></textarea>
				</div>
			{:else}
				<!-- 만족 메시지 -->
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
					유용한 답변이 되었다니 기쁩니다. 소중한 피드백 감사드립니다.
				</p>
			{/if}

			<!-- 버튼 -->
			<div class="flex justify-end space-x-3">
				<button
					on:click={() => {
						showEdmFeedbackModal = false;
						edmFeedbackReason = '';
						edmFeedbackDetail = '';
					}}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300
						   bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
				>
					취소
				</button>
				<button
					on:click={() => {
						console.log('📊 EDM 피드백 제출:', {
							messageId: currentEdmMessageId,
							type: edmFeedbackType,
							reason: edmFeedbackReason,
							detail: edmFeedbackDetail
						});

						// 메시지에 평가 정보 저장
						if (currentEdmMessageId && history.messages[currentEdmMessageId]) {
							history.messages[currentEdmMessageId].feedback = {
								type: edmFeedbackType,
								reason: edmFeedbackReason,
								detail: edmFeedbackDetail,
								timestamp: Date.now()
							};
						}

						toast.success('피드백이 제출되었습니다. 감사합니다!');
						showEdmFeedbackModal = false;
						edmFeedbackReason = '';
						edmFeedbackDetail = '';
					}}
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg
						   hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={edmFeedbackType === 'thumbs-down' && !edmFeedbackReason}
				>
					제출
				</button>
			</div>
		</div>
	</div>
{/if}


<!-- EDM 문서 뷰어 모달 -->
{#if edmDocumentViewerModal && selectedDocument}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
		on:click={closeDocumentViewer}
	>
		<div
			class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col"
			on:click|stopPropagation
		>
			<!-- 뷰어 헤더 -->
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
				<div class="flex-1 min-w-0">
					<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 truncate">
						📄 {selectedDocument.title}
					</h2>
					<div class="flex items-center space-x-4 mt-1 text-sm text-gray-600 dark:text-gray-400">
						<span>👤 {selectedDocument.author}</span>
						<span>📅 {selectedDocument.date}</span>
						<span>📏 {selectedDocument.size}</span>
					</div>
				</div>
				<button
					on:click={closeDocumentViewer}
					class="ml-4 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- 문서 내용 -->
			<div class="flex-1 overflow-y-auto px-6 py-4 bg-gray-50 dark:bg-gray-900">
				{#if isLoadingDocument}
					<div class="flex items-center justify-center h-full">
						<div class="flex flex-col items-center space-y-3">
							<Spinner className="w-8 h-8" />
							<span class="text-gray-700 dark:text-gray-300">문서를 불러오는 중...</span>
						</div>
					</div>
				{:else}
					<pre class="whitespace-pre-wrap font-sans text-sm text-gray-800 dark:text-gray-200 leading-relaxed">{documentContent}</pre>
				{/if}
			</div>

			<!-- 뷰어 푸터 -->
			<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
				<div class="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
					<span class="px-2 py-1 rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
						{selectedDocument.type}
					</span>
					<span>•</span>
					<span>카테고리: {selectedDocument.category}</span>
				</div>
				<button
					on:click={closeDocumentViewer}
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
				>
					닫기
				</button>
			</div>
		</div>
	</div>
{/if}
