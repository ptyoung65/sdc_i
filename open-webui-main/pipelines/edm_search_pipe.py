"""
title: EDM Search Pipeline
author: open-webui
date: 2025-11-01
version: 1.0
license: MIT
description: EDM 문서 검색을 위한 파이프라인 (N8N 워크플로우 연동)
requirements: pydantic, requests
"""

from typing import List, Union, Generator, Iterator, Optional, Dict, Any
from pydantic import BaseModel, Field
import requests
import json
import os


class Pipeline:
    class Valves(BaseModel):
        """파이프라인 설정값"""
        pipelines: List[str] = []
        priority: int = 0

        # N8N 워크플로우 설정
        n8n_base_url: str = Field(
            default=os.getenv("N8N_BASE_URL", "http://169.254.1.2:5678"),
            description="N8N 서버 URL"
        )
        n8n_webhook_path: str = Field(
            default="/webhook/edm-search",
            description="N8N EDM 검색 웹훅 경로"
        )

        # EDM 검색 설정
        default_categories: List[str] = Field(
            default=["edm"],
            description="기본 검색 카테고리"
        )
        max_results: int = Field(
            default=50,
            description="최대 검색 결과 수"
        )

        enable_debug: bool = Field(
            default=True,
            description="디버그 로그 활성화"
        )

    def __init__(self):
        self.type = "pipe"  # pipe 타입
        self.id = "edm_search_pipe"
        self.name = "EDM Search Pipeline"
        self.valves = self.Valves()
        self.debug_log = []

    def _log(self, message: str):
        """디버그 로그 기록"""
        if self.valves.enable_debug:
            self.debug_log.append(message)
            print(f"[EDM Search] {message}")

    def _call_n8n_webhook(
        self,
        query: str,
        categories: List[str],
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        N8N 웹훅 호출하여 EDM 문서 검색

        Args:
            query: 검색 쿼리
            categories: 검색 카테고리 리스트
            chat_id: 채팅 ID (옵션)
            user_id: 사용자 ID (옵션)

        Returns:
            검색 결과 딕셔너리
        """
        try:
            url = f"{self.valves.n8n_base_url}{self.valves.n8n_webhook_path}"
            self._log(f"N8N 웹훅 호출: {url}")

            payload = {
                "message": query,
                "categories": categories or self.valves.default_categories,
                "chat_id": chat_id,
                "user_id": user_id
            }

            self._log(f"Payload: {json.dumps(payload, ensure_ascii=False)}")

            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if not response.ok:
                raise Exception(f"N8N 웹훅 호출 실패: {response.status_code} {response.text}")

            result = response.json()
            self._log(f"N8N 응답: {len(result.get('documents', []))}개 문서")

            return result

        except Exception as e:
            self._log(f"N8N 호출 오류: {str(e)}")
            raise

    def pipe(
        self,
        body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        파이프라인 메인 로직

        Args:
            body: 요청 본문 (query, categories, chatId, userId 포함)

        Returns:
            검색 결과 (List[dict] 형태)
        """
        try:
            self._log("=" * 50)
            self._log("EDM Search 파이프라인 시작")

            # 입력 파라미터 추출
            query = body.get("query", "")
            categories = body.get("categories", self.valves.default_categories)
            chat_id = body.get("chatId")
            user_id = body.get("userId")

            if not query:
                raise ValueError("검색 쿼리가 없습니다")

            self._log(f"검색 쿼리: {query}")
            self._log(f"카테고리: {categories}")
            self._log(f"Chat ID: {chat_id}")
            self._log(f"User ID: {user_id}")

            # N8N 웹훅 호출
            n8n_result = self._call_n8n_webhook(
                query=query,
                categories=categories,
                chat_id=chat_id,
                user_id=user_id
            )

            # 결과 포맷 변환
            documents = n8n_result.get("documents", [])
            total_count = n8n_result.get("total_count", len(documents))

            self._log(f"검색 결과: {total_count}개 문서")

            # 결과 반환 (List[dict] 형태)
            result = {
                "documents": documents,
                "total_count": total_count,
                "query": query,
                "categories": categories,
                "status": "success"
            }

            self._log("EDM Search 파이프라인 완료")
            self._log("=" * 50)

            return result

        except Exception as e:
            error_msg = f"EDM Search 파이프라인 오류: {str(e)}"
            self._log(error_msg)

            return {
                "documents": [],
                "total_count": 0,
                "query": body.get("query", ""),
                "categories": body.get("categories", []),
                "status": "error",
                "error": str(e)
            }


# Pipeline 인스턴스 생성 (Open WebUI에서 자동으로 로드)
def get_pipeline():
    return Pipeline()
