"""
title: EDM Download Pipeline
author: open-webui
date: 2025-11-01
version: 1.0
license: MIT
description: EDM 문서 다운로드 파이프라인 (파일 다운로드 및 메타데이터 반환)
requirements: pydantic, requests
"""

from typing import List, Union, Generator, Iterator, Optional, Dict, Any
from pydantic import BaseModel, Field
import requests
import json
import os
import tempfile
import uuid
from pathlib import Path


class Pipeline:
    class Valves(BaseModel):
        """파이프라인 설정값"""
        pipelines: List[str] = []
        priority: int = 0

        # EDM 서버 설정
        edm_server_url: str = Field(
            default=os.getenv("EDM_SERVER_URL", "http://169.254.1.2:8080"),
            description="EDM 서버 URL"
        )
        edm_download_endpoint: str = Field(
            default="/api/download",
            description="EDM 다운로드 API 엔드포인트"
        )

        # 다운로드 설정
        download_dir: str = Field(
            default="/tmp/edm_downloads",
            description="다운로드 파일 저장 디렉토리"
        )
        max_file_size_mb: int = Field(
            default=100,
            description="최대 파일 크기 (MB)"
        )
        download_timeout: int = Field(
            default=60,
            description="다운로드 타임아웃 (초)"
        )

        enable_debug: bool = Field(
            default=True,
            description="디버그 로그 활성화"
        )

    def __init__(self):
        self.type = "pipe"  # pipe 타입
        self.id = "edm_download_pipe"
        self.name = "EDM Download Pipeline"
        self.valves = self.Valves()
        self.debug_log = []

        # 다운로드 디렉토리 생성
        os.makedirs(self.valves.download_dir, exist_ok=True)

    def _log(self, message: str):
        """디버그 로그 기록"""
        if self.valves.enable_debug:
            self.debug_log.append(message)
            print(f"[EDM Download] {message}")

    def _download_file(
        self,
        objid: str,
        objt_nm: str,
        workspace_nm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        EDM 서버에서 파일 다운로드

        Args:
            objid: 파일 객체 ID
            objt_nm: 파일명
            workspace_nm: 워크스페이스명 (옵션)

        Returns:
            다운로드 결과 딕셔너리 (fileName, filePath 포함)
        """
        try:
            # 다운로드 URL 구성
            url = f"{self.valves.edm_server_url}{self.valves.edm_download_endpoint}"
            self._log(f"다운로드 URL: {url}")

            # 요청 파라미터
            params = {
                "objid": objid,
                "workspace": workspace_nm
            }

            self._log(f"다운로드 요청: {params}")

            # EDM 서버에 다운로드 요청
            response = requests.get(
                url,
                params=params,
                stream=True,
                timeout=self.valves.download_timeout
            )

            if not response.ok:
                raise Exception(f"다운로드 실패: {response.status_code} {response.text}")

            # 파일 저장 경로 생성
            file_extension = Path(objt_nm).suffix or ".bin"
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(self.valves.download_dir, unique_filename)

            # 파일 저장
            total_size = 0
            max_size = self.valves.max_file_size_mb * 1024 * 1024

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        total_size += len(chunk)
                        if total_size > max_size:
                            # 파일 크기 초과
                            os.remove(file_path)
                            raise Exception(f"파일 크기 초과: {total_size / (1024*1024):.2f}MB > {self.valves.max_file_size_mb}MB")
                        f.write(chunk)

            self._log(f"파일 저장 완료: {file_path} ({total_size / 1024:.2f}KB)")

            # 결과 반환
            return {
                "fileName": objt_nm,
                "filePath": file_path,
                "fileSize": total_size,
                "objid": objid,
                "workspaceNm": workspace_nm,
                "status": "success"
            }

        except Exception as e:
            self._log(f"파일 다운로드 오류: {str(e)}")
            raise

    def pipe(
        self,
        body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        파이프라인 메인 로직

        Args:
            body: 요청 본문 (objid, objtNm, workspaceNm 포함)

        Returns:
            다운로드 결과 (fileName, filePath 포함)
        """
        try:
            self._log("=" * 50)
            self._log("EDM Download 파이프라인 시작")

            # 입력 파라미터 추출
            objid = body.get("objid")
            objt_nm = body.get("objtNm")
            workspace_nm = body.get("workspaceNm")

            if not objid:
                raise ValueError("파일 객체 ID가 없습니다")
            if not objt_nm:
                raise ValueError("파일명이 없습니다")

            self._log(f"파일 객체 ID: {objid}")
            self._log(f"파일명: {objt_nm}")
            self._log(f"워크스페이스: {workspace_nm}")

            # 파일 다운로드
            result = self._download_file(
                objid=objid,
                objt_nm=objt_nm,
                workspace_nm=workspace_nm
            )

            self._log("EDM Download 파이프라인 완료")
            self._log("=" * 50)

            return result

        except Exception as e:
            error_msg = f"EDM Download 파이프라인 오류: {str(e)}"
            self._log(error_msg)

            return {
                "fileName": body.get("objtNm", ""),
                "filePath": "",
                "fileSize": 0,
                "objid": body.get("objid", ""),
                "workspaceNm": body.get("workspaceNm", ""),
                "status": "error",
                "error": str(e)
            }


# Pipeline 인스턴스 생성 (Open WebUI에서 자동으로 로드)
def get_pipeline():
    return Pipeline()
