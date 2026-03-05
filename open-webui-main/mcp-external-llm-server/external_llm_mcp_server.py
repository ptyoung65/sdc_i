#!/usr/bin/env python3
"""
Perplexity Search MCP Server
=============================
Open WebUI에서 Perplexity Search API를 호출하기 위한 MCP 서버
ChatGPT 없이 Perplexity Search 전용으로 동작

플로우:
Open WebUI → MCP Server → Perplexity Search API → MCP Server → Open WebUI
"""

import asyncio
import logging
import os
import json
from typing import Any, Optional, Dict, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx
import time
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Perplexity Search MCP Server", version="2.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경 변수에서 API 키 로드
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8100"))

# MCP 메시지 모델
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[dict] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    result: Optional[dict] = None
    error: Optional[dict] = None

# 사용 가능한 도구 목록 (Perplexity Search 전용)
TOOLS = [
    {
        "name": "perplexity_search",
        "description": "Perplexity Search API를 호출하여 실시간 웹 검색 기반 답변을 받습니다. 최신 정보가 필요하거나 특정 주제에 대한 검색이 필요할 때 사용합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색할 질문 또는 쿼리"
                },
                "model": {
                    "type": "string",
                    "description": "사용할 Perplexity 모델",
                    "enum": [
                        "llama-3.1-sonar-small-128k-online",
                        "llama-3.1-sonar-large-128k-online",
                        "llama-3.1-sonar-huge-128k-online"
                    ],
                    "default": "llama-3.1-sonar-small-128k-online"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "최대 응답 토큰 수",
                    "default": 1024
                },
                "temperature": {
                    "type": "number",
                    "description": "응답의 창의성 (0.0~2.0)",
                    "default": 0.2
                },
                "search_recency_filter": {
                    "type": "string",
                    "description": "검색 기간 필터",
                    "enum": ["hour", "day", "week", "month", "year"],
                    "default": "month"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_search_status",
        "description": "Perplexity Search API 연결 상태를 확인합니다",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


async def call_perplexity_search_api(
    query: str,
    model: str = "llama-3.1-sonar-small-128k-online",
    api_key: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    search_recency_filter: str = "month"
) -> Dict:
    """
    Perplexity Search API 호출
    """
    # API 키 결정
    key = api_key or PERPLEXITY_API_KEY

    if not key:
        return {
            "success": False,
            "error": "Perplexity API 키가 설정되지 않았습니다. PERPLEXITY_API_KEY 환경변수를 설정하세요."
        }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful search assistant. Provide accurate and concise answers based on web search results. Always include sources when available. 한국어로 답변해주세요."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "return_citations": True,
        "search_recency_filter": search_recency_filter
    }

    logger.info(f"🔍 Perplexity Search API 호출 시작")
    logger.info(f"   모델: {model}")
    logger.info(f"   쿼리: {query[:100]}...")

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']
                citations = result.get('citations', [])

                logger.info(f"✅ Perplexity Search 응답 성공 ({elapsed:.2f}초)")

                return {
                    "success": True,
                    "model": model,
                    "query": query,
                    "answer": answer,
                    "citations": citations,
                    "usage": result.get('usage', {}),
                    "response_time": elapsed
                }
            else:
                error_msg = f"API 오류: {response.status_code} - {response.text}"
                logger.error(f"❌ Perplexity API 실패: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

    except httpx.TimeoutException:
        error_msg = "API 요청 타임아웃 (60초)"
        logger.error(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"API 호출 오류: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}


def format_search_results(result: Dict) -> str:
    """검색 결과를 포맷팅"""
    output_lines = []

    # 답변
    answer = result.get("answer", "")
    if answer:
        output_lines.append("## Perplexity 검색 결과")
        output_lines.append("")
        output_lines.append(answer)
        output_lines.append("")

    # 출처
    citations = result.get("citations", [])
    if citations:
        output_lines.append("## 출처")
        output_lines.append("")
        for idx, citation in enumerate(citations, 1):
            if isinstance(citation, str):
                output_lines.append(f"{idx}. {citation}")
            elif isinstance(citation, dict):
                title = citation.get("title", "")
                url = citation.get("url", citation.get("link", ""))
                output_lines.append(f"{idx}. [{title}]({url})" if title else f"{idx}. {url}")
        output_lines.append("")

    return "\n".join(output_lines)


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "server": "Perplexity Search MCP Server",
        "version": "2.0.0",
        "api_key_configured": bool(PERPLEXITY_API_KEY),
        "available_models": [
            "llama-3.1-sonar-small-128k-online",
            "llama-3.1-sonar-large-128k-online",
            "llama-3.1-sonar-huge-128k-online"
        ]
    }


# ============================================================================
# OpenAI 호환 API 엔드포인트 (Open WebUI 모델 등록용)
# ============================================================================

@app.get("/v1/models")
async def list_models():
    """
    OpenAI 호환 API: 사용 가능한 Perplexity 모델 목록 반환
    """
    models = []

    if PERPLEXITY_API_KEY:
        models = [
            {
                "id": "perplexity-search",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "perplexity",
                "description": "Perplexity 웹 검색 (기본)"
            },
            {
                "id": "llama-3.1-sonar-small-128k-online",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "perplexity",
                "description": "Perplexity Sonar Small (빠름)"
            },
            {
                "id": "llama-3.1-sonar-large-128k-online",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "perplexity",
                "description": "Perplexity Sonar Large (균형)"
            },
            {
                "id": "llama-3.1-sonar-huge-128k-online",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "perplexity",
                "description": "Perplexity Sonar Huge (고품질)"
            }
        ]

    return {
        "object": "list",
        "data": models
    }


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False


def build_search_query_from_conversation(messages: List[ChatMessage]) -> str:
    """대화 기록에서 검색에 적합한 쿼리 생성"""
    # 최근 사용자 메시지 추출 (현재 질문)
    current_query = ""
    for msg in reversed(messages):
        if msg.role == "user":
            current_query = msg.content
            break

    if not current_query:
        return ""

    # 대화 기록에서 컨텍스트 추출 (이전 대화)
    user_messages = [m for m in messages if m.role == "user"]

    # 마지막 메시지 제외한 이전 사용자 메시지들 (최대 2개)
    prev_user_messages = user_messages[:-1][-2:] if len(user_messages) > 1 else []

    context_parts = []
    for msg in prev_user_messages:
        content = msg.content.strip()
        if len(content) > 80:
            content = content[:80]
        context_parts.append(content)

    # 컨텍스트가 있으면 포함
    if context_parts:
        context_text = " ".join(context_parts)
        search_query = f"{context_text} {current_query}"
        logger.info(f"멀티턴 검색 쿼리 생성: {search_query[:100]}...")
    else:
        search_query = current_query

    # 최대 길이 제한
    if len(search_query) > 400:
        search_query = search_query[:400]

    return search_query


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI 호환 API: 채팅 완료 요청 처리 (Perplexity Search 전용)
    """
    model = request.model
    temperature = request.temperature or 0.2
    max_tokens = request.max_tokens or 1024

    # 대화에서 검색 쿼리 생성
    query = build_search_query_from_conversation(request.messages)

    if not query:
        raise HTTPException(status_code=400, detail="검색 쿼리가 없습니다")

    logger.info(f"Chat Completion 요청: model={model}")
    logger.info(f"검색 쿼리: {query[:100]}...")

    # Perplexity 모델 매핑
    perplexity_model = model
    if model == "perplexity-search":
        perplexity_model = "llama-3.1-sonar-small-128k-online"
    elif not model.startswith("llama-3.1-sonar"):
        perplexity_model = "llama-3.1-sonar-small-128k-online"

    # Perplexity Search API 호출
    result = await call_perplexity_search_api(
        query=query,
        model=perplexity_model,
        temperature=temperature,
        max_tokens=max_tokens
    )

    # 오류 처리
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "API call failed"))

    # 결과 포맷팅
    formatted_content = format_search_results(result)

    # OpenAI 형식으로 응답 반환
    response = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": formatted_content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": result.get("usage", {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }),
        "search_results": {
            "query": result.get("query", ""),
            "citations": result.get("citations", []),
            "response_time": result.get("response_time", 0)
        }
    }

    return response


@app.post("/search")
async def direct_search(request: Request):
    """직접 Perplexity 검색 엔드포인트"""
    body = await request.json()
    query = body.get("query", "")
    model = body.get("model", "llama-3.1-sonar-small-128k-online")
    max_tokens = body.get("max_tokens", 1024)
    temperature = body.get("temperature", 0.2)

    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    result = await call_perplexity_search_api(
        query=query,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )

    return JSONResponse(content=result)


@app.post("/mcp")
@app.post("/")
async def mcp_endpoint(request: Request):
    """
    MCP 메인 엔드포인트
    """
    try:
        body = await request.json()
        logger.info(f"📨 MCP Request: {body.get('method')}")

        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "logging": {}
                },
                "serverInfo": {
                    "name": "perplexity-search-mcp-server",
                    "version": "2.0.0"
                }
            }
            return MCPResponse(id=request_id, result=result).model_dump()

        elif method == "tools/list":
            result = {"tools": TOOLS}
            return MCPResponse(id=request_id, result=result).model_dump()

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            logger.info(f"🔧 Tool Call: {tool_name}")
            logger.info(f"   Arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")

            if tool_name == "perplexity_search":
                result_data = await call_perplexity_search_api(
                    query=arguments.get("query", ""),
                    model=arguments.get("model", "llama-3.1-sonar-small-128k-online"),
                    max_tokens=arguments.get("max_tokens", 1024),
                    temperature=arguments.get("temperature", 0.2),
                    search_recency_filter=arguments.get("search_recency_filter", "month")
                )

                if result_data.get("success"):
                    formatted = format_search_results(result_data)
                    content = [{"type": "text", "text": formatted}]
                    result = {"content": content, "isError": False}
                else:
                    content = [{"type": "text", "text": f"❌ 오류: {result_data.get('error')}"}]
                    result = {"content": content, "isError": True}

            elif tool_name == "get_search_status":
                status_info = {
                    "perplexity_api_configured": bool(PERPLEXITY_API_KEY),
                    "server_status": "running",
                    "version": "2.0.0",
                    "available_models": [
                        "llama-3.1-sonar-small-128k-online",
                        "llama-3.1-sonar-large-128k-online",
                        "llama-3.1-sonar-huge-128k-online"
                    ]
                }
                content = [{"type": "text", "text": json.dumps(status_info, indent=2, ensure_ascii=False)}]
                result = {"content": content, "isError": False}

            else:
                error = {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
                return MCPResponse(id=request_id, error=error).model_dump()

            return MCPResponse(id=request_id, result=result).model_dump()

        elif method == "ping":
            result = {}
            return MCPResponse(id=request_id, result=result).model_dump()

        else:
            error = {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
            return MCPResponse(id=request_id, error=error).model_dump()

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# SSE 엔드포인트 (MCP SSE 지원)
@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE 엔드포인트 - MCP SSE 플러그인 지원"""
    async def event_generator():
        yield f"data: {json.dumps({'type': 'connected', 'server': 'perplexity-search-mcp'})}\n\n"
        while True:
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
            await asyncio.sleep(30)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/messages")
async def messages_endpoint(request: Request):
    """메시지 엔드포인트 - MCP SSE 플러그인 지원"""
    body = await request.json()
    logger.info(f"SSE 메시지 수신: {body}")
    return await mcp_endpoint(request)


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("🔍 Perplexity Search MCP Server Starting")
    logger.info("=" * 80)
    logger.info(f"   Port: {MCP_SERVER_PORT}")
    logger.info(f"   Endpoint: http://localhost:{MCP_SERVER_PORT}/mcp")
    logger.info(f"   Health: http://localhost:{MCP_SERVER_PORT}/health")
    logger.info(f"   Models: http://localhost:{MCP_SERVER_PORT}/v1/models")
    logger.info("")
    logger.info("📋 Available Tools:")
    logger.info("   - perplexity_search: Perplexity 웹 검색 API 호출")
    logger.info("   - get_search_status: API 연결 상태 확인")
    logger.info("")
    logger.info("🔑 API Key:")
    logger.info(f"   Perplexity: {'✅ Configured' if PERPLEXITY_API_KEY else '❌ Not configured'}")
    logger.info("")
    logger.info("📦 Available Models:")
    logger.info("   - llama-3.1-sonar-small-128k-online (빠름)")
    logger.info("   - llama-3.1-sonar-large-128k-online (균형)")
    logger.info("   - llama-3.1-sonar-huge-128k-online (고품질)")
    logger.info("=" * 80)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=MCP_SERVER_PORT,
        log_level="info"
    )
