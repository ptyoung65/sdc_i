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


@router.get("/export", response_model=dict)
# ----- [2026-03-02] exportConfig 권한 확인 시작 -----
# ■ 확인: get_verified_user → 관리자/일반사용자 모두 config 조회 가능 (정상)
# ■ MAX_POPUP_COUNT 포함한 전체 config 반환
# ■ 프론트엔드 호출: +layout.svelte loadPopupAnnouncements() → exportConfig(token)
# ----- [2026-03-02] exportConfig 권한 확인 종료 -----
async def export_config(user=Depends(get_verified_user)):
    return get_config()


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
        log.debug(f"Failed to register OAuth client: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to register OAuth client",
        )


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
                                    log.info(
                                        f"Failed to parse OAuth 2.1 discovery document: {e}"
                                    )
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f"Failed to parse OAuth 2.1 discovery document from {discovery_url}",
                                    )

                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch OAuth 2.1 discovery document from {discovery_urls}",
                )
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
                    log.debug(f"Failed to create MCP client: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to create MCP client",
                    )
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
        log.debug(f"Failed to connect to the tool server: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to the tool server",
        )


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
class ModelsConfigForm(BaseModel):
    DEFAULT_MODELS: Optional[str] = None
    MODEL_ORDER_LIST: Optional[list[str]] = None
    # ----- [2026-03-05] MODEL_SESSION_LIMITS 필드 누락 수정 시작 -----
    MODEL_SESSION_LIMITS: Optional[dict] = None
    # ----- [2026-03-05] MODEL_SESSION_LIMITS 필드 누락 수정 종료 -----

    model_config = ConfigDict(extra="allow")


@router.get("/models", response_model=ModelsConfigForm)
async def get_models_config(request: Request, user=Depends(get_admin_user)):
    # ----- [2026-03-05] MODEL_SESSION_LIMITS: config JSON에서 직접 조회 시작 -----
    config_data = get_config()
    # ----- [2026-03-05] MODEL_SESSION_LIMITS: config JSON에서 직접 조회 종료 -----
    return {
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
        "MODEL_SESSION_LIMITS": config_data.get('MODEL_SESSION_LIMITS', {}),
    }


@router.post("/models", response_model=ModelsConfigForm)
async def set_models_config(
    request: Request, form_data: ModelsConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.DEFAULT_MODELS = form_data.DEFAULT_MODELS
    request.app.state.config.MODEL_ORDER_LIST = form_data.MODEL_ORDER_LIST
    # ----- [2026-03-05] MODEL_SESSION_LIMITS: config JSON에 직접 저장 시작 -----
    # AppConfig(PersistentConfig)에 등록되지 않은 키이므로 get_config/save_config 사용
    if form_data.MODEL_SESSION_LIMITS is not None:
        config_data = get_config()
        config_data['MODEL_SESSION_LIMITS'] = form_data.MODEL_SESSION_LIMITS
        save_config(config_data)
    # ----- [2026-03-05] MODEL_SESSION_LIMITS: config JSON에 직접 저장 종료 -----
    config_data = get_config()
    return {
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
        "MODEL_SESSION_LIMITS": config_data.get('MODEL_SESSION_LIMITS', {}),
    }


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


# ----- [2026-02-04] 팝업 공지사항 관리 API 시작 -----
"""
팝업 공지사항 관리 API 엔드포인트

엔드포인트:
- GET /api/v1/configs/announcements - 모든 공지사항 조회 (관리자)
- GET /api/v1/configs/announcements/active - 활성 공지사항 조회 (일반 사용자)
- GET /api/v1/configs/announcements/{id} - 특정 공지사항 조회
- POST /api/v1/configs/announcements - 공지사항 생성 (관리자)
- PUT /api/v1/configs/announcements/{id} - 공지사항 수정 (관리자)
- DELETE /api/v1/configs/announcements/{id} - 공지사항 삭제 (관리자)
- POST /api/v1/configs/announcements/bulk-delete - 여러 공지사항 삭제 (관리자)
"""

from open_webui.models.announcements import (
    PopupAnnouncements,
    PopupAnnouncementModel,
    PopupAnnouncementForm,
    PopupAnnouncementUpdateForm,
)

# 공지사항 테이블 초기화
try:
    PopupAnnouncements.create_table()
    log.info("[ANNOUNCEMENTS] Table initialized successfully")
except Exception as e:
    log.warning(f"[ANNOUNCEMENTS] Failed to initialize table: {e}")


class BulkDeleteAnnouncementsForm(BaseModel):
    ids: list[str]


@router.get("/announcements", response_model=list[PopupAnnouncementModel])
async def get_announcements(user=Depends(get_admin_user)):
    """모든 공지사항 조회 (관리자 전용)"""
    announcements = PopupAnnouncements.get_all_announcements()
    return announcements


@router.get("/announcements/active", response_model=list[PopupAnnouncementModel])
async def get_active_announcements(user=Depends(get_verified_user)):
    """활성화된 공지사항 조회 (일반 사용자용, 설정된 개수만큼)"""
    # ----- [2026-03-02] MAX_POPUP_COUNT 팝업 표시 개수 확인 시작 -----
    # ■ 확인 결과: get_verified_user 사용으로 관리자/일반사용자 모두 접근 가능 (정상)
    # ■ API 테스트: 관리자(200 OK), 일반사용자(200 OK) 동일한 MAX_POPUP_COUNT 값 반환
    # ----- [2026-03-02] MAX_POPUP_COUNT 팝업 표시 개수 확인 종료 -----
    # ----- [2026-02-05] MAX_POPUP_COUNT 설정 적용 시작 -----
    # ----- [2026-02-26] MAX_POPUP_COUNT 적용 상세 설명 시작 -----
    # ■ 기능: 관리자가 /admin/settings/notification에서 설정한 팝업 표시 개수를 적용
    #
    # ■ 설정값 조회 과정:
    #   1. get_config() → config 테이블의 data(JSONB) 컬럼 전체 조회
    #   2. config.get('MAX_POPUP_COUNT', 3) → MAX_POPUP_COUNT 키 값 읽기 (없으면 기본값 3)
    #
    # ■ 설정값 저장 경로 (관리자 설정 화면에서):
    #   Notification.svelte savePopupCount()
    #   → updateConfigPartial(token, { MAX_POPUP_COUNT: N })
    #   → POST /api/v1/configs/import
    #   → config 테이블 data(JSONB) 컬럼에 MAX_POPUP_COUNT 키로 저장
    #
    # ■ 이 엔드포인트를 호출하는 곳:
    #   1. +layout.svelte loadPopupAnnouncements() → 로그인 시 팝업 표시
    #   2. Navbar.svelte loadAndShowAnnouncements() → 공지 다시보기 버튼 클릭 시
    #   두 곳 모두 getActiveAnnouncements(token) → GET /api/v1/configs/announcements/active 호출
    #
    # ■ limit 적용: get_active_announcements(limit=N)에서 활성 공지를 최근순 N개만 반환
    # ----- [2026-02-26] MAX_POPUP_COUNT 적용 상세 설명 종료 -----
    # ----- [2026-03-02] MAX_POPUP_COUNT 설정값 조회 확인 시작 -----
    # config 테이블 data(JSONB)에서 MAX_POPUP_COUNT 읽기 → 관리자/사용자 동일 적용
    config = get_config()
    max_popup_count = config.get('MAX_POPUP_COUNT', 3)  # 기본값 3
    # ----- [2026-03-02] MAX_POPUP_COUNT 설정값 조회 확인 종료 -----
    # ----- [2026-02-05] MAX_POPUP_COUNT 설정 적용 종료 -----
    announcements = PopupAnnouncements.get_active_announcements(limit=max_popup_count)
    return announcements


@router.get("/announcements/{id}", response_model=PopupAnnouncementModel)
async def get_announcement(id: str, user=Depends(get_verified_user)):
    """특정 공지사항 조회"""
    announcement = PopupAnnouncements.get_announcement_by_id(id)
    if not announcement:
        raise HTTPException(
            status_code=404,
            detail="공지사항을 찾을 수 없습니다."
        )
    return announcement


@router.post("/announcements", response_model=PopupAnnouncementModel)
async def create_announcement(
    form_data: PopupAnnouncementForm,
    user=Depends(get_admin_user)
):
    """새 공지사항 등록 (관리자 전용)"""
    # 날짜 유효성 검사
    if form_data.start_date >= form_data.end_date:
        raise HTTPException(
            status_code=400,
            detail="종료일시는 시작일시보다 이후여야 합니다."
        )

    announcement = PopupAnnouncements.insert_announcement(
        title=form_data.title,
        content=form_data.content,
        author=user.name,
        author_id=user.id,
        start_date=form_data.start_date,
        end_date=form_data.end_date
    )

    if not announcement:
        raise HTTPException(
            status_code=500,
            detail="공지사항 등록에 실패했습니다."
        )

    log.info(f"[ANNOUNCEMENTS] User {user.id} created announcement: {announcement.id}")
    return announcement


@router.put("/announcements/{id}", response_model=PopupAnnouncementModel)
async def update_announcement(
    id: str,
    form_data: PopupAnnouncementUpdateForm,
    user=Depends(get_admin_user)
):
    """공지사항 수정 (관리자 전용)"""
    # 날짜 유효성 검사 (둘 다 있을 때만)
    if form_data.start_date is not None and form_data.end_date is not None:
        if form_data.start_date >= form_data.end_date:
            raise HTTPException(
                status_code=400,
                detail="종료일시는 시작일시보다 이후여야 합니다."
            )

    announcement = PopupAnnouncements.update_announcement(id, form_data)

    if not announcement:
        raise HTTPException(
            status_code=404,
            detail="공지사항을 찾을 수 없습니다."
        )

    log.info(f"[ANNOUNCEMENTS] User {user.id} updated announcement: {id}")
    return announcement


@router.delete("/announcements/{id}")
async def delete_announcement(id: str, user=Depends(get_admin_user)):
    """공지사항 삭제 (관리자 전용)"""
    success = PopupAnnouncements.delete_announcement(id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="공지사항을 찾을 수 없습니다."
        )

    log.info(f"[ANNOUNCEMENTS] User {user.id} deleted announcement: {id}")
    return {"status": True, "message": "공지사항이 삭제되었습니다."}


@router.post("/announcements/bulk-delete")
async def bulk_delete_announcements(
    form_data: BulkDeleteAnnouncementsForm,
    user=Depends(get_admin_user)
):
    """여러 공지사항 삭제 (관리자 전용)"""
    if not form_data.ids:
        raise HTTPException(
            status_code=400,
            detail="삭제할 공지사항 ID를 선택해주세요."
        )

    deleted_count = PopupAnnouncements.delete_announcements(form_data.ids)

    log.info(f"[ANNOUNCEMENTS] User {user.id} bulk deleted {deleted_count} announcements")
    return {
        "status": True,
        "message": f"{deleted_count}개의 공지사항이 삭제되었습니다.",
        "deleted_count": deleted_count
    }

# ----- [2026-02-04] 팝업 공지사항 관리 API 종료 -----
