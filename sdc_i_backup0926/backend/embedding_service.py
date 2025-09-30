#!/usr/bin/env python3
"""
통합 임베딩 서비스
1. 자체 임베딩: sentence-transformers, KURE-v1 (로컬)
2. 내부 서버 임베딩: BGE-M3 모델 (외부 API)
"""

import os
import json
import torch
import numpy as np
import requests
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from transformers import AutoTokenizer, AutoModel
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KoreanEmbeddingService:
    """통합 임베딩 서비스 클래스"""

    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        self.current_model = None
        self.embedding_mode = "bge-m3"  # 기본값: BGE-M3 서버

        # BGE-M3 서버 설정 (기본값)
        self.bge_m3_servers = [
            {
                "id": "sdcrpapocv",
                "name": "sdcrpapocv",
                "url": "http://11.93.26.130:8080",
                "api_key": "••••••••••••••••••••••••••••••••",
                "is_primary": True
            },
            {
                "id": "sdcalpocv2",
                "name": "sdcalpocv2",
                "url": "http://11.93.26.43:8080",
                "api_key": "••••••••••••••••••••••••••••••••",
                "is_primary": False
            },
            {
                "id": "mischataiappddv",
                "name": "mischataiappddv",
                "url": "http://11.93.33.10:8080",
                "api_key": "••••••••••••••••••••••••••••••••",
                "is_primary": False
            }
        ]

        # 로컬 모델 설정
        self.local_model_configs = {
            "kure-v1": {
                "model_name": "klue/roberta-large",  # KURE-v1 호환 모델
                "description": "한국어 KURE-v1 임베딩 모델 (로컬)",
                "max_length": 512
            },
            "sentence-transformers": {
                "model_name": "klue/roberta-base",
                "description": "Sentence Transformers 기반 모델 (로컬)",
                "max_length": 512
            }
        }

    def set_embedding_mode(self, mode: str):
        """임베딩 모드 설정 (bge-m3, kure-v1, sentence-transformers)"""
        self.embedding_mode = mode
        logger.info(f"임베딩 모드 변경: {mode}")

    def get_primary_bge_server(self) -> Optional[Dict]:
        """기본 BGE-M3 서버 반환"""
        for server in self.bge_m3_servers:
            if server.get("is_primary", False):
                return server
        return self.bge_m3_servers[0] if self.bge_m3_servers else None

    async def embed_with_bge_m3(self, texts: List[str]) -> List[List[float]]:
        """BGE-M3 서버로 임베딩 요청"""
        server = self.get_primary_bge_server()
        if not server:
            raise RuntimeError("사용 가능한 BGE-M3 서버가 없습니다")

        try:
            async with aiohttp.ClientSession() as session:
                embed_data = {
                    "texts": texts,
                    "model": "bge-m3"
                }

                headers = {
                    "Authorization": f"Bearer {server['api_key']}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    f"{server['url']}/embed",
                    json=embed_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("embeddings", [])
                    else:
                        logger.error(f"BGE-M3 서버 오류: {response.status}")
                        raise RuntimeError(f"BGE-M3 서버 응답 오류: {response.status}")

        except Exception as e:
            logger.error(f"BGE-M3 임베딩 실패: {e}")
            raise

    def load_local_model(self, model_key: str) -> bool:
        """로컬 모델 로드"""
        try:
            if model_key not in self.local_model_configs:
                logger.error(f"지원하지 않는 로컬 모델: {model_key}")
                return False

            config = self.local_model_configs[model_key]
            model_name = config["model_name"]

            logger.info(f"로컬 모델 로드 시작: {model_name}")

            # 캐시 디렉토리 설정 (오프라인 우선)
            cache_dir = "../offline_packages/models"
            os.makedirs(cache_dir, exist_ok=True)

            # 토크나이저 로드
            self.tokenizers[model_key] = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                local_files_only=False  # 오프라인에서 먼저 시도, 없으면 다운로드
            )

            # 모델 로드
            self.models[model_key] = AutoModel.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                local_files_only=False
            )

            self.current_model = model_key
            logger.info(f"로컬 모델 로드 완료: {model_name}")
            return True

        except Exception as e:
            logger.error(f"로컬 모델 로드 실패: {e}")
            return False

    async def encode_text(self, texts: List[str], mode: Optional[str] = None) -> List[List[float]]:
        """텍스트를 벡터로 인코딩 (모드에 따라 다른 처리)"""
        if mode is None:
            mode = self.embedding_mode

        logger.info(f"임베딩 처리 시작: 모드={mode}, 텍스트 수={len(texts)}")

        if mode == "bge-m3":
            # BGE-M3 서버 API 사용
            return await self.embed_with_bge_m3(texts)

        elif mode in ["kure-v1", "sentence-transformers"]:
            # 로컬 모델 사용
            return await self.encode_with_local_model(texts, mode)

        else:
            raise ValueError(f"지원하지 않는 임베딩 모드: {mode}")

    async def encode_with_local_model(self, texts: List[str], model_key: str) -> List[List[float]]:
        """로컬 모델로 임베딩 생성"""
        if model_key not in self.models:
            if not self.load_local_model(model_key):
                raise RuntimeError(f"로컬 모델 로드 실패: {model_key}")

        model = self.models[model_key]
        tokenizer = self.tokenizers[model_key]
        config = self.local_model_configs[model_key]

        # 배치 처리
        inputs = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=config["max_length"],
            return_tensors="pt"
        )

        # 모델 추론
        with torch.no_grad():
            outputs = model(**inputs)
            # [CLS] 토큰의 벡터를 문장 임베딩으로 사용
            embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()

        # numpy array를 list로 변환
        return [embedding.tolist() for embedding in embeddings]

    def get_available_models(self) -> Dict[str, Any]:
        """사용 가능한 모델 목록 반환"""
        models_info = {}

        # BGE-M3 서버 모델
        models_info["bge-m3"] = {
            "description": "BGE-M3 모델 (내부 서버)",
            "type": "server",
            "loaded": True,
            "current": self.embedding_mode == "bge-m3",
            "is_default": True
        }

        # 로컬 모델들
        for key, config in self.local_model_configs.items():
            models_info[key] = {
                "description": config["description"],
                "type": "local",
                "loaded": key in self.models,
                "current": self.embedding_mode == key,
                "is_default": False
            }

        return models_info

    async def encode_single(self, text: str, mode: Optional[str] = None) -> List[float]:
        """단일 텍스트 인코딩 (API 호출용)"""
        embeddings = await self.encode_text([text], mode)
        return embeddings[0] if embeddings else []

    def get_embedding_info(self) -> Dict[str, Any]:
        """현재 임베딩 설정 정보 반환"""
        return {
            "current_mode": self.embedding_mode,
            "available_modes": list(self.get_available_models().keys()),
            "bge_servers": [
                {
                    "id": server["id"],
                    "name": server["name"],
                    "url": server["url"],
                    "is_primary": server.get("is_primary", False)
                }
                for server in self.bge_m3_servers
            ]
        }

# 전역 서비스 인스턴스
embedding_service = KoreanEmbeddingService()

def test_embedding_service():
    """임베딩 서비스 테스트"""
    try:
        # 모델 로드 테스트
        logger.info("임베딩 서비스 테스트 시작")

        # KLUE RoBERTa 베이스 모델로 테스트 (더 가벼움)
        if embedding_service.load_model("klue-roberta"):
            logger.info("모델 로드 성공")

            # 테스트 텍스트
            test_texts = [
                "안녕하세요. 한국어 임베딩 테스트입니다.",
                "This is a test for Korean embedding service.",
                "문서 처리 시스템에서 사용할 임베딩 벡터를 생성합니다."
            ]

            # 임베딩 생성
            embeddings = embedding_service.encode_text(test_texts)
            logger.info(f"임베딩 생성 완료: {embeddings.shape}")

            # 사용 가능한 모델 확인
            models = embedding_service.get_available_models()
            logger.info(f"사용 가능한 모델: {models}")

            return True
        else:
            logger.error("모델 로드 실패")
            return False

    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        return False

if __name__ == "__main__":
    # 테스트 실행
    test_embedding_service()