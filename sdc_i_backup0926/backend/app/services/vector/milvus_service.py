"""
Milvus Vector Storage Service
청킹된 문서를 벡터화하여 Milvus에 저장하는 서비스
"""

import os
import json
import uuid
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime

# Milvus 클라이언트
try:
    from pymilvus import (
        connections, utility, FieldSchema, CollectionSchema, DataType,
        Collection, MilvusException
    )
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    print("⚠️ [MILVUS] Milvus 클라이언트가 설치되지 않음 - pip install pymilvus")

# 임베딩 서비스
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# 청킹 서비스
from ..document.enhanced_chunker import DocumentChunk, ChunkMetadata

logger = logging.getLogger(__name__)

@dataclass
class VectorDocument:
    """벡터화된 문서 정보"""
    document_id: str
    document_name: str
    chunking_method: str
    total_chunks: int
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class VectorChunk:
    """벡터화된 청크"""
    chunk_id: str
    document_id: str
    text: str
    vector: List[float]
    metadata: Dict[str, Any]
    chunk_index: int

class EmbeddingService:
    """임베딩 생성 서비스"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.dimension = 384  # 기본 차원

        # Sentence Transformers 모델 로드
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                self.dimension = self.model.get_sentence_embedding_dimension()
                logger.info(f"임베딩 모델 로드됨: {model_name}, 차원: {self.dimension}")
            except Exception as e:
                logger.error(f"Sentence Transformers 모델 로드 실패: {e}")
                self.model = None

    async def embed_text(self, text: str) -> List[float]:
        """텍스트를 벡터로 변환"""
        if self.model:
            try:
                # Sentence Transformers 사용
                embedding = self.model.encode(text)
                return embedding.tolist()
            except Exception as e:
                logger.error(f"임베딩 생성 실패: {e}")

        # 대체 방법: 간단한 TF-IDF 기반 벡터 (개발용)
        return self._simple_embedding(text)

    def _simple_embedding(self, text: str) -> List[float]:
        """간단한 임베딩 생성 (개발용)"""
        # 간단한 해시 기반 벡터 생성
        import hashlib
        hash_value = hashlib.md5(text.encode()).hexdigest()
        vector = []
        for i in range(0, min(len(hash_value), self.dimension * 2), 2):
            hex_pair = hash_value[i:i+2]
            vector.append(int(hex_pair, 16) / 255.0 - 0.5)

        # 벡터 길이를 맞춤
        while len(vector) < self.dimension:
            vector.append(0.0)

        return vector[:self.dimension]

    async def embed_chunks(self, chunks: List[DocumentChunk]) -> List[VectorChunk]:
        """청크들을 벡터화"""
        vector_chunks = []

        for chunk in chunks:
            try:
                vector = await self.embed_text(chunk.text)

                vector_chunk = VectorChunk(
                    chunk_id=chunk.chunk_id,
                    document_id="",  # 나중에 설정
                    text=chunk.text,
                    vector=vector,
                    metadata={
                        "chunk_index": chunk.metadata.chunk_index,
                        "source_page": chunk.metadata.source_page,
                        "source_slide": chunk.metadata.source_slide,
                        "source_sheet": chunk.metadata.source_sheet,
                        "content_type": chunk.metadata.content_type,
                        "confidence_score": chunk.metadata.confidence_score,
                        "length": chunk.length
                    },
                    chunk_index=chunk.metadata.chunk_index
                )
                vector_chunks.append(vector_chunk)

            except Exception as e:
                logger.error(f"청크 벡터화 실패 {chunk.chunk_id}: {e}")

        return vector_chunks

class MilvusService:
    """Milvus 벡터 데이터베이스 서비스"""

    def __init__(self,
                 host: str = "localhost",
                 port: int = 19530,
                 collection_name: str = "document_chunks"):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.collection = None
        self.embedding_service = EmbeddingService()

        if not MILVUS_AVAILABLE:
            logger.warning("Milvus가 사용 불가능합니다. 벡터 저장 기능이 제한됩니다.")
            return

        # Milvus 연결 시도
        try:
            self._connect()
            self._create_collection()
            logger.info(f"Milvus 서비스 초기화 완료: {host}:{port}")
        except Exception as e:
            logger.error(f"Milvus 연결 실패: {e}")

    def _connect(self):
        """Milvus 연결"""
        if not MILVUS_AVAILABLE:
            return

        try:
            connections.connect("default", host=self.host, port=self.port)
            logger.info("Milvus 연결 성공")
        except Exception as e:
            logger.error(f"Milvus 연결 실패: {e}")
            raise

    def _create_collection(self):
        """컬렉션 생성"""
        if not MILVUS_AVAILABLE:
            return

        try:
            # 컬렉션이 이미 존재하는지 확인
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"기존 컬렉션 로드: {self.collection_name}")
                return

            # 스키마 정의
            fields = [
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8000),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_service.dimension),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2000),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="created_at", dtype=DataType.INT64)
            ]

            schema = CollectionSchema(fields, f"SDC Document Chunks Collection")

            # 컬렉션 생성
            self.collection = Collection(self.collection_name, schema)

            # 인덱스 생성
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }

            self.collection.create_index("vector", index_params)
            logger.info(f"새 컬렉션 생성: {self.collection_name}")

        except Exception as e:
            logger.error(f"컬렉션 생성 실패: {e}")
            raise

    async def store_document_chunks(self,
                                  document_id: str,
                                  document_name: str,
                                  chunks: List[DocumentChunk],
                                  chunking_method: str) -> bool:
        """문서 청크들을 벡터화하여 Milvus에 저장"""
        if not MILVUS_AVAILABLE or not self.collection:
            logger.warning("Milvus를 사용할 수 없어 벡터 저장을 건너뜁니다.")
            return False

        try:
            # 청크들을 벡터화
            vector_chunks = await self.embedding_service.embed_chunks(chunks)

            # 문서 ID 설정
            for vector_chunk in vector_chunks:
                vector_chunk.document_id = document_id

            # Milvus에 삽입할 데이터 준비
            data = [
                [chunk.chunk_id for chunk in vector_chunks],  # chunk_id
                [chunk.document_id for chunk in vector_chunks],  # document_id
                [chunk.text[:8000] for chunk in vector_chunks],  # text (길이 제한)
                [chunk.vector for chunk in vector_chunks],  # vector
                [json.dumps(chunk.metadata, ensure_ascii=False)[:2000] for chunk in vector_chunks],  # metadata
                [chunk.chunk_index for chunk in vector_chunks],  # chunk_index
                [int(datetime.now().timestamp()) for _ in vector_chunks]  # created_at
            ]

            # 데이터 삽입
            self.collection.insert(data)
            self.collection.flush()

            logger.info(f"문서 {document_name}의 {len(vector_chunks)}개 청크를 Milvus에 저장했습니다.")
            return True

        except Exception as e:
            logger.error(f"벡터 저장 실패: {e}")
            return False

    async def search_similar_chunks(self,
                                  query_text: str,
                                  top_k: int = 5,
                                  document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """유사한 청크 검색"""
        if not MILVUS_AVAILABLE or not self.collection:
            logger.warning("Milvus를 사용할 수 없어 빈 결과를 반환합니다.")
            return []

        try:
            # 컬렉션 로드
            self.collection.load()

            # 쿼리 텍스트 벡터화
            query_vector = await self.embedding_service.embed_text(query_text)

            # 검색 파라미터
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }

            # 검색 조건
            expr = None
            if document_id:
                expr = f'document_id == "{document_id}"'

            # 검색 실행
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["chunk_id", "document_id", "text", "metadata", "chunk_index"]
            )

            # 결과 변환
            similar_chunks = []
            for result in results[0]:
                chunk_data = {
                    "chunk_id": result.entity.get("chunk_id"),
                    "document_id": result.entity.get("document_id"),
                    "text": result.entity.get("text"),
                    "metadata": json.loads(result.entity.get("metadata", "{}")),
                    "chunk_index": result.entity.get("chunk_index"),
                    "similarity_score": float(result.score),
                    "distance": float(result.distance)
                }
                similar_chunks.append(chunk_data)

            return similar_chunks

        except Exception as e:
            logger.error(f"유사 청크 검색 실패: {e}")
            return []

    async def delete_document_chunks(self, document_id: str) -> bool:
        """문서의 모든 청크 삭제"""
        if not MILVUS_AVAILABLE or not self.collection:
            return False

        try:
            expr = f'document_id == "{document_id}"'
            self.collection.delete(expr)
            self.collection.flush()

            logger.info(f"문서 {document_id}의 모든 청크를 삭제했습니다.")
            return True

        except Exception as e:
            logger.error(f"청크 삭제 실패: {e}")
            return False

    async def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 정보"""
        if not MILVUS_AVAILABLE or not self.collection:
            return {"available": False}

        try:
            stats = self.collection.num_entities
            return {
                "available": True,
                "total_chunks": stats,
                "collection_name": self.collection_name,
                "dimension": self.embedding_service.dimension
            }
        except Exception as e:
            logger.error(f"통계 정보 가져오기 실패: {e}")
            return {"available": False, "error": str(e)}

# 싱글톤 인스턴스
milvus_service = None

def get_milvus_service() -> MilvusService:
    """Milvus 서비스 인스턴스 가져오기"""
    global milvus_service
    if milvus_service is None:
        milvus_service = MilvusService()
    return milvus_service