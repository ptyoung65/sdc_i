"""
내부 서버 통신 클라이언트 모듈
- 임베딩 서버 (BGE-M3) 통신
- LLM 서버 (Qwen3-235B) 통신
- 서버 설정 기반 동적 요청 처리
- 로드 밸런싱 및 장애 복구
"""

import asyncio
import httpx
import json
import random
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ServerInfo:
    """서버 정보 클래스"""
    url: str
    name: str
    api_key: str
    status: str = "unknown"


@dataclass
class EmbeddingServer(ServerInfo):
    """임베딩 서버 정보"""
    model: str = "BAAI/bge-m3"


@dataclass
class LLMServer(ServerInfo):
    """LLM 서버 정보"""
    model: str = "Qwen3-235B-A228-instruct-2507"


class InternalServerClient:
    """내부 서버 통신 클라이언트"""

    def __init__(self):
        self.embedding_servers: List[EmbeddingServer] = []
        self.llm_servers: List[LLMServer] = []
        self.timeout = 30.0
        self.max_retries = 3

    def load_servers_from_config(self, config: Dict[str, Any]):
        """서버 설정에서 서버 정보 로드"""
        try:
            # 임베딩 서버 로드
            self.embedding_servers = []
            for server_config in config.get('embedding_servers', []):
                server = EmbeddingServer(
                    url=server_config['url'],
                    name=server_config['name'],
                    api_key=server_config['api_key'],
                    status=server_config.get('status', 'unknown')
                )
                self.embedding_servers.append(server)

            # LLM 서버 로드
            self.llm_servers = []
            for server_config in config.get('llm_servers', []):
                server = LLMServer(
                    url=server_config['url'],
                    name=server_config['name'],
                    api_key=server_config['api_key'],
                    model=server_config.get('model', 'Qwen3-235B-A228-instruct-2507'),
                    status=server_config.get('status', 'unknown')
                )
                self.llm_servers.append(server)

            print(f"📋 [CONFIG] 서버 설정 로드 완료: 임베딩 {len(self.embedding_servers)}대, LLM {len(self.llm_servers)}대")

        except Exception as e:
            print(f"❌ [CONFIG] 서버 설정 로드 실패: {str(e)}")

    def load_servers_from_env(self, env_config: Dict[str, str]):
        """환경변수에서 서버 정보 로드 (기본값)"""
        try:
            # 임베딩 서버 (기본 3대)
            self.embedding_servers = [
                EmbeddingServer(
                    url=env_config.get("INTERNAL_EMBED_SERVER_1", "http://11.93.26.130:8080"),
                    name="sdcrpapoc1v",
                    api_key=env_config.get("INTERNAL_EMBED_API_KEY_1", "")
                ),
                EmbeddingServer(
                    url=env_config.get("INTERNAL_EMBED_SERVER_2", "http://11.93.26.43:8080"),
                    name="sdcaipocv2",
                    api_key=env_config.get("INTERNAL_EMBED_API_KEY_2", "")
                ),
                EmbeddingServer(
                    url=env_config.get("INTERNAL_EMBED_SERVER_3", "http://11.93.33.10:8080"),
                    name="mischataiapddvv",
                    api_key=env_config.get("INTERNAL_EMBED_API_KEY_3", "")
                )
            ]

            # LLM 서버 (기본 2대)
            self.llm_servers = [
                LLMServer(
                    url=env_config.get("INTERNAL_LLM_SERVER_1", "http://11.93.33.10:8080"),
                    name="mischataiapdvv",
                    api_key=env_config.get("INTERNAL_LLM_API_KEY_1", ""),
                    model=env_config.get("INTERNAL_LLM_MODEL_1", "Qwen3-235B-A228-instruct-2507")
                ),
                LLMServer(
                    url=env_config.get("INTERNAL_LLM_SERVER_2", "http://11.93.33.13:8080"),
                    name="mischataidbdvv",
                    api_key=env_config.get("INTERNAL_LLM_API_KEY_2", ""),
                    model=env_config.get("INTERNAL_LLM_MODEL_2", "Qwen3-235B-A228-instruct-2507")
                )
            ]

            print(f"🌍 [ENV] 환경변수에서 기본 서버 설정 로드 완료")

        except Exception as e:
            print(f"❌ [ENV] 환경변수 로드 실패: {str(e)}")

    def select_server(self, servers: List[ServerInfo]) -> Optional[ServerInfo]:
        """사용 가능한 서버 선택 (로드 밸런싱)"""
        if not servers:
            return None

        # 활성 상태 서버 우선 선택
        active_servers = [s for s in servers if s.status == 'active']
        if active_servers:
            return random.choice(active_servers)

        # 활성 서버가 없으면 전체에서 랜덤 선택
        return random.choice(servers)

    async def generate_embedding(self, text: str) -> List[float]:
        """내부 임베딩 서버를 사용한 벡터 임베딩 생성"""
        server = self.select_server(self.embedding_servers)
        if not server:
            raise Exception("사용 가능한 임베딩 서버가 없습니다.")

        print(f"🔄 [EMBED] {server.name}({server.url}) 서버에 임베딩 요청")

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    payload = {
                        "input": text,
                        "model": server.model,
                        "encoding_format": "float"
                    }

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {server.api_key}"
                    } if server.api_key else {"Content-Type": "application/json"}

                    response = await client.post(
                        f"{server.url}/embedding",
                        json=payload,
                        headers=headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        embedding = result.get('data', [{}])[0].get('embedding', [])
                        print(f"✅ [EMBED] 임베딩 생성 완료: {len(embedding)} 차원")
                        return embedding
                    else:
                        print(f"⚠️ [EMBED] HTTP {response.status_code}: {response.text}")

            except Exception as e:
                print(f"❌ [EMBED] Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)  # 재시도 전 대기

        raise Exception(f"임베딩 생성 실패: 모든 재시도 완료")

    async def generate_llm_response(self, message: str, conversation_history: List[Dict] = None) -> str:
        """내부 LLM 서버를 사용한 응답 생성"""
        server = self.select_server(self.llm_servers)
        if not server:
            raise Exception("사용 가능한 LLM 서버가 없습니다.")

        print(f"🤖 [LLM] {server.name}({server.url}) 서버에 요청")

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    # 대화 히스토리 구성
                    messages = []
                    if conversation_history:
                        for msg in conversation_history[-5:]:  # 최근 5개만
                            messages.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })

                    messages.append({
                        "role": "user",
                        "content": message
                    })

                    payload = {
                        "model": server.model,
                        "messages": messages,
                        "max_tokens": 2048,
                        "temperature": 0.7,
                        "stream": False
                    }

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {server.api_key}"
                    } if server.api_key else {"Content-Type": "application/json"}

                    response = await client.post(
                        f"{server.url}/v1/chat/completions",
                        json=payload,
                        headers=headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        assistant_message = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                        print(f"✅ [LLM] 응답 생성 완료: {len(assistant_message)} 문자")
                        return assistant_message
                    else:
                        print(f"⚠️ [LLM] HTTP {response.status_code}: {response.text}")

            except Exception as e:
                print(f"❌ [LLM] Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)

        raise Exception(f"LLM 응답 생성 실패: 모든 재시도 완료")

    async def test_server_connection(self, server_url: str, server_type: str) -> Dict[str, Any]:
        """서버 연결 테스트"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if server_type == "embedding":
                    test_payload = {
                        "input": "connection test",
                        "model": "BAAI/bge-m3",
                        "encoding_format": "float"
                    }
                    test_url = f"{server_url}/embedding"
                else:  # llm
                    test_payload = {
                        "model": "Qwen3-235B-A228-instruct-2507",
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 10
                    }
                    test_url = f"{server_url}/v1/chat/completions"

                response = await client.post(test_url, json=test_payload)

                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0,
                    "message": "연결 성공" if response.status_code == 200 else f"HTTP {response.status_code}"
                }

        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response_time": 0,
                "message": f"연결 실패: {str(e)}"
            }

    async def health_check_all_servers(self) -> Dict[str, Any]:
        """모든 서버 상태 확인"""
        results = {
            "embedding_servers": [],
            "llm_servers": [],
            "summary": {
                "total_servers": 0,
                "active_servers": 0,
                "inactive_servers": 0
            }
        }

        # 임베딩 서버 상태 확인
        for server in self.embedding_servers:
            test_result = await self.test_server_connection(server.url, "embedding")
            server.status = "active" if test_result["success"] else "inactive"
            results["embedding_servers"].append({
                "name": server.name,
                "url": server.url,
                "status": server.status,
                "response_time": test_result["response_time"],
                "message": test_result["message"]
            })

        # LLM 서버 상태 확인
        for server in self.llm_servers:
            test_result = await self.test_server_connection(server.url, "llm")
            server.status = "active" if test_result["success"] else "inactive"
            results["llm_servers"].append({
                "name": server.name,
                "url": server.url,
                "status": server.status,
                "response_time": test_result["response_time"],
                "message": test_result["message"]
            })

        # 요약 정보
        total_servers = len(self.embedding_servers) + len(self.llm_servers)
        active_servers = len([s for s in self.embedding_servers + self.llm_servers if s.status == "active"])

        results["summary"] = {
            "total_servers": total_servers,
            "active_servers": active_servers,
            "inactive_servers": total_servers - active_servers
        }

        return results


# 전역 클라이언트 인스턴스
internal_client = InternalServerClient()


# 편의 함수들
async def generate_internal_embedding_response(text: str) -> List[float]:
    """내부 임베딩 서버 응답 생성 (편의 함수)"""
    return await internal_client.generate_embedding(text)


async def generate_internal_llm_response(message: str, conversation_history: List[Dict] = None) -> str:
    """내부 LLM 서버 응답 생성 (편의 함수)"""
    return await internal_client.generate_llm_response(message, conversation_history)


async def test_internal_server_connection(server_url: str, server_type: str) -> Dict[str, Any]:
    """내부 서버 연결 테스트 (편의 함수)"""
    return await internal_client.test_server_connection(server_url, server_type)


def load_internal_servers_from_config(config: Dict[str, Any]):
    """서버 설정 로드 (편의 함수)"""
    internal_client.load_servers_from_config(config)


def load_internal_servers_from_env(env_config: Dict[str, str]):
    """환경변수에서 서버 설정 로드 (편의 함수)"""
    internal_client.load_servers_from_env(env_config)