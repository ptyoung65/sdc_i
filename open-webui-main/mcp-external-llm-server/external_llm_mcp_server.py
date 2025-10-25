#!/usr/bin/env python3
"""
External LLM MCP Server
Open WebUI에서 외부 LLM (ChatGPT, Perplexity)을 호출하기 위한 MCP 서버

플로우:
Open WebUI → MCP Server → External LLM API → MCP Server → Open WebUI
"""

import asyncio
import logging
import os
import json
from typing import Any, Optional, Dict
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
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

app = FastAPI(title="External LLM MCP Server", version="1.0.0")

# 환경 변수에서 API 키 로드 (선택적)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

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

# 사용 가능한 도구 목록
TOOLS = [
    {
        "name": "query_chatgpt",
        "description": "ChatGPT API를 호출하여 질문에 대한 답변을 받습니다",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "사용할 ChatGPT 모델 (예: gpt-4, gpt-3.5-turbo)",
                    "default": "gpt-3.5-turbo"
                },
                "api_key": {
                    "type": "string",
                    "description": "OpenAI API 키 (선택적, 환경변수 우선)"
                },
                "user_info": {
                    "type": "string",
                    "description": "사용자 정보 (선택적)"
                },
                "question": {
                    "type": "string",
                    "description": "ChatGPT에게 물어볼 질문"
                },
                "temperature": {
                    "type": "number",
                    "description": "응답의 창의성 (0.0~2.0)",
                    "default": 0.7
                },
                "max_tokens": {
                    "type": "number",
                    "description": "최대 토큰 수",
                    "default": 1000
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "query_perplexity",
        "description": "Perplexity API를 호출하여 웹 검색 기반 답변을 받습니다",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "사용할 Perplexity 모델 (예: pplx-7b-online, pplx-70b-online)",
                    "default": "pplx-7b-online"
                },
                "api_key": {
                    "type": "string",
                    "description": "Perplexity API 키 (선택적, 환경변수 우선)"
                },
                "user_info": {
                    "type": "string",
                    "description": "사용자 정보 (선택적)"
                },
                "question": {
                    "type": "string",
                    "description": "Perplexity에게 물어볼 질문"
                },
                "search_domain_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "검색할 도메인 필터 (선택적)"
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "get_llm_status",
        "description": "외부 LLM API 연결 상태를 확인합니다",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


async def call_chatgpt_api(
    question: str,
    model: str = "gpt-3.5-turbo",
    api_key: Optional[str] = None,
    user_info: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> Dict:
    """
    ChatGPT API 호출
    """
    # API 키 결정 (파라미터 우선, 환경변수 fallback)
    key = api_key or OPENAI_API_KEY

    if not key:
        return {
            "success": False,
            "error": "OpenAI API 키가 설정되지 않았습니다. api_key 파라미터를 제공하거나 OPENAI_API_KEY 환경변수를 설정하세요."
        }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": question}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    # 사용자 정보가 있으면 시스템 메시지로 추가
    if user_info:
        payload["messages"].insert(0, {
            "role": "system",
            "content": f"사용자 정보: {user_info}"
        })

    logger.info(f"🤖 ChatGPT API 호출 시작")
    logger.info(f"   모델: {model}")
    logger.info(f"   질문: {question[:100]}...")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']

                logger.info(f"✅ ChatGPT 응답 성공")
                logger.info(f"   토큰 사용: {result.get('usage', {})}")

                return {
                    "success": True,
                    "model": model,
                    "answer": answer,
                    "usage": result.get('usage', {}),
                    "finish_reason": result['choices'][0].get('finish_reason')
                }
            else:
                error_msg = f"API 오류: {response.status_code} - {response.text}"
                logger.error(f"❌ ChatGPT API 실패: {error_msg}")
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


async def call_perplexity_api(
    question: str,
    model: str = "pplx-7b-online",
    api_key: Optional[str] = None,
    user_info: Optional[str] = None,
    search_domain_filter: Optional[list] = None
) -> Dict:
    """
    Perplexity API 호출
    """
    # API 키 결정
    key = api_key or PERPLEXITY_API_KEY

    if not key:
        return {
            "success": False,
            "error": "Perplexity API 키가 설정되지 않았습니다. api_key 파라미터를 제공하거나 PERPLEXITY_API_KEY 환경변수를 설정하세요."
        }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": question}
        ]
    }

    if user_info:
        payload["messages"].insert(0, {
            "role": "system",
            "content": f"사용자 정보: {user_info}"
        })

    if search_domain_filter:
        payload["search_domain_filter"] = search_domain_filter

    logger.info(f"🔍 Perplexity API 호출 시작")
    logger.info(f"   모델: {model}")
    logger.info(f"   질문: {question[:100]}...")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']

                logger.info(f"✅ Perplexity 응답 성공")

                return {
                    "success": True,
                    "model": model,
                    "answer": answer,
                    "citations": result.get('citations', []),
                    "usage": result.get('usage', {})
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


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "server": "External LLM MCP Server",
        "version": "1.0.0",
        "supported_llms": ["ChatGPT", "Perplexity"],
        "api_keys_configured": {
            "openai": bool(OPENAI_API_KEY),
            "perplexity": bool(PERPLEXITY_API_KEY)
        }
    }


# ============================================================================
# OpenAI 호환 API 엔드포인트 (Open WebUI 모델 등록용)
# ============================================================================

@app.get("/v1/models")
async def list_models():
    """
    OpenAI 호환 API: 사용 가능한 모델 목록 반환
    Open WebUI의 모델 선택 드롭다운에 표시됩니다
    """
    models = []

    # ChatGPT 모델들
    if OPENAI_API_KEY:
        models.extend([
            {
                "id": "gpt-4-turbo",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "openai-via-mcp",
                "permission": [],
                "root": "gpt-4-turbo",
                "parent": None
            },
            {
                "id": "gpt-4",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "openai-via-mcp",
                "permission": [],
                "root": "gpt-4",
                "parent": None
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "openai-via-mcp",
                "permission": [],
                "root": "gpt-3.5-turbo",
                "parent": None
            }
        ])

    # Perplexity 모델들
    if PERPLEXITY_API_KEY:
        models.extend([
            {
                "id": "pplx-70b-online",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "perplexity-via-mcp",
                "permission": [],
                "root": "pplx-70b-online",
                "parent": None
            },
            {
                "id": "pplx-7b-online",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "perplexity-via-mcp",
                "permission": [],
                "root": "pplx-7b-online",
                "parent": None
            }
        ])

    return {
        "object": "list",
        "data": models
    }


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    stream: Optional[bool] = False


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI 호환 API: 채팅 완료 요청 처리
    """
    model = request.model
    messages = request.messages
    temperature = request.temperature
    max_tokens = request.max_tokens

    # 마지막 사용자 메시지 추출
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # 모델에 따라 적절한 API 호출
    if model.startswith("gpt-"):
        # ChatGPT API 호출
        result = await call_chatgpt_api(
            question=user_message,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    elif model.startswith("pplx-"):
        # Perplexity API 호출
        result = await call_perplexity_api(
            question=user_message,
            model=model
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")

    # 오류 처리
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "API call failed"))

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
                    "content": result.get("answer", "")
                },
                "finish_reason": "stop"
            }
        ],
        "usage": result.get("usage", {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        })
    }

    return response


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
                    "name": "external-llm-mcp-server",
                    "version": "1.0.0"
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

            if tool_name == "query_chatgpt":
                result_data = await call_chatgpt_api(
                    question=arguments.get("question", ""),
                    model=arguments.get("model", "gpt-3.5-turbo"),
                    api_key=arguments.get("api_key"),
                    user_info=arguments.get("user_info"),
                    temperature=arguments.get("temperature", 0.7),
                    max_tokens=arguments.get("max_tokens", 1000)
                )

                if result_data.get("success"):
                    content_text = f"**ChatGPT 응답 ({result_data['model']})**\n\n{result_data['answer']}\n\n---\n토큰 사용: {result_data.get('usage', {})}"
                    content = [{"type": "text", "text": content_text}]
                    result = {"content": content, "isError": False}
                else:
                    content = [{"type": "text", "text": f"❌ 오류: {result_data.get('error')}"}]
                    result = {"content": content, "isError": True}

            elif tool_name == "query_perplexity":
                result_data = await call_perplexity_api(
                    question=arguments.get("question", ""),
                    model=arguments.get("model", "pplx-7b-online"),
                    api_key=arguments.get("api_key"),
                    user_info=arguments.get("user_info"),
                    search_domain_filter=arguments.get("search_domain_filter")
                )

                if result_data.get("success"):
                    citations_text = ""
                    if result_data.get("citations"):
                        citations_text = "\n\n**출처:**\n" + "\n".join(
                            f"- {cite}" for cite in result_data['citations']
                        )

                    content_text = f"**Perplexity 응답 ({result_data['model']})**\n\n{result_data['answer']}{citations_text}"
                    content = [{"type": "text", "text": content_text}]
                    result = {"content": content, "isError": False}
                else:
                    content = [{"type": "text", "text": f"❌ 오류: {result_data.get('error')}"}]
                    result = {"content": content, "isError": True}

            elif tool_name == "get_llm_status":
                status_info = {
                    "openai_api_configured": bool(OPENAI_API_KEY),
                    "perplexity_api_configured": bool(PERPLEXITY_API_KEY),
                    "server_status": "running",
                    "supported_models": {
                        "chatgpt": ["gpt-4", "gpt-3.5-turbo"],
                        "perplexity": ["pplx-7b-online", "pplx-70b-online"]
                    }
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


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("🚀 External LLM MCP Server Starting")
    logger.info("=" * 80)
    logger.info(f"   Port: 8100")
    logger.info(f"   Endpoint: http://localhost:8100/mcp")
    logger.info(f"   Health: http://localhost:8100/health")
    logger.info("")
    logger.info("📋 Available Tools:")
    logger.info("   - query_chatgpt: ChatGPT API 호출")
    logger.info("   - query_perplexity: Perplexity API 호출 (웹 검색)")
    logger.info("   - get_llm_status: API 연결 상태 확인")
    logger.info("")
    logger.info("🔑 API Keys:")
    logger.info(f"   OpenAI: {'✅ Configured' if OPENAI_API_KEY else '❌ Not configured'}")
    logger.info(f"   Perplexity: {'✅ Configured' if PERPLEXITY_API_KEY else '❌ Not configured'}")
    logger.info("")
    logger.info("💡 Tip: API 키는 환경변수나 도구 호출 시 파라미터로 전달하세요")
    logger.info("=" * 80)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8100,
        log_level="info"
    )
