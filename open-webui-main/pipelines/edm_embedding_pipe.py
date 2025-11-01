"""
title: EDM Embedding Pipeline
author: open-webui
date: 2025-11-01
version: 1.0
license: MIT
description: EDM 문서 임베딩 파이프라인 (파싱, 청킹, 임베딩, Milvus 저장)
requirements: pydantic, requests, pymilvus, sentence-transformers, pypdf2, python-docx
"""

from typing import List, Union, Generator, Iterator, Optional, Dict, Any
from pydantic import BaseModel, Field
import requests
import json
import os
from pathlib import Path
import hashlib


class Pipeline:
    class Valves(BaseModel):
        """파이프라인 설정값"""
        pipelines: List[str] = []
        priority: int = 0

        # Milvus 설정
        milvus_host: str = Field(
            default=os.getenv("MILVUS_HOST", "169.254.1.2"),
            description="Milvus 호스트"
        )
        milvus_port: str = Field(
            default=os.getenv("MILVUS_PORT", "19530"),
            description="Milvus 포트"
        )
        milvus_collection: str = Field(
            default="edm_documents",
            description="Milvus 컬렉션명"
        )

        # 임베딩 모델 설정
        embedding_model: str = Field(
            default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            description="임베딩 모델명"
        )
        embedding_dimension: int = Field(
            default=768,
            description="임베딩 차원"
        )

        # 청킹 설정
        chunk_size: int = Field(
            default=500,
            description="청크 크기 (문자 수)"
        )
        chunk_overlap: int = Field(
            default=50,
            description="청크 오버랩 크기"
        )

        enable_debug: bool = Field(
            default=True,
            description="디버그 로그 활성화"
        )

    def __init__(self):
        self.type = "pipe"  # pipe 타입
        self.id = "edm_embedding_pipe"
        self.name = "EDM Embedding Pipeline"
        self.valves = self.Valves()
        self.debug_log = []

        # 임베딩 모델 초기화 (지연 로딩)
        self.embedding_model_instance = None
        self.milvus_client = None

    def _log(self, message: str):
        """디버그 로그 기록"""
        if self.valves.enable_debug:
            self.debug_log.append(message)
            print(f"[EDM Embedding] {message}")

    def _init_embedding_model(self):
        """임베딩 모델 초기화"""
        if self.embedding_model_instance is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._log(f"임베딩 모델 로딩: {self.valves.embedding_model}")
                self.embedding_model_instance = SentenceTransformer(self.valves.embedding_model)
                self._log("임베딩 모델 로딩 완료")
            except Exception as e:
                self._log(f"임베딩 모델 로딩 실패: {str(e)}")
                raise

    def _init_milvus_client(self):
        """Milvus 클라이언트 초기화"""
        if self.milvus_client is None:
            try:
                from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

                self._log(f"Milvus 연결 중: {self.valves.milvus_host}:{self.valves.milvus_port}")

                connections.connect(
                    alias="default",
                    host=self.valves.milvus_host,
                    port=self.valves.milvus_port
                )

                # 컬렉션 존재 확인
                if not utility.has_collection(self.valves.milvus_collection):
                    self._log(f"컬렉션 생성 중: {self.valves.milvus_collection}")
                    self._create_collection()

                self.milvus_client = Collection(self.valves.milvus_collection)
                self._log("Milvus 연결 완료")

            except Exception as e:
                self._log(f"Milvus 연결 실패: {str(e)}")
                raise

    def _create_collection(self):
        """Milvus 컬렉션 생성"""
        from pymilvus import Collection, FieldSchema, CollectionSchema, DataType

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.valves.embedding_dimension),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2000)
        ]

        schema = CollectionSchema(fields, description="EDM 문서 임베딩 컬렉션")
        collection = Collection(name=self.valves.milvus_collection, schema=schema)

        # 인덱스 생성
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        self._log("컬렉션 및 인덱스 생성 완료")

    def _parse_file(self, file_path: str, file_name: str) -> str:
        """
        파일 파싱하여 텍스트 추출

        Args:
            file_path: 파일 경로
            file_name: 파일명

        Returns:
            추출된 텍스트
        """
        try:
            file_ext = Path(file_name).suffix.lower()
            self._log(f"파일 파싱 시작: {file_name} ({file_ext})")

            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()

            elif file_ext == '.pdf':
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
                except ImportError:
                    self._log("PyPDF2 not installed. Falling back to text extraction.")
                    return ""

            elif file_ext in ['.docx', '.doc']:
                try:
                    from docx import Document
                    doc = Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    return text
                except ImportError:
                    self._log("python-docx not installed. Falling back to text extraction.")
                    return ""

            else:
                # 기타 파일은 텍스트로 읽기 시도
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()

        except Exception as e:
            self._log(f"파일 파싱 오류: {str(e)}")
            return ""

    def _chunk_text(self, text: str) -> List[str]:
        """
        텍스트 청킹

        Args:
            text: 원본 텍스트

        Returns:
            청크 리스트
        """
        chunks = []
        chunk_size = self.valves.chunk_size
        overlap = self.valves.chunk_overlap

        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            if chunk.strip():
                chunks.append(chunk)

            start = end - overlap

        self._log(f"텍스트 청킹 완료: {len(chunks)}개 청크")
        return chunks

    def _embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        """
        청크 임베딩

        Args:
            chunks: 청크 리스트

        Returns:
            임베딩 벡터 리스트
        """
        self._init_embedding_model()

        self._log(f"임베딩 생성 중: {len(chunks)}개 청크")
        embeddings = self.embedding_model_instance.encode(chunks, convert_to_numpy=True)

        return embeddings.tolist()

    def _store_in_milvus(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        file_name: str,
        metadata: Dict[str, Any]
    ) -> int:
        """
        Milvus에 임베딩 저장

        Args:
            chunks: 청크 리스트
            embeddings: 임베딩 벡터 리스트
            file_name: 파일명
            metadata: 메타데이터

        Returns:
            저장된 벡터 수
        """
        self._init_milvus_client()

        # 데이터 준비
        ids = []
        texts = []
        file_names = []
        chunk_indices = []
        metadatas = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # 고유 ID 생성
            chunk_id = hashlib.md5(f"{file_name}_{i}_{chunk[:50]}".encode()).hexdigest()

            ids.append(chunk_id)
            texts.append(chunk[:65535])  # VARCHAR 최대 길이 제한
            file_names.append(file_name[:500])
            chunk_indices.append(i)
            metadatas.append(json.dumps(metadata, ensure_ascii=False)[:2000])

        # Milvus에 삽입
        self._log(f"Milvus에 저장 중: {len(ids)}개 벡터")

        entities = [
            ids,
            embeddings,
            texts,
            file_names,
            chunk_indices,
            metadatas
        ]

        self.milvus_client.insert(entities)
        self.milvus_client.flush()

        self._log(f"Milvus 저장 완료: {len(ids)}개 벡터")
        return len(ids)

    def pipe(
        self,
        body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        파이프라인 메인 로직

        Args:
            body: 요청 본문 (fileName, filePath, metadata 포함)

        Returns:
            임베딩 결과
        """
        try:
            self._log("=" * 50)
            self._log("EDM Embedding 파이프라인 시작")

            # 입력 파라미터 추출
            file_name = body.get("fileName")
            file_path = body.get("filePath")
            metadata = body.get("metadata", {})

            if not file_name:
                raise ValueError("파일명이 없습니다")
            if not file_path:
                raise ValueError("파일 경로가 없습니다")
            if not os.path.exists(file_path):
                raise ValueError(f"파일이 존재하지 않습니다: {file_path}")

            self._log(f"파일명: {file_name}")
            self._log(f"파일 경로: {file_path}")

            # 1. 파일 파싱
            text = self._parse_file(file_path, file_name)
            if not text:
                raise ValueError("파일에서 텍스트를 추출할 수 없습니다")

            self._log(f"추출된 텍스트 길이: {len(text)} 문자")

            # 2. 청킹
            chunks = self._chunk_text(text)
            if not chunks:
                raise ValueError("청크를 생성할 수 없습니다")

            # 3. 임베딩
            embeddings = self._embed_chunks(chunks)

            # 4. Milvus 저장
            vector_count = self._store_in_milvus(
                chunks=chunks,
                embeddings=embeddings,
                file_name=file_name,
                metadata=metadata
            )

            result = {
                "fileName": file_name,
                "filePath": file_path,
                "chunkCount": len(chunks),
                "vectorCount": vector_count,
                "status": "success"
            }

            self._log("EDM Embedding 파이프라인 완료")
            self._log("=" * 50)

            return result

        except Exception as e:
            error_msg = f"EDM Embedding 파이프라인 오류: {str(e)}"
            self._log(error_msg)

            return {
                "fileName": body.get("fileName", ""),
                "filePath": body.get("filePath", ""),
                "chunkCount": 0,
                "vectorCount": 0,
                "status": "error",
                "error": str(e)
            }


# Pipeline 인스턴스 생성 (Open WebUI에서 자동으로 로드)
def get_pipeline():
    return Pipeline()
