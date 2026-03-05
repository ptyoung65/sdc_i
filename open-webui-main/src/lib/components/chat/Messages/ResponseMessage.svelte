<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';

	import { createEventDispatcher } from 'svelte';
	import { onMount, tick, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType, t } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	const dispatch = createEventDispatcher();

	import { createNewFeedback, getFeedbackById, updateFeedbackById } from '$lib/apis/evaluations';
	import { getChatById } from '$lib/apis/chats';
	import { generateTags } from '$lib/apis';

	// [2026.01.19] modelColors, getModelColorClass 추가 - 모델별 색상 설정
	import { config, models, settings, temporaryChatEnabled, TTSWorker, user, modelColors, getModelColorClass } from '$lib/stores';
	import { synthesizeOpenAISpeech } from '$lib/apis/audio';
	import { imageGenerations } from '$lib/apis/images';
	import {
		copyToClipboard as _copyToClipboard,
		approximateToHumanReadable,
		getMessageContentParts,
		sanitizeResponseContent,
		createMessagesList,
		formatDate,
		removeDetails,
		removeAllDetails
	} from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Skeleton from './Skeleton.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import RateComment from './RateComment.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import WebSearchResults from './ResponseMessage/WebSearchResults.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';

	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Error from './Error.svelte';
	import Citations from './Citations.svelte';
	import CodeExecutions from './CodeExecutions.svelte';
	import ContentRenderer from './ContentRenderer.svelte';
	import { KokoroWorker } from '$lib/workers/KokoroWorker';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import EdmSearchResultsModal from '$lib/components/chat/EdmSearchResultsModal.svelte';
	import EdmFeedbackModal from '$lib/components/chat/EdmFeedbackModal.svelte';

	interface MessageType {
		id: string;
		model: string;
		content: string;
		files?: { type: string; url: string }[];
		timestamp: number;
		role: string;
		statusHistory?: {
			done: boolean;
			action: string;
			description: string;
			urls?: string[];
			query?: string;
		}[];
		status?: {
			done: boolean;
			action: string;
			description: string;
			urls?: string[];
			query?: string;
		};
		done: boolean;
		error?: boolean | { content: string };
		sources?: string[];
		code_executions?: {
			uuid: string;
			name: string;
			code: string;
			language?: string;
			result?: {
				error?: string;
				output?: string;
				files?: { name: string; url: string }[];
			};
		}[];
		info?: {
			openai?: boolean;
			prompt_tokens?: number;
			completion_tokens?: number;
			total_tokens?: number;
			eval_count?: number;
			eval_duration?: number;
			prompt_eval_count?: number;
			prompt_eval_duration?: number;
			total_duration?: number;
			load_duration?: number;
			usage?: unknown;
		};
		annotation?: { type: string; rating: number };
		isEdmResult?: boolean;
		edmFileList?: any[];
		edmData?: any[];
		feedback?: any;
	}

	export let chatId = '';
	export let history;
	export let messageId;

	let message: MessageType = JSON.parse(JSON.stringify(history.messages[messageId]));
	$: if (history.messages) {
		if (JSON.stringify(message) !== JSON.stringify(history.messages[messageId])) {
			message = JSON.parse(JSON.stringify(history.messages[messageId]));
		}
	}

	// ============================================
	// [2024.12.30] 화면 표시 - 토큰수/누적토큰수/누적턴수 계산 및 표시 시작
	// 역할: 채팅 화면에서 (토큰수: 357, 누적토큰수: 357, 누적턴수: 1) 형태로 표시
	// 데이터 소스: message.usage.total_tokens 또는 message.info.total_tokens
	// ============================================

	// 현재 메시지의 토큰수 (usage.total_tokens 또는 info.total_tokens)
	$: currentTokens = message?.usage?.total_tokens || message?.info?.total_tokens || message?.info?.eval_count || 0;

	// 누적 토큰수 및 누적 턴수 계산
	$: tokenStats = (() => {
		let accumulatedTokens = 0;
		let turnCount = 0;

		if (history?.messages) {
			// 메시지를 timestamp 순으로 정렬하여 순회
			const sortedMessages = Object.values(history.messages)
				.filter((msg: any) => msg.timestamp)
				.sort((a: any, b: any) => a.timestamp - b.timestamp);

			for (const msg of sortedMessages) {
				const msgAny = msg as any;
				// 토큰수 누적 (usage.total_tokens 또는 info.total_tokens)
				const msgTokens = msgAny?.usage?.total_tokens || msgAny?.info?.total_tokens || msgAny?.info?.eval_count || 0;
				accumulatedTokens += msgTokens;

				// 사용자 메시지일 때 턴수 증가
				if (msgAny.role === 'user') {
					turnCount++;
				}

				// 현재 메시지에 도달하면 중단
				if (msgAny.id === messageId) {
					break;
				}
			}
		}

		return { accumulatedTokens, turnCount };
	})();
	// [2024.12.30] 화면 표시 완료 ============================================

	// HTML 주석에서 EDM 파일 리스트 파싱
	function parseEdmFiles(content: string): any[] {
		try {
			const match = content.match(/<!--EDM_FILES:(.*?)-->/s);
			if (match && match[1]) {
				return JSON.parse(match[1]);
			}
		} catch (e) {
			console.error('EDM 파일 리스트 파싱 실패:', e);
		}
		return [];
	}

	// 메시지 내용에서 EDM 파일 리스트 추출
	$: edmFiles = message.content ? parseEdmFiles(message.content) : [];

	// EDM 파일 메타데이터 주석을 제거한 순수 메시지 내용 (화면 표시용)
	function removeEdmMetadata(content: string): string {
		if (!content) return content;
		// <!--EDM_FILES:....--> 형태의 주석 제거
		return content.replace(/<!--EDM_FILES:.*?-->/gs, '').trim();
	}

	// 화면에 표시될 순수 메시지 내용
	$: displayContent = removeEdmMetadata(message.content);

	// EDM 메시지 디버깅
	$: if (message.isEdmResult || message?.info?.edmFileList || message?.metadata?.edm_file_list) {
		console.log('🔵 [ResponseMessage] EDM 메시지 감지:', {
			id: message.id,
			isEdmResult: message.isEdmResult,
			edmFileList: message.edmFileList,
			edmData: message.edmData,
			infoEdmFileList: message?.info?.edmFileList,
			metadataEdmFileList: message?.metadata?.edm_file_list,
			fileCount: (message.edmFileList || message.edmData || message?.info?.edmFileList || message?.metadata?.edm_file_list || []).length
		});
	}

	export let siblings;

	export let gotoMessage: Function = () => {};
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;

	export let updateChat: Function;
	export let editMessage: Function;
	export let saveMessage: Function;
	export let rateMessage: Function;
	export let actionMessage: Function;
	export let deleteMessage: Function;

	export let submitMessage: Function;
	export let continueResponse: Function;
	export let regenerateResponse: Function;

	export let addMessages: Function;

	export let isLastMessage = true;
	export let readOnly = false;

	let buttonsContainerElement: HTMLDivElement;
	let showDeleteConfirm = false;

	let model = null;
	$: model = $models.find((m) => m.id === message.model);

	// [2026.01.19] 모델별 색상 - 스토어에서 설정 로드하여 사용 (설정 가능)

	let edit = false;
	let editedContent = '';
	let editTextAreaElement: HTMLTextAreaElement;

	let messageIndexEdit = false;

	let audioParts: Record<number, HTMLAudioElement | null> = {};
	let speaking = false;

	// EDM 모달 상태
	let showEdmSearchModal = false;
	let showEdmFeedbackModal = false;
	let showFileContentsModal = false;
	let selectedFileContents = { title: '', contents: [] };
	let speakingIdx: number | undefined;

	let loadingSpeech = false;
	let generatingImage = false;

	let showRateComment = false;
	let showNegativeFeedbackModal = false;
	let selectedFeedbackReason = '';
	let feedbackComment = '';

	const copyToClipboard = async (text) => {
		text = removeAllDetails(text);

		if (($config?.ui?.response_watermark ?? '').trim() !== '') {
			text = `${text}\n\n${$config?.ui?.response_watermark}`;
		}

		const res = await _copyToClipboard(text, $settings?.copyFormatted ?? false);
		if (res) {
			toast.success($i18n.t('Copying to clipboard was successful!'));
		}
	};

	const playAudio = (idx: number) => {
		return new Promise<void>((res) => {
			speakingIdx = idx;
			const audio = audioParts[idx];

			if (!audio) {
				return res();
			}

			audio.play();
			audio.onended = async () => {
				await new Promise((r) => setTimeout(r, 300));

				if (Object.keys(audioParts).length - 1 === idx) {
					speaking = false;
				}

				res();
			};
		});
	};

	const toggleSpeakMessage = async () => {
		if (speaking) {
			try {
				speechSynthesis.cancel();

				if (speakingIdx !== undefined && audioParts[speakingIdx]) {
					audioParts[speakingIdx]!.pause();
					audioParts[speakingIdx]!.currentTime = 0;
				}
			} catch {}

			speaking = false;
			speakingIdx = undefined;
			return;
		}

		if (!(message?.content ?? '').trim().length) {
			toast.info($i18n.t('No content to speak'));
			return;
		}

		speaking = true;

		const content = removeAllDetails(displayContent);

		if ($config.audio.tts.engine === '') {
			let voices = [];
			const getVoicesLoop = setInterval(() => {
				voices = speechSynthesis.getVoices();
				if (voices.length > 0) {
					clearInterval(getVoicesLoop);

					const voice =
						voices
							?.filter(
								(v) => v.voiceURI === ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
							)
							?.at(0) ?? undefined;

					console.log(voice);

					const speak = new SpeechSynthesisUtterance(content);
					speak.rate = $settings.audio?.tts?.playbackRate ?? 1;

					console.log(speak);

					speak.onend = () => {
						speaking = false;
						if ($settings.conversationMode) {
							document.getElementById('voice-input-button')?.click();
						}
					};

					if (voice) {
						speak.voice = voice;
					}

					speechSynthesis.speak(speak);
				}
			}, 100);
		} else {
			loadingSpeech = true;

			const messageContentParts: string[] = getMessageContentParts(
				content,
				$config?.audio?.tts?.split_on ?? 'punctuation'
			);

			if (!messageContentParts.length) {
				console.log('No content to speak');
				toast.info($i18n.t('No content to speak'));

				speaking = false;
				loadingSpeech = false;
				return;
			}

			console.debug('Prepared message content for TTS', messageContentParts);

			audioParts = messageContentParts.reduce(
				(acc, _sentence, idx) => {
					acc[idx] = null;
					return acc;
				},
				{} as typeof audioParts
			);

			let lastPlayedAudioPromise = Promise.resolve(); // Initialize a promise that resolves immediately

			if ($settings.audio?.tts?.engine === 'browser-kokoro') {
				if (!$TTSWorker) {
					await TTSWorker.set(
						new KokoroWorker({
							dtype: $settings.audio?.tts?.engineConfig?.dtype ?? 'fp32'
						})
					);

					await $TTSWorker.init();
				}

				for (const [idx, sentence] of messageContentParts.entries()) {
					const blob = await $TTSWorker
						.generate({
							text: sentence,
							voice: $settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice
						})
						.catch((error) => {
							console.error(error);
							toast.error(`${error}`);

							speaking = false;
							loadingSpeech = false;
						});

					if (blob) {
						const audio = new Audio(blob);
						audio.playbackRate = $settings.audio?.tts?.playbackRate ?? 1;

						audioParts[idx] = audio;
						loadingSpeech = false;
						lastPlayedAudioPromise = lastPlayedAudioPromise.then(() => playAudio(idx));
					}
				}
			} else {
				for (const [idx, sentence] of messageContentParts.entries()) {
					const res = await synthesizeOpenAISpeech(
						localStorage.token,
						$settings?.audio?.tts?.defaultVoice === $config.audio.tts.voice
							? ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
							: $config?.audio?.tts?.voice,
						sentence
					).catch((error) => {
						console.error(error);
						toast.error(`${error}`);

						speaking = false;
						loadingSpeech = false;
					});

					if (res) {
						const blob = await res.blob();
						const blobUrl = URL.createObjectURL(blob);
						const audio = new Audio(blobUrl);
						audio.playbackRate = $settings.audio?.tts?.playbackRate ?? 1;

						audioParts[idx] = audio;
						loadingSpeech = false;
						lastPlayedAudioPromise = lastPlayedAudioPromise.then(() => playAudio(idx));
					}
				}
			}
		}
	};

	let preprocessedDetailsCache = [];

	function preprocessForEditing(content: string): string {
		// Replace <details>...</details> with unique ID placeholder
		const detailsBlocks = [];
		let i = 0;

		content = content.replace(/<details[\s\S]*?<\/details>/gi, (match) => {
			detailsBlocks.push(match);
			return `<details id="__DETAIL_${i++}__"/>`;
		});

		// Store original blocks in the editedContent or globally (see merging later)
		preprocessedDetailsCache = detailsBlocks;

		return content;
	}

	function postprocessAfterEditing(content: string): string {
		const restoredContent = content.replace(
			/<details id="__DETAIL_(\d+)__"\/>/g,
			(_, index) => preprocessedDetailsCache[parseInt(index)] || ''
		);

		return restoredContent;
	}

	const editMessageHandler = async () => {
		edit = true;

		editedContent = preprocessForEditing(message.content);

		await tick();

		editTextAreaElement.style.height = '';
		editTextAreaElement.style.height = `${editTextAreaElement.scrollHeight}px`;
	};

	const editMessageConfirmHandler = async () => {
		const messageContent = postprocessAfterEditing(editedContent ? editedContent : '');
		editMessage(message.id, { content: messageContent }, false);

		edit = false;
		editedContent = '';

		await tick();
	};

	const saveAsCopyHandler = async () => {
		const messageContent = postprocessAfterEditing(editedContent ? editedContent : '');

		editMessage(message.id, { content: messageContent });

		edit = false;
		editedContent = '';

		await tick();
	};

	const cancelEditMessage = async () => {
		edit = false;
		editedContent = '';
		await tick();
	};

	const generateImage = async (message: MessageType) => {
		generatingImage = true;
		const res = await imageGenerations(localStorage.token, message.content).catch((error) => {
			toast.error(`${error}`);
		});
		console.log(res);

		if (res) {
			const files = res.map((image) => ({
				type: 'image',
				url: `${image.url}`
			}));

			saveMessage(message.id, {
				...message,
				files: files
			});
		}

		generatingImage = false;
	};

	let feedbackLoading = false;

	/**
	 * 🎯 완벽한 피드백 저장 핸들러 (UltraThink 최적화)
	 *
	 * @param rating - 평가 점수 (10: thumbs up, -1: thumbs down)
	 * @param details - 추가 세부정보 (reason, comment)
	 *
	 * 처리 흐름:
	 * 1. 낙관적 업데이트 (UI 즉시 반영)
	 * 2. 서버 저장 (재시도 로직 포함)
	 * 3. 검증 및 동기화
	 * 4. 태그 자동 생성 (rating 10 제외)
	 */
	const feedbackHandler = async (rating: number | null = null, details: object | null = null, retryCount = 0) => {
		const MAX_RETRIES = 3;
		feedbackLoading = true;

		console.log('📝 [feedbackHandler] 시작', {
			rating,
			details,
			retryCount,
			currentFeedbackId: message?.feedbackId,
			timestamp: new Date().toISOString()
		});

		try {
			// ========================================
			// 1️⃣ 낙관적 업데이트: UI 즉시 반영
			// ========================================
			const updatedMessage = {
				...message,
				annotation: {
					...(message?.annotation ?? {}),
					...(rating !== null ? { rating: rating } : {}),
					...(details ? details : {})
				}
			};

			// 즉시 UI 업데이트 (낙관적)
			if (history.messages[message.id]) {
				history.messages[message.id] = {
					...history.messages[message.id],
					annotation: updatedMessage.annotation
				};
			}
			message = { ...message, annotation: updatedMessage.annotation };

			// ========================================
			// 2️⃣ 채팅 데이터 조회
			// ========================================
			const chat = await getChatById(localStorage.token, chatId).catch((error) => {
				console.error('❌ [feedbackHandler] 채팅 조회 실패:', error);
				toast.error($i18n.t('채팅 정보를 불러올 수 없습니다.'));
				return null;
			});

			if (!chat) {
				feedbackLoading = false;
				return;
			}

			const messages = createMessagesList(history, message.id);

			// ========================================
			// 3️⃣ 피드백 아이템 구성
			// ========================================
			let feedbackItem = {
				type: 'rating',
				data: {
					...(updatedMessage?.annotation ? updatedMessage.annotation : {}),
					model_id: message?.selectedModelId ?? message.model,
					...(history.messages[message.parentId].childrenIds.length > 1
						? {
								sibling_model_ids: history.messages[message.parentId].childrenIds
									.filter((id) => id !== message.id)
									.map((id) => history.messages[id]?.selectedModelId ?? history.messages[id].model)
							}
						: {})
				},
				meta: {
					arena: message ? message.arena : false,
					model_id: message.model,
					message_id: message.id,
					message_index: messages.length,
					chat_id: chatId
				},
				snapshot: {
					chat: chat
				}
			};

			const baseModels = [
				feedbackItem.data.model_id,
				...(feedbackItem.data.sibling_model_ids ?? [])
			].reduce((acc, modelId) => {
				const model = $models.find((m) => m.id === modelId);
				if (model) {
					acc[model.id] = model?.info?.base_model_id ?? null;
				} else {
					console.warn(`⚠️ [feedbackHandler] 모델 ID ${modelId}를 찾을 수 없습니다`);
				}
				return acc;
			}, {});
			feedbackItem.meta.base_models = baseModels;

			// ========================================
			// 4️⃣ 서버 저장 (재시도 로직 포함)
			// ========================================
			let feedback = null;
			let operationType = '';

			if (message?.feedbackId) {
				operationType = '업데이트';
				console.log('🔄 [feedbackHandler] 기존 피드백 업데이트 중', {
					feedbackId: message.feedbackId,
					rating,
					details
				});

				feedback = await updateFeedbackById(
					localStorage.token,
					message.feedbackId,
					feedbackItem
				).catch(async (error) => {
					console.error('❌ [feedbackHandler] 피드백 업데이트 실패:', error);

					// 재시도 로직
					if (retryCount < MAX_RETRIES) {
						console.log(`🔁 [feedbackHandler] 재시도 ${retryCount + 1}/${MAX_RETRIES}`);
						await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
						feedbackLoading = false;
						return feedbackHandler(rating, details, retryCount + 1);
					}

					return null;
				});

				if (!feedback) {
					console.error('❌ [feedbackHandler] 피드백 업데이트 실패 - null 반환');
					toast.error($i18n.t('피드백 저장에 실패했습니다. 다시 시도해주세요.'));
					feedbackLoading = false;
					return;
				}

				console.log('✅ [feedbackHandler] 피드백 업데이트 완료', {
					feedbackId: feedback.id,
					rating: feedbackItem.data.rating,
					reason: feedbackItem.data.reason,
					comment: feedbackItem.data.comment
				});

			} else {
				operationType = '생성';
				console.log('➕ [feedbackHandler] 새 피드백 생성 중', {
					rating,
					details
				});

				feedback = await createNewFeedback(localStorage.token, feedbackItem).catch(async (error) => {
					console.error('❌ [feedbackHandler] 피드백 생성 실패:', error);

					// 재시도 로직
					if (retryCount < MAX_RETRIES) {
						console.log(`🔁 [feedbackHandler] 재시도 ${retryCount + 1}/${MAX_RETRIES}`);
						await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
						feedbackLoading = false;
						return feedbackHandler(rating, details, retryCount + 1);
					}

					return null;
				});

				if (!feedback) {
					console.error('❌ [feedbackHandler] 피드백 생성 실패 - null 반환');
					toast.error($i18n.t('피드백 저장에 실패했습니다. 다시 시도해주세요.'));
					feedbackLoading = false;
					return;
				}

				console.log('✅ [feedbackHandler] 피드백 생성 성공', {
					feedbackId: feedback.id,
					rating: feedbackItem.data.rating
				});

				// 새로 생성된 feedbackId 저장
				updatedMessage.feedbackId = feedback.id;
			}

			// ========================================
			// 5️⃣ 영속성 보장: 다중 레이어 저장
			// ========================================
			console.log('💾 [feedbackHandler] 다중 레이어 저장 시작', {
				feedbackId: updatedMessage.feedbackId,
				rating: updatedMessage.annotation.rating,
				reason: updatedMessage.annotation.reason,
				comment: updatedMessage.annotation.comment
			});

			// Layer 1: history.messages 직접 업데이트
			if (history.messages[message.id]) {
				history.messages[message.id] = {
					...history.messages[message.id],
					...updatedMessage,
					feedbackId: updatedMessage.feedbackId
				};
			}

			// Layer 2: saveMessage (localStorage/DB 저장)
			saveMessage(message.id, updatedMessage);

			// Layer 3: 로컬 message 객체 업데이트
			message = { ...updatedMessage };

			console.log('✅ [feedbackHandler] 다중 레이어 저장 완료', {
				historyMessagesFeedbackId: history.messages[message.id]?.feedbackId,
				localMessageFeedbackId: message.feedbackId,
				savedMessageFeedbackId: updatedMessage.feedbackId
			});

			await tick();

			// ========================================
			// 6️⃣ 태그 자동 생성 (thumbs down만)
			// ========================================
			if (!details && rating !== 10) {
				showRateComment = true;

				if (!updatedMessage.annotation?.tags) {
					console.log('🏷️ [feedbackHandler] 태그 자동 생성 시작...');

					const tags = await generateTags(localStorage.token, message.model, messages, chatId).catch(
						(error) => {
							console.error('❌ [feedbackHandler] 태그 생성 실패:', error);
							return [];
						}
					);

					if (tags && tags.length > 0) {
						console.log('✅ [feedbackHandler] 태그 생성 완료:', tags);

						updatedMessage.annotation.tags = tags;
						feedbackItem.data.tags = tags;

						if (history.messages[message.id]) {
							history.messages[message.id].annotation.tags = tags;
						}

						saveMessage(message.id, updatedMessage);

						await updateFeedbackById(
							localStorage.token,
							updatedMessage.feedbackId,
							feedbackItem
						).catch((error) => {
							console.error('❌ [feedbackHandler] 태그 업데이트 실패:', error);
						});
					}
				}
			}

			// ========================================
			// 7️⃣ 검증: 저장 확인
			// ========================================
			const savedFeedback = await getFeedbackById(localStorage.token, updatedMessage.feedbackId).catch((error) => {
				console.warn('⚠️ [feedbackHandler] 피드백 검증 실패 (무시 가능):', error);
				return null;
			});

			if (savedFeedback) {
				console.log('✅ [feedbackHandler] 저장 검증 성공', {
					feedbackId: savedFeedback.id,
					rating: savedFeedback.data?.rating,
					reason: savedFeedback.data?.reason,
					comment: savedFeedback.data?.comment
				});
			}

			// ========================================
			// 8️⃣ 완료
			// ========================================
			console.log('🎉 [feedbackHandler] 전체 프로세스 완료', {
				operation: operationType,
				feedbackId: updatedMessage.feedbackId,
				rating: updatedMessage.annotation.rating,
				reason: updatedMessage.annotation.reason,
				comment: updatedMessage.annotation.comment,
				timestamp: new Date().toISOString()
			});

			toast.success($i18n.t(rating === 10 ? '👍 긍정 평가가 저장되었습니다.' : '👎 부정 평가가 저장되었습니다.'));

		} catch (error) {
			console.error('❌ [feedbackHandler] 치명적 오류 발생:', error);
			toast.error($i18n.t('피드백 저장 중 오류가 발생했습니다. 다시 시도해주세요.'));
		} finally {
			feedbackLoading = false;
		}
	};

	const deleteMessageHandler = async () => {
		deleteMessage(message.id);
	};

	$: if (!edit) {
		(async () => {
			await tick();
		})();
	}

	onMount(async () => {
		// console.log('ResponseMessage mounted');

		await tick();
		if (buttonsContainerElement) {
			console.log(buttonsContainerElement);

			buttonsContainerElement.addEventListener('wheel', function (event) {
				if (buttonsContainerElement.scrollWidth <= buttonsContainerElement.clientWidth) {
					// If the container is not scrollable, horizontal scroll
					return;
				} else {
					event.preventDefault();

					if (event.deltaY !== 0) {
						// Adjust horizontal scroll position based on vertical scroll
						buttonsContainerElement.scrollLeft += event.deltaY;
					}
				}
			});
		}
	});
</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete message?')}
	on:confirm={() => {
		deleteMessageHandler();
	}}
/>

{#key message.id}
	<div
		class=" flex w-full message-{message.id}"
		id="message-{message.id}"
		dir={$settings.chatDirection}
	>
		{#if false}
			<!-- 프로필 아이콘 숨김 -->
			<div class={`shrink-0 ltr:mr-3 rtl:ml-3`}>
				<ProfileImage
					src={model?.info?.meta?.profile_image_url ??
						($i18n.language === 'dg-DG' ? `/doge.png` : `${WEBUI_BASE_URL}/static/favicon.png`)}
					className={'size-8'}
				/>
			</div>
		{/if}

		<div class="flex-auto w-0 pl-1 relative">
			<Name>
				<!-- [2026.01.19] 모델별 색상 표시 적용 -->
				<Tooltip content={model?.name ?? message.model} placement="top-start">
					<span class="line-clamp-1 font-semibold {getModelColorClass(model?.name ?? message.model, $modelColors)}">
						{model?.name ?? message.model}
					</span>
				</Tooltip>

				{#if message.timestamp}
					<div
						class=" self-center text-xs invisible group-hover:visible text-gray-400 font-medium first-letter:capitalize ml-0.5 translate-y-[1px]"
					>
						<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
							<span class="line-clamp-1">{dayjs(message.timestamp * 1000).format('YYYY년 MM월 DD일 HH:mm:ss')}</span>
						</Tooltip>
					</div>
				{/if}

				<!-- ============================================ -->
				<!-- [2024.12.30] 턴 및 토큰수 제약처리 - 표시 UI 시작 -->
				<!-- 역할: 채팅 메시지에 토큰수/누적토큰수/누적턴수 표시 -->
				<!-- ============================================ -->
				<!-- 토큰수 및 턴수 정보 표시 -->
				<div class="self-center text-xs text-gray-400 font-medium ml-2 translate-y-[1px] whitespace-nowrap">
					<Tooltip content="토큰수: 현재 메시지 / 누적: 이전 메시지까지의 합계 / 턴수: 사용자 질문 횟수">
						<span class="text-gray-500 dark:text-gray-400">
							(토큰수: <span class="text-blue-500">{currentTokens.toLocaleString()}</span>,
							누적토큰수: <span class="text-green-500">{tokenStats.accumulatedTokens.toLocaleString()}</span>,
							누적턴수: <span class="text-orange-500">{tokenStats.turnCount}</span>)
						</span>
					</Tooltip>
				</div>
				<!-- [2024.12.30] 턴 및 토큰수 제약처리 - 표시 UI 완료 ============================================ -->
			</Name>

			<div>
				<div class="chat-{message.role} w-full min-w-full markdown-prose">
					<div>
						{#if (message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]).length > 0}
							{@const status = (
								message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]
							).at(-1)}
							{#if !status?.hidden}
								<div class="status-description flex items-center gap-2 py-0.5">
									{#if status?.action === 'web_search' && status?.urls}
										<WebSearchResults {status}>
											<div class="flex flex-col justify-center -space-y-0.5">
												<div
													class="{status?.done === false
														? 'shimmer'
														: ''} text-base line-clamp-1 text-wrap"
												>
													<!-- $i18n.t("Generating search query") -->
													<!-- $i18n.t("No search query generated") -->

													<!-- $i18n.t('Searched {{count}} sites') -->
													{#if status?.description.includes('{{count}}')}
														{$i18n.t(status?.description, {
															count: status?.urls.length
														})}
													{:else if status?.description === 'No search query generated'}
														{$i18n.t('No search query generated')}
													{:else if status?.description === 'Generating search query'}
														{$i18n.t('Generating search query')}
													{:else}
														{status?.description}
													{/if}
												</div>
											</div>
										</WebSearchResults>
									{:else if status?.action === 'knowledge_search'}
										<div class="flex flex-col justify-center -space-y-0.5">
											<div
												class="{status?.done === false
													? 'shimmer'
													: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
											>
												{$i18n.t(`Searching Knowledge for "{{searchQuery}}"`, {
													searchQuery: status.query
												})}
											</div>
										</div>
									{:else}
										<div class="flex flex-col justify-center -space-y-0.5">
											<div
												class="{status?.done === false
													? 'shimmer'
													: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
											>
												<!-- $i18n.t(`Searching "{{searchQuery}}"`) -->
												{#if status?.description.includes('{{searchQuery}}')}
													{$i18n.t(status?.description, {
														searchQuery: status?.query
													})}
												{:else if status?.description === 'No search query generated'}
													{$i18n.t('No search query generated')}
												{:else if status?.description === 'Generating search query'}
													{$i18n.t('Generating search query')}
												{:else if status?.description === 'Searching the web'}
													{$i18n.t('Searching the web...')}
												{:else}
													{status?.description}
												{/if}
											</div>
										</div>
									{/if}
								</div>
							{/if}
						{/if}

						{#if message?.files && message.files?.filter((f) => f.type === 'image').length > 0}
							<div class="my-1 w-full flex overflow-x-auto gap-2 flex-wrap">
								{#each message.files as file}
									<div>
										{#if file.type === 'image'}
											<Image src={file.url} alt={message.content} />
										{:else}
											<FileItem
												item={file}
												url={file.url}
												name={file.name}
												type={file.type}
												size={file?.size}
												colorClassName="bg-white dark:bg-gray-850 "
											/>
										{/if}
									</div>
								{/each}
							</div>
						{/if}

						{#if edit === true}
							<div class="w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-5 py-3 my-2">
								<textarea
									id="message-edit-{message.id}"
									bind:this={editTextAreaElement}
									class=" bg-transparent outline-hidden w-full resize-none"
									bind:value={editedContent}
									on:input={(e) => {
										e.target.style.height = '';
										e.target.style.height = `${e.target.scrollHeight}px`;
									}}
									on:keydown={(e) => {
										if (e.key === 'Escape') {
											document.getElementById('close-edit-message-button')?.click();
										}

										const isCmdOrCtrlPressed = e.metaKey || e.ctrlKey;
										const isEnterPressed = e.key === 'Enter';

										if (isCmdOrCtrlPressed && isEnterPressed) {
											document.getElementById('confirm-edit-message-button')?.click();
										}
									}}
								/>

								<div class=" mt-2 mb-1 flex justify-between text-sm font-medium">
									<div>
										<button
											id="save-new-message-button"
											class=" px-4 py-2 bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-100 dark:border-gray-700 text-gray-700 dark:text-gray-200 transition rounded-3xl"
											on:click={() => {
												saveAsCopyHandler();
											}}
										>
											{$i18n.t('Save As Copy')}
										</button>
									</div>

									<div class="flex space-x-1.5">
										<button
											id="close-edit-message-button"
											class="px-4 py-2 bg-white dark:bg-gray-900 hover:bg-gray-100 text-gray-800 dark:text-gray-100 transition rounded-3xl"
											on:click={() => {
												cancelEditMessage();
											}}
										>
											{$i18n.t('Cancel')}
										</button>

										<button
											id="confirm-edit-message-button"
											class=" px-4 py-2 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
											on:click={() => {
												editMessageConfirmHandler();
											}}
										>
											{$i18n.t('Save')}
										</button>
									</div>
								</div>
							</div>
						{:else}
							<div class="w-full flex flex-col relative" id="response-content-container">
								{#if message.content === '' && !message.error && (message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]).length === 0}
									<Skeleton />
								{:else if message.content && message.error !== true}
									<!-- always show message contents even if there's an error -->
									<!-- unless message.error === true which is legacy error handling, where the error message is stored in message.content -->
									<ContentRenderer
										id={message.id}
										{history}
										content={displayContent}
										sources={message.sources}
										floatingButtons={message?.done && !readOnly}
										save={!readOnly}
										preview={!readOnly}
										{model}
										onTaskClick={async (e) => {
											console.log(e);
										}}
										onSourceClick={async (id, idx) => {
											console.log(id, idx);
											let sourceButton = document.getElementById(`source-${message.id}-${idx}`);
											const sourcesCollapsible = document.getElementById(
												`collapsible-${message.id}`
											);

											if (sourceButton) {
												sourceButton.click();
											} else if (sourcesCollapsible) {
												// Open sources collapsible so we can click the source button
												sourcesCollapsible
													.querySelector('div:first-child')
													.dispatchEvent(new PointerEvent('pointerup', {}));

												// Wait for next frame to ensure DOM updates
												await new Promise((resolve) => {
													requestAnimationFrame(() => {
														requestAnimationFrame(resolve);
													});
												});

												// Try clicking the source button again
												sourceButton = document.getElementById(`source-${message.id}-${idx}`);
												sourceButton && sourceButton.click();
											}
										}}
										onAddMessages={({ modelId, parentId, messages }) => {
											addMessages({ modelId, parentId, messages });
										}}
										onSave={({ raw, oldContent, newContent }) => {
											history.messages[message.id].content = history.messages[
												message.id
											].content.replace(raw, raw.replace(oldContent, newContent));

											updateChat();
										}}
									/>
								{/if}

								{#if message?.error}
									<Error content={message?.error?.content ?? message.content} />
								{/if}

								{#if (message?.sources || message?.citations) && (model?.info?.meta?.capabilities?.citations ?? true)}
									<Citations id={message?.id} sources={message?.sources ?? message?.citations} />
								{/if}

								{#if message.code_executions}
									<CodeExecutions codeExecutions={message.code_executions} />
								{/if}
							</div>
						{/if}
					</div>
				</div>

				{#if !edit}
					<div
						bind:this={buttonsContainerElement}
						class="flex justify-start overflow-x-auto buttons text-gray-600 dark:text-gray-500 mt-0.5"
					>
						{#if message.done || siblings.length > 1}
							{#if false}
							{#if siblings.length > 1}
								<div class="flex self-center min-w-fit" dir="ltr">
									<button
										class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
										on:click={() => {
											showPreviousMessage(message);
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
											stroke-width="2.5"
											class="size-3.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.75 19.5 8.25 12l7.5-7.5"
											/>
										</svg>
									</button>

									{#if messageIndexEdit}
										<div
											class="text-sm flex justify-center font-semibold self-center dark:text-gray-100 min-w-fit"
										>
											<input
												id="message-index-input-{message.id}"
												type="number"
												value={siblings.indexOf(message.id) + 1}
												min="1"
												max={siblings.length}
												on:focus={(e) => {
													e.target.select();
												}}
												on:blur={(e) => {
													gotoMessage(message, e.target.value - 1);
													messageIndexEdit = false;
												}}
												on:keydown={(e) => {
													if (e.key === 'Enter') {
														gotoMessage(message, e.target.value - 1);
														messageIndexEdit = false;
													}
												}}
												class="bg-transparent font-semibold self-center dark:text-gray-100 min-w-fit outline-hidden"
											/>/{siblings.length}
										</div>
									{:else}
										<!-- svelte-ignore a11y-no-static-element-interactions -->
										<div
											class="text-sm tracking-widest font-semibold self-center dark:text-gray-100 min-w-fit"
											on:dblclick={async () => {
												messageIndexEdit = true;

												await tick();
												const input = document.getElementById(`message-index-input-${message.id}`);
												if (input) {
													input.focus();
													input.select();
												}
											}}
										>
											{siblings.indexOf(message.id) + 1}/{siblings.length}
										</div>
									{/if}

									<button
										class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
										on:click={() => {
											showNextMessage(message);
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
											stroke-width="2.5"
											class="size-3.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="m8.25 4.5 7.5 7.5-7.5 7.5"
											/>
										</svg>
									</button>
								</div>
							{/if}
							{/if}

							{#if message.done}
								{#if !readOnly}
									{#if false}
									{#if $user?.role === 'user' ? ($user?.permissions?.chat?.edit ?? true) : true}
										<Tooltip content={$i18n.t('Edit')} placement="bottom">
											<button
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
												on:click={() => {
													editMessageHandler();
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}
									{/if}
								{/if}

								{#if false}
								<Tooltip content={$i18n.t('Copy')} placement="bottom">
									<button
										class="{isLastMessage
											? 'visible'
											: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition copy-response-button"
										on:click={() => {
											copyToClipboard(displayContent);
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="2.3"
											stroke="currentColor"
											class="w-4 h-4"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
											/>
										</svg>
									</button>
								</Tooltip>
								{/if}

								{#if false}
								{#if $user?.role === 'admin' || ($user?.permissions?.chat?.tts ?? true)}
									<Tooltip content={$i18n.t('Read Aloud')} placement="bottom">
										<button
											id="speak-button-{message.id}"
											class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
											on:click={() => {
												if (!loadingSpeech) {
													toggleSpeakMessage();
												}
											}}
										>
											{#if loadingSpeech}
												<svg
													class=" w-4 h-4"
													fill="currentColor"
													viewBox="0 0 24 24"
													xmlns="http://www.w3.org/2000/svg"
												>
													<style>
														.spinner_S1WN {
															animation: spinner_MGfb 0.8s linear infinite;
															animation-delay: -0.8s;
														}

														.spinner_Km9P {
															animation-delay: -0.65s;
														}

														.spinner_JApP {
															animation-delay: -0.5s;
														}

														@keyframes spinner_MGfb {
															93.75%,
															100% {
																opacity: 0.2;
															}
														}
													</style>
													<circle class="spinner_S1WN" cx="4" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_Km9P" cx="12" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_JApP" cx="20" cy="12" r="3" />
												</svg>
											{:else if speaking}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
													/>
												</svg>
											{:else}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z"
													/>
												</svg>
											{/if}
										</button>
									</Tooltip>
								{/if}
								{/if}

								{#if false}
								{#if $config?.features.enable_image_generation && ($user?.role === 'admin' || $user?.permissions?.features?.image_generation) && !readOnly}
									<Tooltip content={$i18n.t('Generate Image')} placement="bottom">
										<button
											class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'}  p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
											on:click={() => {
												if (!generatingImage) {
													generateImage(message);
												}
											}}
										>
											{#if generatingImage}
												<svg
													class=" w-4 h-4"
													fill="currentColor"
													viewBox="0 0 24 24"
													xmlns="http://www.w3.org/2000/svg"
												>
													<style>
														.spinner_S1WN {
															animation: spinner_MGfb 0.8s linear infinite;
															animation-delay: -0.8s;
														}

														.spinner_Km9P {
															animation-delay: -0.65s;
														}

														.spinner_JApP {
															animation-delay: -0.5s;
														}

														@keyframes spinner_MGfb {
															93.75%,
															100% {
																opacity: 0.2;
															}
														}
													</style>
													<circle class="spinner_S1WN" cx="4" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_Km9P" cx="12" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_JApP" cx="20" cy="12" r="3" />
												</svg>
											{:else}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
													/>
												</svg>
											{/if}
										</button>
									</Tooltip>
								{/if}
								{/if}

								{#if false}
								{#if message.usage}
									<Tooltip
										content={message.usage
											? `<pre>${sanitizeResponseContent(
													JSON.stringify(message.usage, null, 2)
														.replace(/"([^(")"]+)":/g, '$1:')
														.slice(1, -1)
														.split('\n')
														.map((line) => line.slice(2))
														.map((line) => (line.endsWith(',') ? line.slice(0, -1) : line))
														.join('\n')
												)}</pre>`
											: ''}
										placement="bottom"
									>
										<button
											class=" {isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition whitespace-pre-wrap"
											on:click={() => {
												// ========== [2026-01-27 시스템 프롬프트 노출 방지] 시작 ==========
												// console.log(message); // 보안: 메시지 콘솔 노출 제거
												// ========== [2026-01-27 시스템 프롬프트 노출 방지] 종료 ==========
											}}
											id="info-{message.id}"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2.3"
												stroke="currentColor"
												class="w-4 h-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}
								{/if}

								{#if !readOnly}
									{#if !$temporaryChatEnabled && ($config?.features.enable_message_rating ?? true)}
										<!-- Copy Button -->
										<Tooltip content={$i18n.t('Copy')} placement="bottom">
											<button
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition copy-response-button"
												on:click={() => {
													copyToClipboard(displayContent);
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
													/>
												</svg>
											</button>
										</Tooltip>

										<!-- Thumbs Up Button -->
										<Tooltip content={$i18n.t('Good Response')} placement="bottom">
											<button
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg {(
													message?.annotation?.rating ?? ''
												).toString() === '10'
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} dark:hover:text-white hover:text-black transition disabled:cursor-progress disabled:hover:bg-transparent"
												disabled={feedbackLoading}
												on:click={async () => {
													console.log('👍 [Thumbs Up] 클릭', {
														feedbackId: message?.feedbackId,
														currentRating: message?.annotation?.rating
													});

													// 이미 thumbs up 상태인지 확인
													if (message?.annotation?.rating === 10) {
														console.log('ℹ️ [Thumbs Up] 이미 긍정 평가된 메시지입니다.');
														toast.info($i18n.t('이미 긍정 평가하셨습니다.'));
														return;
													}

													await feedbackHandler(10);
													console.log('✅ [Thumbs Up] 처리 완료');

													window.setTimeout(() => {
														document
															.getElementById(`message-feedback-${message.id}`)
															?.scrollIntoView();
													}, 0);
												}}
											>
												<svg
													stroke="currentColor"
													fill="none"
													stroke-width="2.3"
													viewBox="0 0 24 24"
													stroke-linecap="round"
													stroke-linejoin="round"
													class="w-4 h-4"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"
													/>
												</svg>
											</button>
										</Tooltip>

										<Tooltip content={$i18n.t('Bad Response')} placement="bottom">
											<button
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg {(
													message?.annotation?.rating ?? ''
												).toString() === '1'
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} dark:hover:text-white hover:text-black transition disabled:cursor-progress disabled:hover:bg-transparent"
												disabled={feedbackLoading}
												on:click={async () => {
													// thumbs down: 커스텀 피드백 모달 표시
													console.log('🔍 [Thumbs Down] 클릭', {
														feedbackId: message?.feedbackId,
														currentRating: message?.annotation?.rating,
														currentReason: message?.annotation?.reason,
														currentComment: message?.annotation?.comment
													});

													// 기존 평가 데이터 불러오기 (재클릭 시)
													if (message?.annotation?.rating === 1) {
														selectedFeedbackReason = message?.annotation?.reason || '';
														feedbackComment = message?.annotation?.comment || '';
														console.log('✅ [Thumbs Down] 기존 평가 데이터 로드:', {
															reason: selectedFeedbackReason,
															comment: feedbackComment
														});
													} else {
														// 새 평가: 초기화
														selectedFeedbackReason = '';
														feedbackComment = '';
													}

													showNegativeFeedbackModal = true;
												}}
											>
												<svg
													stroke="currentColor"
													fill="none"
													stroke-width="2.3"
													viewBox="0 0 24 24"
													stroke-linecap="round"
													stroke-linejoin="round"
													class="w-4 h-4"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 6 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"
													/>
												</svg>
											</button>
										</Tooltip>

										<!-- AI 안내 문구 -->
										<div class="flex items-center ml-3">
											<svg class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 mr-1.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
											<span class="text-xs text-gray-400 dark:text-gray-500 leading-tight">
												생성형 AI는 부정확한 내용을 답변할 가능성이 있으므로 검토 후 활용하세요.
											</span>
										</div>
									{/if}

									{#if false}
									{#if isLastMessage}
										<Tooltip content={$i18n.t('Continue Response')} placement="bottom">
											<button
												type="button"
												id="continue-response-button"
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
												on:click={() => {
													continueResponse();
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
													/>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}

									<Tooltip content={$i18n.t('Regenerate')} placement="bottom">
										<button
											type="button"
											class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
											on:click={() => {
												showRateComment = false;
												regenerateResponse(message);

												(model?.actions ?? []).forEach((action) => {
													dispatch('action', {
														id: action.id,
														event: {
															id: 'regenerate-response',
															data: {
																messageId: message.id
															}
														}
													});
												});
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2.3"
												stroke="currentColor"
												class="w-4 h-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
												/>
											</svg>
										</button>
									</Tooltip>

									{#if siblings.length > 1}
										<Tooltip content={$i18n.t('Delete')} placement="bottom">
											<button
												type="button"
												id="delete-response-button"
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
												on:click={() => {
													showDeleteConfirm = true;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}

									{#if isLastMessage}
										{#each model?.actions ?? [] as action}
											<Tooltip content={action.name} placement="bottom">
												<button
													type="button"
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
													on:click={() => {
														actionMessage(action.id, message);
													}}
												>
													{#if action?.icon}
														<div class="size-4">
															<img
																src={action.icon}
																class="w-4 h-4 {action.icon.includes('svg')
																	? 'dark:invert-[80%]'
																	: ''}"
																style="fill: currentColor;"
																alt={action.name}
															/>
														</div>
													{:else}
														<Sparkles strokeWidth="2.1" className="size-4" />
													{/if}
												</button>
											</Tooltip>
										{/each}
									{/if}
									{/if}
								{/if}
							{/if}
						{/if}
					</div>

					{#if message.done && showRateComment}
						<RateComment
							bind:message
							bind:show={showRateComment}
							on:save={async (e) => {
								await feedbackHandler(null, {
									...e.detail
								});
							}}
						/>
					{/if}

					<!-- EDM 검색 결과 버튼 및 평가 버튼 -->
					{#if edmFiles.length > 0 || (message.isEdmResult && (message.edmFileList || message.edmData)) || message?.info?.edmFileList || message?.metadata?.edm_file_list}
						{@const fileList = edmFiles.length > 0 ? edmFiles : (message.edmFileList || message.edmData || message?.info?.edmFileList || message?.metadata?.edm_file_list || [])}
						<!-- EDM 검색결과 버튼 -->
						<div class="mt-3">
							<button
								data-testid="edm-file-list-button"
								on:click={() => {
									console.log('🔵 [ResponseMessage] EDM 파일 검색 버튼 클릭:', {
										messageId: message.id,
										filesCount: fileList.length
									});
									dispatch('openEdmFileList', { files: fileList });
								}}
								class="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-all duration-200 shadow-sm hover:shadow-md border border-gray-300 dark:border-gray-600"
								type="button"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
								</svg>
								<span>EDM 검색결과</span>
								<span class="px-2 py-0.5 bg-gray-200 dark:bg-gray-600 rounded-full text-xs font-semibold">
									{fileList.length}건
								</span>
							</button>
						</div>
					{/if}
				{/if}
			</div>

			{#if message?.done}
				<div aria-live="polite" class="sr-only">
					{message?.content ?? ''}
				</div>
			{/if}
		</div>
	</div>
{/key}

<!-- EDM 검색 결과 모달 -->
{#if showEdmSearchModal}
	{@const edmResults = message?.edmFileList || message?.edmData || message?.info?.edmFileList || []}
	{#if edmResults.length > 0}
		<EdmSearchResultsModal bind:show={showEdmSearchModal} results={edmResults} />
	{/if}
{/if}

<!-- EDM 피드백 모달 -->
{#if showEdmFeedbackModal}
	<EdmFeedbackModal
		messageId={message.id}
		on:close={() => {
			console.log('🔵 [ResponseMessage] EDM 피드백 모달 닫기');
			showEdmFeedbackModal = false;
		}}
		on:submit={(e) => {
			console.log('🔵 [ResponseMessage] EDM 피드백 제출:', e.detail);
			showEdmFeedbackModal = false;
			toast.success($i18n.t('피드백이 전송되었습니다.'));
		}}
	/>
{/if}

<!-- 부정 피드백 모달 (OpenWebUI 스타일) -->
{#if showNegativeFeedbackModal}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="fixed top-0 right-0 left-0 bottom-0 bg-black/60 w-full h-screen max-h-[100dvh] flex justify-center z-50 overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showNegativeFeedbackModal = false;
		}}
	>
		<div
			class="m-auto max-w-full w-[32rem] mx-2 bg-white/95 dark:bg-gray-950/95 backdrop-blur-sm rounded-4xl max-h-[100dvh] shadow-3xl border border-white dark:border-gray-900"
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<div class="px-[1.75rem] py-6 flex flex-col">
				<!-- 모달 제목 -->
				<div class="text-lg font-medium dark:text-gray-200 mb-4">
					{$i18n.t('피드백 보내기')}
				</div>

				<!-- 불만족 유형 선택 -->
				<div class="mb-4">
					<div class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						{$i18n.t('불만족 유형을 선택하거나 의견을 작성해주세요')} <span class="text-gray-400">(선택 사항)</span>
					</div>
					<div class="flex flex-wrap gap-1.5 text-sm">
						<button
							class="px-3 py-1.5 border border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850 {selectedFeedbackReason ===
							'질문과 답변의 관련성이 낮음'
								? 'bg-gray-100 dark:bg-gray-800'
								: ''} transition rounded-xl"
							on:click={() => {
								selectedFeedbackReason = '질문과 답변의 관련성이 낮음';
							}}
							type="button"
						>
							질문과 답변의 관련성이 낮음
						</button>
						<button
							class="px-3 py-1.5 border border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850 {selectedFeedbackReason ===
							'사실과 다르거나 오류가 있음'
								? 'bg-gray-100 dark:bg-gray-800'
								: ''} transition rounded-xl"
							on:click={() => {
								selectedFeedbackReason = '사실과 다르거나 오류가 있음';
							}}
							type="button"
						>
							사실과 다르거나 오류가 있음
						</button>
						<button
							class="px-3 py-1.5 border border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850 {selectedFeedbackReason ===
							'지시한 조건이나 형식을 무시함'
								? 'bg-gray-100 dark:bg-gray-800'
								: ''} transition rounded-xl"
							on:click={() => {
								selectedFeedbackReason = '지시한 조건이나 형식을 무시함';
							}}
							type="button"
						>
							지시한 조건이나 형식을 무시함
						</button>
						<button
							class="px-3 py-1.5 border border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850 {selectedFeedbackReason ===
							'도움이 되지 않음'
								? 'bg-gray-100 dark:bg-gray-800'
								: ''} transition rounded-xl"
							on:click={() => {
								selectedFeedbackReason = '도움이 되지 않음';
							}}
							type="button"
						>
							도움이 되지 않음
						</button>
					</div>
				</div>

				<!-- 상세 의견 입력 -->
				<div class="mb-6">
					<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
						{$i18n.t('선택한 불만족 유형에 대한 상세한 설명을 작성해주세요')}
					</div>
					<textarea
						bind:value={feedbackComment}
						class="w-full text-sm px-3 py-2 bg-transparent border border-gray-100 dark:border-gray-850 outline-none resize-none rounded-xl dark:text-gray-100"
						placeholder={$i18n.t('구체적인 피드백을 작성해주세요...')}
						rows="4"
					/>
				</div>

				<!-- 버튼 -->
				<div class="flex justify-between gap-1.5">
					<button
						class="text-sm bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white font-medium w-full py-2 rounded-3xl transition"
						on:click={() => {
							showNegativeFeedbackModal = false;
							selectedFeedbackReason = '';
							feedbackComment = '';
						}}
						type="button"
					>
						{$i18n.t('취소')}
					</button>
					<button
						class="text-sm bg-gray-900 hover:bg-gray-850 text-gray-100 dark:bg-gray-100 dark:hover:bg-white dark:text-gray-800 font-medium w-full py-2 rounded-3xl transition disabled:opacity-50 disabled:cursor-not-allowed"
						disabled={(!selectedFeedbackReason && !feedbackComment) || feedbackLoading}
						on:click={async () => {
							// 분류를 선택하지 않으면 '기타'로 자동 설정
							const finalReason = selectedFeedbackReason || '기타';

							// 부정 피드백 저장
							console.log('👎 [Thumbs Down] 부정 피드백 저장 시작:', {
								rating: 1,
								reason: finalReason,
								comment: feedbackComment
							});

							await feedbackHandler(1, {
								reason: finalReason,
								comment: feedbackComment
							});

							console.log('👎 [Thumbs Down] 처리 완료');

							showNegativeFeedbackModal = false;

							// 초기화
							selectedFeedbackReason = '';
							feedbackComment = '';
						}}
						type="button"
					>
						{feedbackLoading ? $i18n.t('전송 중...') : $i18n.t('제출')}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- 파일 목록 팝업 모달 (Open WebUI 스타일) -->
{#if showFileContentsModal}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
		on:click={() => showFileContentsModal = false}
		on:keydown={(e) => e.key === 'Escape' && (showFileContentsModal = false)}
		role="dialog"
		aria-modal="true"
		aria-labelledby="file-contents-modal-title"
	>
		<div
			class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-4xl w-full mx-4 max-h-[85vh] flex flex-col border border-gray-200 dark:border-gray-700"
			role="document"
			on:click|stopPropagation
			on:keydown|stopPropagation
		>
			<!-- Header -->
			<div class="flex items-center justify-between p-6 pb-4 border-b dark:border-gray-800">
				<div>
					<h2 id="file-contents-modal-title" class="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
						<svg class="w-7 h-7 text-blue-600 dark:text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
						</svg>
						{selectedFileContents.title}
					</h2>
					<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
						총 <span class="font-semibold">{selectedFileContents.contents.length}</span>개 항목
					</p>
				</div>
				<button
					on:click={() => showFileContentsModal = false}
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
					aria-label="닫기"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
					</svg>
				</button>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-y-auto p-6 bg-gray-50/50 dark:bg-gray-900/30">
				{#if selectedFileContents.contents.length === 0}
					<div class="text-center py-20">
						<svg class="mx-auto w-16 h-16 text-gray-400 dark:text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
						</svg>
						<p class="text-lg font-medium text-gray-500 dark:text-gray-400">목록이 비어있습니다</p>
					</div>
				{:else}
					<div class="space-y-3">
						{#each selectedFileContents.contents as item, index}
							<div class="flex items-start gap-4 p-5 rounded-xl bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-md transition-all duration-200">
								<div class="flex-shrink-0 w-9 h-9 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center text-blue-700 dark:text-blue-300 font-bold text-sm">
									{index + 1}
								</div>
								<div class="flex-1 min-w-0 pt-1">
									<p class="text-gray-900 dark:text-white leading-relaxed">
										{item}
									</p>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-between px-6 py-5 border-t dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
				<div class="text-sm text-gray-600 dark:text-gray-400">
					<span class="font-medium">{selectedFileContents.contents.length}개 항목 표시 중</span>
				</div>
				<button
					on:click={() => showFileContentsModal = false}
					class="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700 transition-all duration-200 hover:shadow-sm"
				>
					닫기
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.buttons::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.buttons {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
