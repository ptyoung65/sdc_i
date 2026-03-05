import { EventSourceParserStream } from 'eventsource-parser/stream';
import type { ParsedEvent } from 'eventsource-parser';

// ----- [2026-02-05] LLM 응답 ID 트레이싱 기능 시작 -----
type TextStreamUpdate = {
	done: boolean;
	value: string;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	sources?: any;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	selectedModelId?: any;
	error?: any;
	usage?: ResponseUsage;
	// LLM 응답 ID (예: chatcmpl-xxx) - 트레이싱용
	llmResponseId?: string;
	// LLM 모델명 (응답에서 반환된 실제 모델)
	llmModel?: string;
	// LLM 응답 생성 시간
	llmCreated?: number;
};
// ----- [2026-02-05] LLM 응답 ID 트레이싱 기능 종료 -----

type ResponseUsage = {
	/** Including images and tools if any */
	prompt_tokens: number;
	/** The tokens generated */
	completion_tokens: number;
	/** Sum of the above two fields */
	total_tokens: number;
	/** Any other fields that aren't part of the base OpenAI spec */
	[other: string]: unknown;
};

// createOpenAITextStream takes a responseBody with a SSE response,
// and returns an async generator that emits delta updates with large deltas chunked into random sized chunks
export async function createOpenAITextStream(
	responseBody: ReadableStream<Uint8Array>,
	splitLargeDeltas: boolean
): Promise<AsyncGenerator<TextStreamUpdate>> {
	const eventStream = responseBody
		.pipeThrough(new TextDecoderStream())
		.pipeThrough(new EventSourceParserStream())
		.getReader();
	let iterator = openAIStreamToIterator(eventStream);
	if (splitLargeDeltas) {
		iterator = streamLargeDeltasAsRandomChunks(iterator);
	}
	return iterator;
}

async function* openAIStreamToIterator(
	reader: ReadableStreamDefaultReader<ParsedEvent>
): AsyncGenerator<TextStreamUpdate> {
	while (true) {
		const { value, done } = await reader.read();
		if (done) {
			yield { done: true, value: '' };
			break;
		}
		if (!value) {
			continue;
		}
		const data = value.data;
		if (data.startsWith('[DONE]')) {
			yield { done: true, value: '' };
			break;
		}

		try {
			const parsedData = JSON.parse(data);
			// ========== [2026-01-27 시스템 프롬프트 노출 방지] 시작 ==========
			// console.log(parsedData); // 보안: 스트리밍 데이터 콘솔 노출 제거
			// ========== [2026-01-27 시스템 프롬프트 노출 방지] 종료 ==========

			if (parsedData.error) {
				yield { done: true, value: '', error: parsedData.error };
				break;
			}

			if (parsedData.sources) {
				yield { done: false, value: '', sources: parsedData.sources };
				continue;
			}

			if (parsedData.selected_model_id) {
				yield { done: false, value: '', selectedModelId: parsedData.selected_model_id };
				continue;
			}

			if (parsedData.usage) {
				yield { done: false, value: '', usage: parsedData.usage };
				continue;
			}

			// ----- [2026-02-05] LLM 응답 ID 추출 시작 -----
			// OpenAI 응답 형식: { id: "chatcmpl-xxx", model: "gpt-4", created: 1234567890, ... }
			const llmResponseId = parsedData.id || undefined;
			const llmModel = parsedData.model || undefined;
			const llmCreated = parsedData.created || undefined;
			// ----- [2026-02-05] LLM 응답 ID 추출 종료 -----

			yield {
				done: false,
				value: parsedData.choices?.[0]?.delta?.content ?? '',
				// ----- [2026-02-05] LLM 트레이싱 정보 전달 시작 -----
				...(llmResponseId && { llmResponseId }),
				...(llmModel && { llmModel }),
				...(llmCreated && { llmCreated })
				// ----- [2026-02-05] LLM 트레이싱 정보 전달 종료 -----
			};
		} catch (e) {
			console.error('Error extracting delta from SSE event:', e);
		}
	}
}

// streamLargeDeltasAsRandomChunks will chunk large deltas (length > 5) into random sized chunks between 1-3 characters
// This is to simulate a more fluid streaming, even though some providers may send large chunks of text at once
async function* streamLargeDeltasAsRandomChunks(
	iterator: AsyncGenerator<TextStreamUpdate>
): AsyncGenerator<TextStreamUpdate> {
	for await (const textStreamUpdate of iterator) {
		if (textStreamUpdate.done) {
			yield textStreamUpdate;
			return;
		}

		if (textStreamUpdate.error) {
			yield textStreamUpdate;
			continue;
		}
		if (textStreamUpdate.sources) {
			yield textStreamUpdate;
			continue;
		}
		if (textStreamUpdate.selectedModelId) {
			yield textStreamUpdate;
			continue;
		}
		if (textStreamUpdate.usage) {
			yield textStreamUpdate;
			continue;
		}
		// ----- [2026-02-05] LLM 응답 ID 전달 시작 -----
		if (textStreamUpdate.llmResponseId) {
			yield textStreamUpdate;
			continue;
		}
		// ----- [2026-02-05] LLM 응답 ID 전달 종료 -----

		let content = textStreamUpdate.value;
		if (content.length < 5) {
			yield { done: false, value: content };
			continue;
		}
		while (content != '') {
			const chunkSize = Math.min(Math.floor(Math.random() * 3) + 1, content.length);
			const chunk = content.slice(0, chunkSize);
			yield { done: false, value: chunk };
			// Do not sleep if the tab is hidden
			// Timers are throttled to 1s in hidden tabs
			if (document?.visibilityState !== 'hidden') {
				await sleep(5);
			}
			content = content.slice(chunkSize);
		}
	}
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
