import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, ConfigDict
import aiohttp

from typing import Optional

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.config import get_config, save_config
from open_webui.config import BannerModel

from open_webui.utils.tools import (
    get_tool_server_data,
    get_tool_server_url,
    set_tool_servers,
)
from open_webui.utils.mcp.client import MCPClient

from open_webui.env import SRC_LOG_LEVELS

from open_webui.utils.oauth import (
    get_discovery_urls,
    get_oauth_client_info_with_dynamic_client_registration,
    encrypt_data,
    decrypt_data,
    OAuthClientInformationFull,
)
from mcp.shared.auth import OAuthMetadata

router = APIRouter()

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


############################
# ImportConfig
############################


class ImportConfigForm(BaseModel):
    config: dict


@router.post("/import", response_model=dict)
async def import_config(form_data: ImportConfigForm, user=Depends(get_admin_user)):
    save_config(form_data.config)
    return get_config()


############################
# ExportConfig
############################


# ============================================================================================================
# ----- [2026-01-31] /configs/export 권한 변경 및 사용자용 모델 설정 API 추가 시작 -----
# 보안 이슈 대응: /configs/export를 관리자 전용으로 변경
# 일반 사용자는 /configs/default-models API를 통해 모델 정보 조회 (읽기 전용)
# ============================================================================================================

@router.get("/export", response_model=dict)
async def export_config(user=Depends(get_admin_user)):
    """
    [2026-01-31] 관리자 전용으로 변경 (기존: get_verified_user → 변경: get_admin_user)
    전체 설정을 내보내는 API - 보안상 관리자만 접근 가능
    """
    return get_config()


############################
# User Models Config (모든 인증된 사용자 접근 가능)
############################


class UserModelsConfigResponse(BaseModel):
    """일반 사용자에게 필요한 모델 관련 설정"""
    default_internal_model: Optional[str] = None
    default_external_model: Optional[str] = None
    MODEL_SESSION_LIMITS: Optional[dict] = None  # 모델별 세션 제한 설정
    DEFAULT_MODELS: Optional[str] = None         # 기본 모델 설정
    MODEL_ORDER_LIST: Optional[list[str]] = None # 모델 정렬 순서


@router.get("/default-models", response_model=UserModelsConfigResponse)
async def get_default_models_config(request: Request, user=Depends(get_verified_user)):
    """
    [2026-01-31] 사용자용 모델 설정 API (읽기 전용) - 신규 추가
    모든 인증된 사용자가 접근 가능

    반환 정보:
    - default_internal_model: 내부 기본 모델
    - default_external_model: 외부 기본 모델
    - MODEL_SESSION_LIMITS: 모델별 세션 제한 (턴/토큰 수)
    - DEFAULT_MODELS: 기본 모델 설정
    - MODEL_ORDER_LIST: 모델 표시 순서

    관리자 전용 /configs/export, /configs/models 대신 일반 사용자는
    이 API를 통해 모델 관련 설정을 조회할 수 있음 (변경 불가, 조회만 가능)
    """
    config_data = get_config()
    return {
        "default_internal_model": config_data.get("default_internal_model", ""),
        "default_external_model": config_data.get("default_external_model", ""),
        "MODEL_SESSION_LIMITS": config_data.get("MODEL_SESSION_LIMITS", None),
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
    }

# ----- [2026-01-31] /configs/export 권한 변경 및 사용자용 모델 설정 API 추가 종료 -----
# ============================================================================================================


############################
# Connections Config
############################


class ConnectionsConfigForm(BaseModel):
    ENABLE_DIRECT_CONNECTIONS: bool
    ENABLE_BASE_MODELS_CACHE: bool


@router.get("/connections", response_model=ConnectionsConfigForm)
async def get_connections_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_DIRECT_CONNECTIONS": request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
        "ENABLE_BASE_MODELS_CACHE": request.app.state.config.ENABLE_BASE_MODELS_CACHE,
    }


@router.post("/connections", response_model=ConnectionsConfigForm)
async def set_connections_config(
    request: Request,
    form_data: ConnectionsConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.ENABLE_DIRECT_CONNECTIONS = (
        form_data.ENABLE_DIRECT_CONNECTIONS
    )
    request.app.state.config.ENABLE_BASE_MODELS_CACHE = (
        form_data.ENABLE_BASE_MODELS_CACHE
    )

    return {
        "ENABLE_DIRECT_CONNECTIONS": request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
        "ENABLE_BASE_MODELS_CACHE": request.app.state.config.ENABLE_BASE_MODELS_CACHE,
    }


class OAuthClientRegistrationForm(BaseModel):
    url: str
    client_id: str
    client_name: Optional[str] = None


@router.post("/oauth/clients/register")
async def register_oauth_client(
    request: Request,
    form_data: OAuthClientRegistrationForm,
    type: Optional[str] = None,
    user=Depends(get_admin_user),
):
    try:
        oauth_client_id = form_data.client_id
        if type:
            oauth_client_id = f"{type}:{form_data.client_id}"

        oauth_client_info = (
            await get_oauth_client_info_with_dynamic_client_registration(
                request, oauth_client_id, form_data.url
            )
        )
        return {
            "status": True,
            "oauth_client_info": encrypt_data(
                oauth_client_info.model_dump(mode="json")
            ),
        }
    except Exception as e:
        # ========== [2026-01-27 오류 정보 노출 방지] 시작 ==========
        # 상세 오류는 내부 로그에만 기록, 사용자에게는 일반 메시지만 표시
        import hashlib
        from datetime import datetime
        error_id = hashlib.md5(f"{datetime.now().isoformat()}-{str(e)[:30]}".encode()).hexdigest()[:8]
        log.error(f"[ERROR-{error_id}] OAuth client registration failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"OAuth 클라이언트 등록에 실패했습니다. (오류 코드: {error_id})",
        )
        # ========== [2026-01-27 오류 정보 노출 방지] 종료 ==========


############################
# ToolServers Config
############################


class ToolServerConnection(BaseModel):
    url: str
    path: str
    type: Optional[str] = "openapi"  # openapi, mcp
    auth_type: Optional[str]
    key: Optional[str]
    config: Optional[dict]

    model_config = ConfigDict(extra="allow")


class ToolServersConfigForm(BaseModel):
    TOOL_SERVER_CONNECTIONS: list[ToolServerConnection]


@router.get("/tool_servers", response_model=ToolServersConfigForm)
async def get_tool_servers_config(request: Request, user=Depends(get_admin_user)):
    return {
        "TOOL_SERVER_CONNECTIONS": request.app.state.config.TOOL_SERVER_CONNECTIONS,
    }


@router.post("/tool_servers", response_model=ToolServersConfigForm)
async def set_tool_servers_config(
    request: Request,
    form_data: ToolServersConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.TOOL_SERVER_CONNECTIONS = [
        connection.model_dump() for connection in form_data.TOOL_SERVER_CONNECTIONS
    ]

    await set_tool_servers(request)

    for connection in request.app.state.config.TOOL_SERVER_CONNECTIONS:
        server_type = connection.get("type", "openapi")
        if server_type == "mcp":
            server_id = connection.get("info", {}).get("id")
            auth_type = connection.get("auth_type", "none")
            if auth_type == "oauth_2.1" and server_id:
                try:
                    oauth_client_info = connection.get("info", {}).get(
                        "oauth_client_info", ""
                    )
                    oauth_client_info = decrypt_data(oauth_client_info)

                    request.app.state.oauth_client_manager.add_client(
                        f"{server_type}:{server_id}",
                        OAuthClientInformationFull(**oauth_client_info),
                    )
                except Exception as e:
                    log.debug(f"Failed to add OAuth client for MCP tool server: {e}")
                    continue

    return {
        "TOOL_SERVER_CONNECTIONS": request.app.state.config.TOOL_SERVER_CONNECTIONS,
    }


@router.post("/tool_servers/verify")
async def verify_tool_servers_config(
    request: Request, form_data: ToolServerConnection, user=Depends(get_admin_user)
):
    """
    Verify the connection to the tool server.
    """
    try:
        if form_data.type == "mcp":
            if form_data.auth_type == "oauth_2.1":
                discovery_urls = get_discovery_urls(form_data.url)
                for discovery_url in discovery_urls:
                    log.debug(
                        f"Trying to fetch OAuth 2.1 discovery document from {discovery_url}"
                    )
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            discovery_url
                        ) as oauth_server_metadata_response:
                            if oauth_server_metadata_response.status == 200:
                                try:
                                    oauth_server_metadata = (
                                        OAuthMetadata.model_validate(
                                            await oauth_server_metadata_response.json()
                                        )
                                    )
                                    return {
                                        "status": True,
                                        "oauth_server_metadata": oauth_server_metadata.model_dump(
                                            mode="json"
                                        ),
                                    }
                                except Exception as e:
                                    # ========== [2026-01-27 오류 정보 노출 방지] 시작 ==========
                                    import hashlib
                                    from datetime import datetime
                                    error_id = hashlib.md5(f"{datetime.now().isoformat()}-{str(e)[:30]}".encode()).hexdigest()[:8]
                                    log.error(f"[ERROR-{error_id}] OAuth parse failed: {type(e).__name__}: {str(e)}")
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f"OAuth 문서 파싱에 실패했습니다. (오류 코드: {error_id})",
                                    )
                                    # ========== [2026-01-27 오류 정보 노출 방지] 종료 ==========

                # ========== [2026-01-27 오류 정보 노출 방지] 시작 ==========
                raise HTTPException(
                    status_code=400,
                    detail="OAuth 2.1 검색 문서를 가져올 수 없습니다. 서버 연결을 확인해주세요.",
                )
                # ========== [2026-01-27 오류 정보 노출 방지] 종료 ==========
            else:
                try:
                    client = MCPClient()
                    headers = None

                    token = None
                    if form_data.auth_type == "bearer":
                        token = form_data.key
                    elif form_data.auth_type == "session":
                        token = request.state.token.credentials
                    elif form_data.auth_type == "system_oauth":
                        try:
                            if request.cookies.get("oauth_session_id", None):
                                token = await request.app.state.oauth_manager.get_oauth_token(
                                    user.id,
                                    request.cookies.get("oauth_session_id", None),
                                )
                        except Exception as e:
                            pass

                    if token:
                        headers = {"Authorization": f"Bearer {token}"}

                    await client.connect(form_data.url, headers=headers)
                    specs = await client.list_tool_specs()
                    return {
                        "status": True,
                        "specs": specs,
                    }
                except Exception as e:
                    # ========== [2026-01-27 오류 정보 노출 방지] 시작 ==========
                    import hashlib
                    from datetime import datetime
                    error_id = hashlib.md5(f"{datetime.now().isoformat()}-{str(e)[:30]}".encode()).hexdigest()[:8]
                    log.error(f"[ERROR-{error_id}] MCP client failed: {type(e).__name__}: {str(e)}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"MCP 클라이언트 연결에 실패했습니다. (오류 코드: {error_id})",
                    )
                    # ========== [2026-01-27 오류 정보 노출 방지] 종료 ==========
                finally:
                    if client:
                        await client.disconnect()
        else:  # openapi
            token = None
            if form_data.auth_type == "bearer":
                token = form_data.key
            elif form_data.auth_type == "session":
                token = request.state.token.credentials
            elif form_data.auth_type == "system_oauth":
                try:
                    if request.cookies.get("oauth_session_id", None):
                        token = await request.app.state.oauth_manager.get_oauth_token(
                            user.id,
                            request.cookies.get("oauth_session_id", None),
                        )
                except Exception as e:
                    pass

            url = get_tool_server_url(form_data.url, form_data.path)
            return await get_tool_server_data(token, url)
    except HTTPException as e:
        raise e
    except Exception as e:
        # ========== [2026-01-27 오류 정보 노출 방지] 시작 ==========
        import hashlib
        from datetime import datetime
        error_id = hashlib.md5(f"{datetime.now().isoformat()}-{str(e)[:30]}".encode()).hexdigest()[:8]
        log.error(f"[ERROR-{error_id}] Tool server connection failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"도구 서버 연결에 실패했습니다. (오류 코드: {error_id})",
        )
        # ========== [2026-01-27 오류 정보 노출 방지] 종료 ==========


############################
# CodeInterpreterConfig
############################
class CodeInterpreterConfigForm(BaseModel):
    ENABLE_CODE_EXECUTION: bool
    CODE_EXECUTION_ENGINE: str
    CODE_EXECUTION_JUPYTER_URL: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_EXECUTION_JUPYTER_TIMEOUT: Optional[int]
    ENABLE_CODE_INTERPRETER: bool
    CODE_INTERPRETER_ENGINE: str
    CODE_INTERPRETER_PROMPT_TEMPLATE: Optional[str]
    CODE_INTERPRETER_JUPYTER_URL: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_INTERPRETER_JUPYTER_TIMEOUT: Optional[int]


@router.get("/code_execution", response_model=CodeInterpreterConfigForm)
async def get_code_execution_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_CODE_EXECUTION": request.app.state.config.ENABLE_CODE_EXECUTION,
        "CODE_EXECUTION_ENGINE": request.app.state.config.CODE_EXECUTION_ENGINE,
        "CODE_EXECUTION_JUPYTER_URL": request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
        "CODE_EXECUTION_JUPYTER_AUTH": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH,
        "CODE_EXECUTION_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
        "CODE_EXECUTION_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
        "CODE_EXECUTION_JUPYTER_TIMEOUT": request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        "ENABLE_CODE_INTERPRETER": request.app.state.config.ENABLE_CODE_INTERPRETER,
        "CODE_INTERPRETER_ENGINE": request.app.state.config.CODE_INTERPRETER_ENGINE,
        "CODE_INTERPRETER_PROMPT_TEMPLATE": request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE,
        "CODE_INTERPRETER_JUPYTER_URL": request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
        "CODE_INTERPRETER_JUPYTER_AUTH": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH,
        "CODE_INTERPRETER_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
        "CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
        "CODE_INTERPRETER_JUPYTER_TIMEOUT": request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
    }


@router.post("/code_execution", response_model=CodeInterpreterConfigForm)
async def set_code_execution_config(
    request: Request, form_data: CodeInterpreterConfigForm, user=Depends(get_admin_user)
):

    request.app.state.config.ENABLE_CODE_EXECUTION = form_data.ENABLE_CODE_EXECUTION

    request.app.state.config.CODE_EXECUTION_ENGINE = form_data.CODE_EXECUTION_ENGINE
    request.app.state.config.CODE_EXECUTION_JUPYTER_URL = (
        form_data.CODE_EXECUTION_JUPYTER_URL
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH = (
        form_data.CODE_EXECUTION_JUPYTER_AUTH
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN = (
        form_data.CODE_EXECUTION_JUPYTER_AUTH_TOKEN
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD = (
        form_data.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT = (
        form_data.CODE_EXECUTION_JUPYTER_TIMEOUT
    )

    request.app.state.config.ENABLE_CODE_INTERPRETER = form_data.ENABLE_CODE_INTERPRETER
    request.app.state.config.CODE_INTERPRETER_ENGINE = form_data.CODE_INTERPRETER_ENGINE
    request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE = (
        form_data.CODE_INTERPRETER_PROMPT_TEMPLATE
    )

    request.app.state.config.CODE_INTERPRETER_JUPYTER_URL = (
        form_data.CODE_INTERPRETER_JUPYTER_URL
    )

    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH = (
        form_data.CODE_INTERPRETER_JUPYTER_AUTH
    )

    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN = (
        form_data.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
    )
    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD = (
        form_data.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
    )
    request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT = (
        form_data.CODE_INTERPRETER_JUPYTER_TIMEOUT
    )

    return {
        "ENABLE_CODE_EXECUTION": request.app.state.config.ENABLE_CODE_EXECUTION,
        "CODE_EXECUTION_ENGINE": request.app.state.config.CODE_EXECUTION_ENGINE,
        "CODE_EXECUTION_JUPYTER_URL": request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
        "CODE_EXECUTION_JUPYTER_AUTH": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH,
        "CODE_EXECUTION_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
        "CODE_EXECUTION_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
        "CODE_EXECUTION_JUPYTER_TIMEOUT": request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        "ENABLE_CODE_INTERPRETER": request.app.state.config.ENABLE_CODE_INTERPRETER,
        "CODE_INTERPRETER_ENGINE": request.app.state.config.CODE_INTERPRETER_ENGINE,
        "CODE_INTERPRETER_PROMPT_TEMPLATE": request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE,
        "CODE_INTERPRETER_JUPYTER_URL": request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
        "CODE_INTERPRETER_JUPYTER_AUTH": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH,
        "CODE_INTERPRETER_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
        "CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
        "CODE_INTERPRETER_JUPYTER_TIMEOUT": request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
    }


############################
# SetDefaultModels
############################
# ============================================================================================================
# [2025.01.05] 세션 제한 설정 저장 API 엔드포인트 (백엔드)
# ============================================================================================================
#
# ■ 기능: 모델별 세션 제한 설정(MODEL_SESSION_LIMITS)을 config DB에 저장/조회
#
# ■ 데이터 구조:
#   MODEL_SESSION_LIMITS = {
#     "모델ID": {
#       "maxTurns": 10,        # 최대 대화 턴수 (0=무제한)
#       "maxTokens": 50000,    # 세션 전체 최대 토큰수 (0=무제한)
#       "maxInputTokens": 4000, # 1턴당 입력 가능 토큰수 (0=무제한)
#       "warningTurns": 2      # 경고 시작 턴수 (0=경고없음)
#     }
#   }
#
# ■ 저장 위치:
#   - 테이블: config
#   - 컬럼: data (JSONB 타입)
#   - JSON 키: MODEL_SESSION_LIMITS
#
# ■ 저장 흐름 (POST /api/v1/configs/models):
#   1. 프론트엔드 setModelsConfig() 호출
#   2. set_models_config() 함수 실행
#   3. get_config()로 기존 설정 전체 조회 (config.py)
#   4. config["MODEL_SESSION_LIMITS"] = 새 값 병합
#   5. save_config(config) 호출 (config.py)
#   6. save_to_db(data) 호출 - SQLAlchemy ORM
#   7. PostgreSQL config 테이블 UPDATE 실행
#   8. CONFIG_DATA 전역 변수 업데이트 (메모리 캐시)
#   9. PERSISTENT_CONFIG_REGISTRY 업데이트 트리거
#
# ■ 조회 흐름 (GET /api/v1/configs/models):
#   1. 프론트엔드 getModelsConfig() 호출
#   2. get_models_config() 함수 실행
#   3. get_config()로 config 테이블에서 data 컬럼 조회
#   4. config["MODEL_SESSION_LIMITS"] 추출하여 반환
#
# ■ 컨테이너 재시작: 불필요 (즉시 적용)
#   - DB에 직접 저장되고 메모리 캐시도 동기화됨
#
# ■ 관련 파일:
#   - 프론트엔드 UI: src/lib/components/admin/Settings/Models.svelte
#   - API 클라이언트: src/lib/apis/configs/index.ts
#   - 현재 파일 (백엔드 API): backend/open_webui/routers/configs.py
#   - DB 저장/조회: backend/open_webui/config.py (get_config, save_config, save_to_db)
#
# ============================================================================================================
# ----- [2025.01.05] 세션 제한 설정 API 시작 -----
class ModelsConfigForm(BaseModel):
    MODEL_SESSION_LIMITS: Optional[dict] = None  # 모델별 세션 제한 설정 (JSON 객체)
    DEFAULT_MODELS: Optional[str] = None         # 기본 모델 설정
    MODEL_ORDER_LIST: Optional[list[str]] = None # 모델 정렬 순서


@router.get("/models", response_model=ModelsConfigForm)
async def get_models_config(request: Request, user=Depends(get_admin_user)):
    """
    [2025.01.05] 세션 제한 설정 조회 API

    호출 흐름:
    1. 프론트엔드 getModelsConfig() → GET /api/v1/configs/models
    2. get_config()로 config 테이블에서 data 컬럼(JSONB) 조회
    3. MODEL_SESSION_LIMITS 키에서 모델별 설정 추출
    4. 프론트엔드로 응답 반환
    """
    # config.py의 get_config() 함수 호출 - config 테이블에서 data 컬럼 조회
    config_data = get_config()
    # MODEL_SESSION_LIMITS 키에서 모델별 세션 제한 설정 추출
    model_session_limits = config_data.get("MODEL_SESSION_LIMITS", None)

    return {
        "MODEL_SESSION_LIMITS": model_session_limits,  # 모델별 세션 제한 설정
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
    }


@router.post("/models", response_model=ModelsConfigForm)
async def set_models_config(
    request: Request, form_data: ModelsConfigForm, user=Depends(get_admin_user)
):
    """
    [2025.01.05] 세션 제한 설정 저장 API

    저장 흐름:
    1. 프론트엔드 setModelsConfig() → POST /api/v1/configs/models
    2. get_config()로 기존 설정 전체 조회
    3. MODEL_SESSION_LIMITS 키에 새 값 병합
    4. save_config() → save_to_db() → PostgreSQL UPDATE
    5. CONFIG_DATA 전역 변수 업데이트 (메모리 캐시)
    6. PERSISTENT_CONFIG_REGISTRY 업데이트 트리거
    7. 저장 완료 후 업데이트된 설정 반환

    컨테이너 재시작: 불필요 (즉시 적용)
    """
    # MODEL_SESSION_LIMITS가 요청에 포함된 경우 DB에 저장
    if form_data.MODEL_SESSION_LIMITS is not None:
        # Step 1: 기존 config 전체 조회 (다른 설정 유지를 위해)
        config_data = get_config()

        # Step 2: MODEL_SESSION_LIMITS 키에 새 값 병합
        config_data["MODEL_SESSION_LIMITS"] = form_data.MODEL_SESSION_LIMITS

        # Step 3: config.py의 save_config() 호출
        # save_config() → save_to_db() → SQLAlchemy ORM → PostgreSQL UPDATE
        # 동시에 CONFIG_DATA 전역 변수와 PERSISTENT_CONFIG_REGISTRY도 업데이트
        save_config(config_data)

        log.info(f"MODEL_SESSION_LIMITS saved to DB: {form_data.MODEL_SESSION_LIMITS}")

    # 기타 설정 저장 (메모리에만 저장)
    if form_data.DEFAULT_MODELS is not None:
        request.app.state.config.DEFAULT_MODELS = form_data.DEFAULT_MODELS
    if form_data.MODEL_ORDER_LIST is not None:
        request.app.state.config.MODEL_ORDER_LIST = form_data.MODEL_ORDER_LIST

    # 저장된 값 반환 (DB에서 다시 조회하여 최신 값 보장)
    config_data = get_config()
    return {
        "MODEL_SESSION_LIMITS": config_data.get("MODEL_SESSION_LIMITS", None),
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
    }
# ----- [2025.01.05] 세션 제한 설정 API 종료 -----


class PromptSuggestion(BaseModel):
    title: list[str]
    content: str


class SetDefaultSuggestionsForm(BaseModel):
    suggestions: list[PromptSuggestion]


@router.post("/suggestions", response_model=list[PromptSuggestion])
async def set_default_suggestions(
    request: Request,
    form_data: SetDefaultSuggestionsForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS = data["suggestions"]
    return request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS


############################
# SetBanners
############################


class SetBannersForm(BaseModel):
    banners: list[BannerModel]


@router.post("/banners", response_model=list[BannerModel])
async def set_banners(
    request: Request,
    form_data: SetBannersForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    request.app.state.config.BANNERS = data["banners"]
    return request.app.state.config.BANNERS


@router.get("/banners", response_model=list[BannerModel])
async def get_banners(
    request: Request,
    user=Depends(get_verified_user),
):
    return request.app.state.config.BANNERS


############################
# [2026.01.07] Help Images API
############################
# ============================================================================================================
# 도움말 이미지 목록 조회 API
# ============================================================================================================
# 목적: 관리자가 설정한 도움말 폴더의 이미지 목록을 조회
#
# 사용 위치:
# - src/lib/components/chat/HelpImageViewer.svelte: 도움말 이미지 뷰어
# - src/lib/components/chat/Navbar.svelte: ? 아이콘 클릭 시 모달 표시
#
# 이미지 정렬: 파일명 순 (001.png, 002.png 등으로 순서 지정 권장)
# ============================================================================================================
import os
import glob as glob_module

@router.get("/help/images")
async def get_help_images(
    request: Request,
    folder: str = "/static/help",
    user=Depends(get_verified_user),
):
    """
    [2026.01.07] 도움말 이미지 목록 조회 API

    Parameters:
    - folder: 도움말 이미지 폴더 경로 (기본값: /static/help)

    Returns:
    - images: 정렬된 이미지 URL 목록
    """
    try:
        # static 폴더 기준 경로 계산
        # 프로젝트 루트의 static 폴더 사용
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        # /static/help -> static/help 변환
        relative_folder = folder.lstrip('/')
        full_path = os.path.join(base_dir, relative_folder)

        log.info(f"[Help Images] Looking for images in: {full_path}")

        if not os.path.exists(full_path):
            log.warning(f"[Help Images] Folder not found: {full_path}")
            return {"images": [], "message": f"폴더를 찾을 수 없습니다: {folder}"}

        # 이미지 파일 확장자
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp', '*.svg']

        images = []
        for ext in image_extensions:
            pattern = os.path.join(full_path, ext)
            images.extend(glob_module.glob(pattern))
            # 대문자 확장자도 검색
            images.extend(glob_module.glob(pattern.upper()))

        # 파일명 기준으로 정렬 (001.png, 002.png 순서)
        images.sort(key=lambda x: os.path.basename(x).lower())

        # URL 경로로 변환 (API 엔드포인트 사용)
        from urllib.parse import quote
        image_urls = []
        for img_path in images:
            # 파일명만 추출
            filename = os.path.basename(img_path)
            # 파일명에 공백, 한글 등이 있을 수 있으므로 URL 인코딩
            encoded_filename = quote(filename, safe='')
            # API 엔드포인트를 통해 이미지 서빙 (/api/v1/configs/help/image/파일명)
            url = f'/api/v1/configs/help/image/{encoded_filename}'
            image_urls.append(url)

        log.info(f"[Help Images] Found {len(image_urls)} images")

        return {"images": image_urls}

    except Exception as e:
        log.error(f"[Help Images] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"도움말 이미지 조회 실패: {str(e)}"
        )
# ----- [2026.01.07] Help Images API 종료 -----

# ----- [2026.01.07] Help Image 파일 서빙 API 시작 -----
from fastapi.responses import FileResponse

@router.get("/help/image/{filename:path}")
async def get_help_image(
    request: Request,
    filename: str,
    folder: str = "/static/help",
):
    """
    [2026.01.07] 도움말 이미지 파일 서빙 API

    Parameters:
    - filename: 이미지 파일명
    - folder: 도움말 이미지 폴더 경로 (기본값: /static/help)

    Returns:
    - 이미지 파일 (FileResponse)
    """
    try:
        from urllib.parse import unquote

        # URL 디코딩
        decoded_filename = unquote(filename)

        # 프로젝트 루트 경로 계산
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        # /static/help -> static/help 변환
        relative_folder = folder.lstrip('/')
        full_path = os.path.join(base_dir, relative_folder, decoded_filename)

        log.info(f"[Help Image] Serving: {full_path}")

        if not os.path.exists(full_path):
            log.warning(f"[Help Image] File not found: {full_path}")
            raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다")

        # 파일 확장자에 따른 MIME 타입 설정
        ext = os.path.splitext(full_path)[1].lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml'
        }
        media_type = mime_types.get(ext, 'application/octet-stream')

        return FileResponse(full_path, media_type=media_type)

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"[Help Image] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"이미지 로드 실패: {str(e)}"
        )
# ----- [2026.01.07] Help Image 파일 서빙 API 종료 -----


# ----- [2026.01.19] Client IP 조회 API 시작 -----
# ----- [2026.01.30] X-Forwarded-For IP 변조 취약점 수정 시작 -----
import ipaddress
import re

# 신뢰할 수 있는 프록시 IP 목록 (내부 네트워크만)
TRUSTED_PROXY_IPS = [
    "127.0.0.1",
    "::1",
    # 내부 네트워크 대역
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    # Podman/Docker 네트워크
    "10.88.0.0/16",
    "10.89.0.0/16",
]

def is_trusted_proxy(ip: str) -> bool:
    """
    [2026.01.30] 신뢰할 수 있는 프록시 IP인지 확인
    """
    try:
        client_ip = ipaddress.ip_address(ip)
        for trusted in TRUSTED_PROXY_IPS:
            if "/" in trusted:
                # CIDR 표기법
                if client_ip in ipaddress.ip_network(trusted, strict=False):
                    return True
            else:
                if client_ip == ipaddress.ip_address(trusted):
                    return True
        return False
    except ValueError:
        return False

def is_valid_ip(ip: str) -> bool:
    """
    [2026.01.30] 유효한 IP 주소 형식인지 검증
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def sanitize_ip_header(header_value: str) -> str:
    """
    [2026.01.30] IP 헤더 값 검증 및 정화
    - SQL Injection, XSS 등 방지
    - 유효한 IP 형식만 허용
    """
    if not header_value:
        return None

    # 첫 번째 IP만 추출 (쉼표로 구분된 경우)
    first_ip = header_value.split(",")[0].strip()

    # IP 주소 형식 검증 (IPv4/IPv6만 허용)
    ip_pattern = r'^[\d\.:a-fA-F]+$'
    if not re.match(ip_pattern, first_ip):
        return None

    # 유효한 IP인지 최종 확인
    if is_valid_ip(first_ip):
        return first_ip

    return None
# ----- [2026.01.30] X-Forwarded-For IP 변조 취약점 수정 종료 -----

@router.get("/client-ip")
async def get_client_ip(
    request: Request,
    user=Depends(get_verified_user),
):
    """
    [2026.01.19] 클라이언트 IP 주소 조회 API
    [2026.01.30] 보안 강화: X-Forwarded-For 헤더 변조 방지

    현재 접속한 사용자의 IP 주소를 반환합니다.

    보안 정책:
    - X-Forwarded-For 헤더는 신뢰할 수 있는 프록시에서만 허용
    - 헤더 값의 IP 형식 검증
    - 직접 연결 IP를 기본으로 사용

    Returns:
    - ip: 클라이언트 IP 주소
    - forwarded_for: X-Forwarded-For 헤더 값 (있는 경우)
    - source: IP 출처 (direct/forwarded/real_ip)
    """
    try:
        # ----- [2026.01.30] 보안 강화된 IP 추출 로직 시작 -----
        # 직접 연결 IP 먼저 확인
        direct_ip = request.client.host if request.client else None

        # 프록시 헤더 값 추출 및 검증
        forwarded_for_raw = request.headers.get("X-Forwarded-For")
        real_ip_raw = request.headers.get("X-Real-IP")

        # 헤더 값 정화 (악의적인 값 필터링)
        forwarded_for = sanitize_ip_header(forwarded_for_raw)
        real_ip = sanitize_ip_header(real_ip_raw)

        # IP 결정 로직 (보안 우선)
        source = "direct"

        # 직접 연결이 신뢰할 수 있는 프록시인 경우에만 X-Forwarded-For 신뢰
        if direct_ip and is_trusted_proxy(direct_ip):
            if forwarded_for:
                client_ip = forwarded_for
                source = "forwarded"
            elif real_ip:
                client_ip = real_ip
                source = "real_ip"
            else:
                client_ip = direct_ip
        else:
            # 직접 연결이 외부 IP인 경우, 프록시 헤더 무시 (변조 방지)
            client_ip = direct_ip if direct_ip else "Unknown"
            if forwarded_for_raw or real_ip_raw:
                log.warning(
                    f"[Client IP] 보안 경고: 비신뢰 출처에서 프록시 헤더 감지 "
                    f"(direct_ip={direct_ip}, X-Forwarded-For={forwarded_for_raw})"
                )
        # ----- [2026.01.30] 보안 강화된 IP 추출 로직 종료 -----

        return {
            "ip": client_ip,
            "source": source,
            "forwarded_for": forwarded_for_raw,  # 원본 값 (디버깅용)
            "real_ip": real_ip_raw,
            "direct_ip": direct_ip,
            "trusted_proxy": is_trusted_proxy(direct_ip) if direct_ip else False
        }
    except Exception as e:
        log.error(f"[Client IP] Error: {e}")
        return {"ip": "Unknown", "error": str(e)}
# ----- [2026.01.19] Client IP 조회 API 종료 -----


# ----- [2026.01.19] 모델 색상 설정 API 시작 -----
# 기본 모델 색상 설정
DEFAULT_MODEL_COLORS = [
    {"keyword": "gpt", "color": "emerald", "label": "GPT (OpenAI)"},
    {"keyword": "openai", "color": "emerald", "label": "OpenAI"},
    {"keyword": "claude", "color": "orange", "label": "Claude (Anthropic)"},
    {"keyword": "anthropic", "color": "orange", "label": "Anthropic"},
    {"keyword": "gemini", "color": "blue", "label": "Gemini (Google)"},
    {"keyword": "google", "color": "blue", "label": "Google"},
    {"keyword": "llama", "color": "purple", "label": "Llama (Meta)"},
    {"keyword": "meta", "color": "purple", "label": "Meta"},
    {"keyword": "mistral", "color": "yellow", "label": "Mistral"},
    {"keyword": "mixtral", "color": "yellow", "label": "Mixtral"},
    {"keyword": "qwen", "color": "indigo", "label": "Qwen (Alibaba)"},
    {"keyword": "deepseek", "color": "pink", "label": "DeepSeek"},
    {"keyword": "phi", "color": "teal", "label": "Phi (Microsoft)"},
    {"keyword": "solar", "color": "red", "label": "Solar (Upstage)"},
    {"keyword": "ollama", "color": "cyan", "label": "Ollama"},
]

@router.get("/model-colors")
async def get_model_colors(
    request: Request,
    user=Depends(get_verified_user),
):
    """
    [2026.01.19] 모델 색상 설정 조회 API

    채팅 화면에서 모델명을 색상으로 구분하기 위한 설정을 반환합니다.

    Returns:
    - colors: 모델 색상 매핑 배열
    """
    try:
        # config에서 MODEL_COLORS 조회
        config_data = Configs.get_config()
        if config_data and "MODEL_COLORS" in config_data:
            return {"colors": config_data["MODEL_COLORS"]}
        else:
            # 기본값 반환
            return {"colors": DEFAULT_MODEL_COLORS}
    except Exception as e:
        log.error(f"[Model Colors] Get error: {e}")
        return {"colors": DEFAULT_MODEL_COLORS}


@router.post("/model-colors")
async def set_model_colors(
    request: Request,
    user=Depends(get_admin_user),
):
    """
    [2026.01.19] 모델 색상 설정 저장 API (관리자 전용)

    채팅 화면에서 모델명을 색상으로 구분하기 위한 설정을 저장합니다.

    Request Body:
    - colors: 모델 색상 매핑 배열
      - keyword: 모델명에 포함된 키워드
      - color: Tailwind 색상 이름 (예: emerald, orange, blue)
      - label: 표시 라벨

    Returns:
    - success: 성공 여부
    - colors: 저장된 설정
    """
    try:
        data = await request.json()
        colors = data.get("colors", DEFAULT_MODEL_COLORS)

        # config에서 기존 설정 조회
        config_data = Configs.get_config() or {}

        # MODEL_COLORS 업데이트
        config_data["MODEL_COLORS"] = colors

        # config 저장
        Configs.set_config(config_data)

        log.info(f"[Model Colors] Settings saved: {len(colors)} color mappings")
        return {"success": True, "colors": colors}
    except Exception as e:
        log.error(f"[Model Colors] Save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ----- [2026.01.19] 모델 색상 설정 API 종료 -----


# ============================================================================================================
# ----- [2026-01-31] Active-Active 캐시 동기화 API 시작 -----
# ============================================================================================================
#
# ■ 기능 개요:
#   Active-Active 환경에서 설정 변경 시 모든 서버의 메모리 캐시를 동기화
#
# ■ 문제 상황:
#   - App Server 1에서 설정 변경 → DB 저장 + Server 1 캐시 업데이트
#   - App Server 2의 캐시는 그대로 → 불일치 발생
#
# ■ 해결 방법:
#   1. /refresh-cache: 현재 서버의 캐시를 DB에서 다시 로드
#   2. /sync-servers: 설정된 모든 서버에 refresh-cache 호출
#
# ■ 환경변수 설정 (docker-compose.yml 또는 .env):
#   CLUSTER_SERVER_URLS=http://192.168.122.178:8080,http://192.168.122.177:8080
#
# ============================================================================================================

from open_webui.config import get_config as load_config_from_db

# 클러스터 서버 URL 목록 (환경변수에서 로드)
CLUSTER_SERVER_URLS = os.environ.get("CLUSTER_SERVER_URLS", "").split(",")
CLUSTER_SERVER_URLS = [url.strip() for url in CLUSTER_SERVER_URLS if url.strip()]


@router.post("/refresh-cache")
async def refresh_config_cache(
    request: Request,
    user=Depends(get_admin_user),
):
    """
    [2026-01-31] 현재 서버의 설정 캐시를 DB에서 다시 로드

    Active-Active 환경에서 다른 서버에서 설정이 변경되었을 때
    현재 서버의 메모리 캐시를 최신 상태로 갱신합니다.

    Returns:
    - success: 성공 여부
    - message: 결과 메시지
    - config_keys: 로드된 설정 키 목록
    """
    try:
        from open_webui import config as config_module

        # DB에서 최신 설정 로드
        fresh_config = load_config_from_db()

        # 글로벌 CONFIG_DATA 업데이트
        config_module.CONFIG_DATA = fresh_config

        # PERSISTENT_CONFIG_REGISTRY 업데이트 트리거
        for config_item in config_module.PERSISTENT_CONFIG_REGISTRY:
            try:
                config_item.update()
            except Exception as e:
                log.warning(f"[Refresh Cache] Failed to update config item: {e}")

        config_keys = list(fresh_config.keys()) if isinstance(fresh_config, dict) else []

        log.info(f"[Refresh Cache] Config cache refreshed successfully. Keys: {config_keys}")

        return {
            "success": True,
            "message": "설정 캐시가 성공적으로 갱신되었습니다.",
            "config_keys": config_keys,
            "server": request.base_url.hostname
        }
    except Exception as e:
        log.error(f"[Refresh Cache] Error: {e}")
        raise HTTPException(status_code=500, detail=f"캐시 갱신 실패: {str(e)}")


@router.post("/sync-servers")
async def sync_config_to_all_servers(
    request: Request,
    user=Depends(get_admin_user),
):
    """
    [2026-01-31] 모든 클러스터 서버의 설정 캐시를 동기화

    환경변수 CLUSTER_SERVER_URLS에 설정된 모든 서버에
    /refresh-cache API를 호출하여 캐시를 동기화합니다.

    환경변수 설정 예시:
    CLUSTER_SERVER_URLS=http://192.168.122.178:8080,http://192.168.122.177:8080

    Returns:
    - success: 전체 성공 여부
    - results: 각 서버별 동기화 결과
    - total_servers: 전체 서버 수
    - successful_servers: 성공한 서버 수
    """
    results = []

    # 현재 서버는 자동으로 갱신됨 (저장 시 이미 갱신)
    current_host = f"{request.base_url.scheme}://{request.base_url.netloc}"

    # 인증 토큰 추출
    auth_header = request.headers.get("Authorization", "")

    if not CLUSTER_SERVER_URLS:
        # 클러스터 설정이 없으면 현재 서버만 갱신
        log.warning("[Sync Servers] CLUSTER_SERVER_URLS not configured. Only refreshing current server.")
        return {
            "success": True,
            "message": "클러스터 설정이 없습니다. 현재 서버만 갱신되었습니다.",
            "results": [{"server": current_host, "success": True, "message": "현재 서버"}],
            "total_servers": 1,
            "successful_servers": 1
        }

    for server_url in CLUSTER_SERVER_URLS:
        server_url = server_url.rstrip("/")

        # 현재 서버는 건너뛰기 (이미 갱신됨)
        if server_url in current_host or current_host in server_url:
            results.append({
                "server": server_url,
                "success": True,
                "message": "현재 서버 (이미 갱신됨)"
            })
            continue

        try:
            # 다른 서버에 refresh-cache 호출
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{server_url}/api/v1/configs/refresh-cache",
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        results.append({
                            "server": server_url,
                            "success": True,
                            "message": result_data.get("message", "성공")
                        })
                        log.info(f"[Sync Servers] Successfully synced: {server_url}")
                    else:
                        error_text = await response.text()
                        results.append({
                            "server": server_url,
                            "success": False,
                            "message": f"HTTP {response.status}: {error_text[:100]}"
                        })
                        log.warning(f"[Sync Servers] Failed to sync {server_url}: {response.status}")
        except aiohttp.ClientError as e:
            results.append({
                "server": server_url,
                "success": False,
                "message": f"연결 실패: {str(e)}"
            })
            log.error(f"[Sync Servers] Connection error for {server_url}: {e}")
        except Exception as e:
            results.append({
                "server": server_url,
                "success": False,
                "message": f"오류: {str(e)}"
            })
            log.error(f"[Sync Servers] Error for {server_url}: {e}")

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    return {
        "success": successful == total,
        "message": f"{successful}/{total} 서버 동기화 완료",
        "results": results,
        "total_servers": total,
        "successful_servers": successful
    }


@router.get("/cluster-servers")
async def get_cluster_servers(
    request: Request,
    user=Depends(get_admin_user),
):
    """
    [2026-01-31] 설정된 클러스터 서버 목록 조회

    Returns:
    - servers: 클러스터 서버 URL 목록
    - current_server: 현재 서버 URL
    """
    current_host = f"{request.base_url.scheme}://{request.base_url.netloc}"

    return {
        "servers": CLUSTER_SERVER_URLS,
        "current_server": current_host,
        "configured": len(CLUSTER_SERVER_URLS) > 0
    }

# ----- [2026-01-31] Active-Active 캐시 동기화 API 종료 -----
# ============================================================================================================
