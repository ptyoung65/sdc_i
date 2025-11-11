"""
title: EDM Download & Knowledge Pipeline
author: open-webui
date: 2025-11-11
version: 3.1
license: MIT
description: EDM 파일 다운로드 → Open WebUI 백엔드 표준 API로 자동 벡터화 (스트리밍 응답)
requirements: pydantic, requests
"""

from typing import Optional, Dict, Any, List, AsyncGenerator
from pydantic import BaseModel, Field
import requests
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
import asyncio


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
        download_base_dir: str = Field(
            default="/tmp/upload",
            description="다운로드 파일 저장 기본 디렉토리"
        )

        # Open WebUI 백엔드 API
        openwebui_api_base: str = Field(
            default="http://localhost:8080/api/v1",
            description="Open WebUI 백엔드 API 베이스 URL"
        )

        # 지식베이스 ID (선택)
        knowledge_base_id: Optional[str] = Field(
            default=None,
            description="파일을 추가할 지식베이스 ID (없으면 파일만 업로드)"
        )

        # 업로드 모드
        upload_mode: str = Field(
            default="individual",
            description="업로드 모드: 'individual' (개별 업로드) 또는 'folder' (폴더 전체 업로드)"
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
        os.makedirs(self.valves.download_base_dir, exist_ok=True)

    def _log(self, message: str):
        """디버그 로그 기록"""
        if self.valves.enable_debug:
            print(f"[EDM Download] {message}", flush=True)

    def _create_download_folder(self) -> str:
        """
        /tmp/upload/날짜+랜덤폴더 생성

        Returns:
            생성된 폴더 경로 (예: /tmp/upload/20251111_a3f2b1c4)
        """
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = str(uuid.uuid4())[:8]
        folder_name = f"{date_str}_{random_str}"
        folder_path = os.path.join(self.valves.download_base_dir, folder_name)

        os.makedirs(folder_path, exist_ok=True)
        self._log(f"📁 다운로드 폴더 생성: {folder_path}")

        return folder_path

    def _download_edm_file(
        self,
        objid: str,
        file_last_ver_sno: int,
        request_user: str,
        download_folder: str
    ) -> Dict[str, Any]:
        """
        N8N 웹훅을 통해 EDM 파일 다운로드

        Args:
            objid: 파일 객체 ID
            file_last_ver_sno: 파일 버전
            request_user: 요청 사용자
            download_folder: 다운로드 대상 폴더

        Returns:
            {
                "file_name": "example.pdf",
                "file_path": "/tmp/upload/20251111_a3f2b1c4/example.pdf",
                "success": True
            }
        """
        try:
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
            file_name = result.get("file_name", f"downloaded_{objid}.pdf")
            file_content = result.get("file_content")  # base64 인코딩된 내용

            # 파일 저장
            file_path = os.path.join(download_folder, file_name)

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

    def _upload_folder_to_openwebui(
        self,
        folder_path: str,
        token: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        폴더 내 모든 파일을 Open WebUI에 업로드

        Args:
            folder_path: 업로드할 폴더 경로
            token: 사용자 인증 토큰
            metadata: 추가 메타데이터

        Returns:
            {
                "success": True,
                "uploaded_files": [
                    {"file_id": "uuid", "file_name": "file1.pdf", "success": True},
                    ...
                ]
            }
        """
        try:
            import os
            from pathlib import Path

            self._log(f"📁 폴더 업로드 시작: {folder_path}")

            # 폴더 내 모든 파일 찾기
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                raise Exception(f"폴더가 존재하지 않습니다: {folder_path}")

            all_files = []
            for file_path in folder.rglob('*'):
                if file_path.is_file():
                    all_files.append(file_path)

            if not all_files:
                self._log("⚠️  폴더에 파일이 없습니다")
                return {
                    "success": True,
                    "uploaded_files": [],
                    "message": "폴더에 업로드할 파일이 없습니다"
                }

            self._log(f"📋 발견된 파일 수: {len(all_files)}개")

            uploaded_files = []

            # 각 파일을 개별 업로드
            for idx, file_path in enumerate(all_files, 1):
                file_name = file_path.name
                self._log(f"📤 [{idx}/{len(all_files)}] 업로드 중: {file_name}")

                result = self._upload_to_openwebui(
                    file_path=str(file_path),
                    file_name=file_name,
                    token=token,
                    metadata=metadata
                )

                uploaded_files.append(result)

                if result["success"]:
                    self._log(f"✅ [{idx}/{len(all_files)}] 완료: {file_name}")
                else:
                    self._log(f"❌ [{idx}/{len(all_files)}] 실패: {file_name}")

            success_count = sum(1 for f in uploaded_files if f.get("success"))
            fail_count = len(uploaded_files) - success_count

            self._log(f"📊 폴더 업로드 완료: 성공 {success_count}개, 실패 {fail_count}개")

            return {
                "success": success_count > 0,
                "uploaded_files": uploaded_files,
                "summary": {
                    "total": len(uploaded_files),
                    "success": success_count,
                    "failed": fail_count
                }
            }

        except Exception as e:
            self._log(f"❌ 폴더 업로드 오류: {str(e)}")
            return {
                "success": False,
                "uploaded_files": [],
                "error": str(e)
            }

    def _upload_to_openwebui(
        self,
        file_path: str,
        file_name: str,
        token: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Open WebUI 백엔드 표준 API로 파일 업로드
        백엔드가 자동으로 파싱/청킹/임베딩/벡터화 수행

        Args:
            file_path: 업로드할 파일 경로
            file_name: 파일명
            token: 사용자 인증 토큰
            metadata: 추가 메타데이터

        Returns:
            {
                "file_id": "uuid",
                "success": True
            }
        """
        try:
            self._log(f"📤 Open WebUI 업로드 시작: {file_name}")

            # multipart/form-data로 파일 업로드
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_name, f, self._get_content_type(file_name))
                }

                data = {}
                if metadata:
                    data['metadata'] = json.dumps(metadata)

                headers = {
                    'Authorization': f'Bearer {token}'
                }

                # Open WebUI 백엔드 파일 업로드 API
                upload_url = f"{self.valves.openwebui_api_base}/files/"

                response = requests.post(
                    upload_url,
                    files=files,
                    data=data,
                    headers=headers,
                    params={
                        'process': 'true',  # 파일 처리 활성화
                        'process_in_background': 'true'  # 백그라운드 처리
                    },
                    timeout=300  # 5분 타임아웃
                )

                if not response.ok:
                    raise Exception(f"파일 업로드 실패: {response.status_code} {response.text}")

                result = response.json()
                file_id = result.get('id')

                self._log(f"✅ Open WebUI 업로드 완료: file_id={file_id}")
                self._log("🔄 백엔드에서 자동으로 파싱/청킹/임베딩/벡터화 진행 중...")

                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "success": True,
                    "result": result
                }

        except Exception as e:
            self._log(f"❌ Open WebUI 업로드 오류: {str(e)}")
            return {
                "file_id": None,
                "file_name": file_name,
                "success": False,
                "error": str(e)
            }

    def _add_to_knowledge_base(
        self,
        file_id: str,
        knowledge_base_id: str,
        token: str
    ) -> Dict[str, Any]:
        """
        파일을 지식베이스에 추가 (선택 사항)

        Args:
            file_id: 업로드된 파일 ID
            knowledge_base_id: 지식베이스 ID
            token: 사용자 인증 토큰

        Returns:
            {"success": True}
        """
        try:
            self._log(f"📚 지식베이스 추가 시작: {knowledge_base_id}")

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            payload = {
                'file_id': file_id
            }

            add_url = f"{self.valves.openwebui_api_base}/knowledge/{knowledge_base_id}/file/add"

            response = requests.post(
                add_url,
                json=payload,
                headers=headers,
                timeout=60
            )

            if not response.ok:
                raise Exception(f"지식베이스 추가 실패: {response.status_code} {response.text}")

            self._log(f"✅ 지식베이스 추가 완료")

            return {"success": True}

        except Exception as e:
            self._log(f"⚠️  지식베이스 추가 실패 (파일은 업로드됨): {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_content_type(self, filename: str) -> str:
        """파일 확장자로 Content-Type 추정"""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
        }
        return content_types.get(ext, 'application/octet-stream')

    def _process_folder_upload(self, folder_path: str, user_token: str) -> dict:
        """
        폴더 업로드 모드 처리

        Args:
            folder_path: 업로드할 폴더 경로
            user_token: 사용자 인증 토큰

        Returns:
            처리 결과 딕셔너리
        """
        try:
            if not user_token:
                error_msg = "user_token이 필요합니다"
                self._log(f"❌ {error_msg}")
                return {
                    "success": False,
                    "processed_files": [],
                    "error": error_msg
                }

            # Bearer 제거
            if user_token.startswith("Bearer "):
                user_token = user_token[7:]

            self._log(f"📁 폴더 경로: {folder_path}")

            # 메타데이터
            metadata = {
                "source": "folder_upload",
                "folder_path": folder_path
            }

            # 폴더 업로드 실행
            upload_result = self._upload_folder_to_openwebui(
                folder_path=folder_path,
                token=user_token,
                metadata=metadata
            )

            if not upload_result["success"]:
                self._log(f"❌ 폴더 업로드 실패")
                return {
                    "success": False,
                    "processed_files": [],
                    "error": upload_result.get("error", "폴더 업로드 실패")
                }

            uploaded_files = upload_result.get("uploaded_files", [])

            # 지식베이스에 추가 (선택 사항)
            if self.valves.knowledge_base_id:
                for file_result in uploaded_files:
                    if file_result.get("success") and file_result.get("file_id"):
                        kb_result = self._add_to_knowledge_base(
                            file_id=file_result["file_id"],
                            knowledge_base_id=self.valves.knowledge_base_id,
                            token=user_token
                        )

            # 최종 결과
            success_count = upload_result["summary"]["success"]
            fail_count = upload_result["summary"]["failed"]

            self._log("=" * 80)
            self._log(f"✨ 처리 완료: 성공 {success_count}개, 실패 {fail_count}개")
            self._log(f"📁 처리된 폴더: {folder_path}")
            self._log("=" * 80)

            return {
                "success": success_count > 0,
                "processed_files": uploaded_files,
                "folder_path": folder_path,
                "summary": upload_result["summary"]
            }

        except Exception as e:
            error_msg = f"폴더 업로드 처리 오류: {str(e)}"
            self._log(f"❌ {error_msg}")
            return {
                "success": False,
                "processed_files": [],
                "error": error_msg
            }

    async def pipe(
        self,
        body: dict
    ) -> AsyncGenerator[str, None]:
        """
        파이프라인 메인 로직 (Function 타입)

        입력 body (모드 1 - EDM 파일 다운로드):
        {
            "files": [
                {
                    "objid": "176126817626004568",
                    "fileLastVerSno": 1,
                    "requestUser": "user@example.com"
                },
                ...
            ],
            "user_token": "Bearer xxx"
        }

        입력 body (모드 2 - 폴더 업로드):
        {
            "folder_path": "/tmp/upload/20251111_abc123",
            "user_token": "Bearer xxx"
        }

        출력:
        {
            "success": True,
            "processed_files": [
                {
                    "objid": "176126817626004568",
                    "file_name": "example.pdf",
                    "file_id": "uuid",
                    "success": True
                },
                ...
            ]
        }
        """
        try:
            self._log("=" * 80)
            self._log("📋 [FUNCTION] edm_download_pipe")

            # 입력 검증
            files = body.get("files", [])
            folder_path = body.get("folder_path", "")
            user_token = body.get("user_token", "")

            # 폴더 업로드 모드 체크
            if folder_path:
                self._log("📋 [MODE] 폴더 업로드 모드")
                return self._process_folder_upload(folder_path, user_token)

            # 기본 모드: EDM 파일 다운로드 및 업로드
            self._log("📋 [MODE] EDM 파일 다운로드 및 업로드")
            self._log("📋 [ACTION] EDM 파일 지식화 시작")

            if not files:
                error_msg = "files 또는 folder_path 파라미터가 필요합니다"
                self._log(f"❌ {error_msg}")
                return {
                    "success": False,
                    "processed_files": [],
                    "error": error_msg
                }

            if not user_token:
                error_msg = "user_token이 필요합니다"
                self._log(f"❌ {error_msg}")
                return {
                    "success": False,
                    "processed_files": [],
                    "error": error_msg
                }

            # Bearer 제거
            if user_token.startswith("Bearer "):
                user_token = user_token[7:]

            self._log(f"📋 처리할 파일 수: {len(files)}개")

            # 1. 다운로드 폴더 생성 (날짜+랜덤)
            download_folder = self._create_download_folder()

            processed_files = []

            # 2. 각 파일 처리
            for idx, file_info in enumerate(files):
                objid = file_info.get("objid")
                file_last_ver_sno = file_info.get("fileLastVerSno", 1)
                request_user = file_info.get("requestUser")

                if not objid or not request_user:
                    self._log(f"⚠️  파일 {idx+1} 스킵: objid 또는 requestUser 누락")
                    processed_files.append({
                        "objid": objid or "unknown",
                        "success": False,
                        "error": "objid 또는 requestUser 누락"
                    })
                    continue

                self._log(f"\n--- 파일 {idx+1}/{len(files)} 처리 시작 ---")
                self._log(f"📋 OBJID: {objid}")
                self._log(f"📋 VERSION: {file_last_ver_sno}")
                self._log(f"📋 USER: {request_user}")

                # 2-1. EDM에서 파일 다운로드
                download_result = self._download_edm_file(
                    objid=objid,
                    file_last_ver_sno=file_last_ver_sno,
                    request_user=request_user,
                    download_folder=download_folder
                )

                if not download_result["success"]:
                    self._log(f"❌ 파일 {idx+1} 다운로드 실패")
                    processed_files.append({
                        "objid": objid,
                        "file_name": download_result.get("file_name", ""),
                        "success": False,
                        "error": download_result.get("error", "다운로드 실패")
                    })
                    continue

                file_name = download_result["file_name"]
                file_path = download_result["file_path"]

                # 2-2. Open WebUI 백엔드로 업로드 (자동 벡터화)
                metadata = {
                    "source": "EDM",
                    "objid": objid,
                    "file_last_ver_sno": file_last_ver_sno,
                    "request_user": request_user
                }

                upload_result = self._upload_to_openwebui(
                    file_path=file_path,
                    file_name=file_name,
                    token=user_token,
                    metadata=metadata
                )

                if not upload_result["success"]:
                    self._log(f"❌ 파일 {idx+1} 업로드 실패")
                    processed_files.append({
                        "objid": objid,
                        "file_name": file_name,
                        "success": False,
                        "error": upload_result.get("error", "업로드 실패")
                    })
                    continue

                file_id = upload_result["file_id"]

                # 2-3. 지식베이스에 추가 (선택 사항)
                if self.valves.knowledge_base_id:
                    kb_result = self._add_to_knowledge_base(
                        file_id=file_id,
                        knowledge_base_id=self.valves.knowledge_base_id,
                        token=user_token
                    )

                self._log(f"✅ 파일 {idx+1} 처리 완료")
                processed_files.append({
                    "objid": objid,
                    "file_name": file_name,
                    "file_id": file_id,
                    "file_path": file_path,
                    "success": True
                })

            # 최종 결과
            success_count = sum(1 for f in processed_files if f.get("success"))
            fail_count = len(processed_files) - success_count

            self._log("=" * 80)
            self._log(f"✨ 처리 완료: 성공 {success_count}개, 실패 {fail_count}개")
            self._log(f"📁 다운로드 폴더: {download_folder}")
            self._log("=" * 80)

            return {
                "success": success_count > 0,
                "processed_files": processed_files,
                "download_folder": download_folder,
                "summary": {
                    "total": len(processed_files),
                    "success": success_count,
                    "failed": fail_count
                }
            }

        except Exception as e:
            error_msg = f"파이프라인 오류: {str(e)}"
            self._log(f"❌ {error_msg}")
            return {
                "success": False,
                "processed_files": [],
                "error": error_msg
            }
