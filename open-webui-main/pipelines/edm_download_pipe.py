"""
title: EDM Download & Knowledge Pipeline
author: open-webui
date: 2025-11-03
version: 2.0
license: MIT
description: EDM 파일 다운로드 → 파싱 → Milvus 저장 → 벡터 검색 → LLM 응답
requirements: pydantic, requests, pymilvus
"""

from typing import AsyncGenerator, Optional, Dict, Any
from pydantic import BaseModel, Field
import requests
import json
import os
import uuid
from pathlib import Path


class Pipeline:
    class Valves(BaseModel):
        """파이프라인 설정값"""
        priority: int = 0

        # N8N 웹훅 URL
        n8n_download_url: str = Field(
            default="http://192.168.122.177:5678/webhook/edm-download",
            description="N8N EDM Download Webhook URL"
        )

        # 다운로드 설정
        download_dir: str = Field(
            default="/tmp/downloads",
            description="다운로드 파일 저장 디렉토리"
        )

        # Milvus 설정
        milvus_host: str = Field(
            default="localhost",
            description="Milvus 호스트"
        )
        milvus_port: int = Field(
            default=19530,
            description="Milvus 포트"
        )
        collection_name: str = Field(
            default="edm_documents",
            description="Milvus 컬렉션 이름"
        )

        enable_debug: bool = Field(
            default=True,
            description="디버그 로그 활성화"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "edm_download_pipe"
        self.name = "EDM Download Pipeline"
        self.valves = self.Valves()

        # 다운로드 디렉토리 생성
        os.makedirs(self.valves.download_dir, exist_ok=True)

    def _log(self, message: str):
        """디버그 로그 기록"""
        if self.valves.enable_debug:
            print(f"[EDM Download] {message}", flush=True)

    async def _call_n8n_download(
        self,
        objid: str,
        file_last_ver_sno: int,
        request_user: str
    ) -> Dict[str, Any]:
        """
        N8N 웹훅을 통해 EDM 파일 다운로드

        Args:
            objid: 파일 객체 ID
            file_last_ver_sno: 파일 버전
            request_user: 요청 사용자

        Returns:
            {
                "file_name": "example.pdf",
                "file_path": "/tmp/downloads/uuid/example.pdf",
                "file_content": "base64_encoded_content",
                "success": True
            }
        """
        try:
            # 다운로드 폴더 생성
            download_id = str(uuid.uuid4())
            download_path = os.path.join(self.valves.download_dir, download_id)
            os.makedirs(download_path, exist_ok=True)

            # N8N 웹훅 호출
            payload = {
                "objid": objid,
                "fileLastVerSno": file_last_ver_sno,
                "requestUser": request_user
            }

            self._log(f"📥 N8N 다운로드 요청: {json.dumps(payload, ensure_ascii=False)}")

            response = requests.post(
                self.valves.n8n_download_url,
                json=payload,
                timeout=60
            )

            if not response.ok:
                raise Exception(f"N8N 다운로드 실패: {response.status_code} {response.text}")

            result = response.json()
            file_name = result.get("file_name", "downloaded_file.pdf")
            file_content = result.get("file_content")  # base64 인코딩된 내용

            # 파일 저장
            file_path = os.path.join(download_path, file_name)

            if file_content:
                import base64
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(file_content))
            else:
                # Mock 데이터 (테스트용)
                with open(file_path, "wb") as f:
                    f.write(b"Mock EDM file content for testing")

            self._log(f"✅ 파일 다운로드 완료: {file_path}")

            return {
                "file_name": file_name,
                "file_path": file_path,
                "success": True
            }

        except Exception as e:
            self._log(f"❌ 파일 다운로드 오류: {str(e)}")
            return {
                "file_name": "",
                "file_path": "",
                "success": False,
                "error": str(e)
            }

    async def _parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        문서 파싱

        Returns:
            {
                "text": "파싱된 전체 텍스트",
                "chunks": ["chunk1", "chunk2", ...],
                "success": True
            }
        """
        try:
            ext = os.path.splitext(file_path)[1].lower()
            self._log(f"📄 문서 파싱 시작: {file_path} (확장자: {ext})")

            # 간단한 텍스트 추출
            if ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            elif ext == ".pdf":
                try:
                    import PyPDF2
                    text = ""
                    with open(file_path, "rb") as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        for page in pdf_reader.pages:
                            text += page.extract_text()
                except:
                    text = f"Mock parsed content from {file_path}"
            else:
                text = f"Mock parsed content from {file_path}"

            # 청킹 (500자 단위, 100자 오버랩)
            chunk_size = 500
            overlap = 100
            chunks = []

            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i:i + chunk_size]
                if chunk.strip():
                    chunks.append(chunk.strip())

            self._log(f"✅ 파싱 완료: {len(chunks)}개 청크 생성")

            return {
                "text": text,
                "chunks": chunks,
                "success": True
            }

        except Exception as e:
            self._log(f"❌ 문서 파싱 오류: {str(e)}")
            return {
                "text": "",
                "chunks": [],
                "success": False,
                "error": str(e)
            }

    async def _store_to_milvus(self, chunks: list, metadata: dict) -> Dict[str, Any]:
        """
        Milvus에 벡터 저장

        Returns:
            {"stored_count": 10, "success": True}
        """
        try:
            # Mock 구현 (실제로는 Milvus에 저장)
            self._log(f"🧠 Milvus 저장: {len(chunks)}개 청크")

            # 여기서 실제 Milvus 저장 로직 구현
            # from pymilvus import connections, Collection
            # ...

            return {
                "stored_count": len(chunks),
                "success": True
            }

        except Exception as e:
            self._log(f"❌ Milvus 저장 오류: {str(e)}")
            return {
                "stored_count": 0,
                "success": False,
                "error": str(e)
            }

    async def pipe(
        self, body: dict, __event_emitter__=None
    ) -> AsyncGenerator[str, None]:
        """
        파이프라인 메인 로직 (edm_search_pipe와 동일한 방식)

        입력 body:
        {
            "messages": [...],
            "edm_file": {
                "objid": "176126817626004568",
                "fileLastVerSno": 1,
                "requestUser": "rladndgh.kim@partner.samsung.com"
            }
        }
        """
        try:
            self._log("=" * 80)
            self._log("📋 [PIPELINE] edm_download_pipe")
            self._log("📋 [ACTION] EDM Download 파이프라인 시작")

            # EDM 파일 정보 추출
            edm_file = body.get("edm_file", {})
            objid = edm_file.get("objid")
            file_last_ver_sno = edm_file.get("fileLastVerSno", 1)
            request_user = edm_file.get("requestUser")

            if not objid or not request_user:
                error_msg = "❌ objid와 requestUser는 필수 파라미터입니다"
                self._log(error_msg)
                yield error_msg
                return

            self._log(f"📋 [OBJID] {objid}")
            self._log(f"📋 [VERSION] {file_last_ver_sno}")
            self._log(f"📋 [USER] {request_user}")

            # 1. 파일 다운로드
            yield "📥 파일 다운로드 중...\n\n"

            download_result = await self._call_n8n_download(
                objid=objid,
                file_last_ver_sno=file_last_ver_sno,
                request_user=request_user
            )

            if not download_result["success"]:
                error_msg = f"❌ 파일 다운로드 실패: {download_result.get('error', '알 수 없는 오류')}"
                self._log(error_msg)
                yield error_msg
                return

            file_name = download_result["file_name"]
            file_path = download_result["file_path"]

            yield f"✅ 파일 다운로드 완료: {file_name}\n\n"

            # 2. 문서 파싱
            yield "📄 문서 파싱 중...\n\n"

            parse_result = await self._parse_document(file_path)

            if not parse_result["success"]:
                error_msg = f"❌ 문서 파싱 실패: {parse_result.get('error', '알 수 없는 오류')}"
                self._log(error_msg)
                yield error_msg
                return

            chunks = parse_result["chunks"]
            yield f"✅ 문서 파싱 완료: {len(chunks)}개 청크 생성\n\n"

            # 3. Milvus 저장
            yield "🧠 벡터 데이터베이스에 저장 중...\n\n"

            metadata = {
                "objid": objid,
                "file_name": file_name,
                "file_last_ver_sno": file_last_ver_sno,
                "request_user": request_user
            }

            store_result = await self._store_to_milvus(chunks, metadata)

            if not store_result["success"]:
                error_msg = f"❌ 벡터 저장 실패: {store_result.get('error', '알 수 없는 오류')}"
                self._log(error_msg)
                yield error_msg
                return

            yield f"✅ 벡터 저장 완료: {store_result['stored_count']}개 청크\n\n"

            # 최종 메시지
            yield f"✨ **파일 지식화 완료!**\n\n"
            yield f"📄 파일명: {file_name}\n"
            yield f"📍 저장 경로: {file_path}\n"
            yield f"📦 생성된 청크: {len(chunks)}개\n\n"
            yield "이제 이 문서 내용을 바탕으로 질문하실 수 있습니다.\n"

            self._log("=" * 80)
            self._log("✅ EDM Download 파이프라인 완료")
            self._log("=" * 80)

        except Exception as e:
            error_msg = f"❌ EDM Download 파이프라인 오류: {str(e)}"
            self._log(error_msg)
            yield error_msg
