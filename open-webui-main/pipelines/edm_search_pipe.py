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


class Pipe:
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

    async def pipe(
        self, body: dict, __event_emitter__=None
    ) -> Union[str, Generator, Iterator, dict]:
        """
        파이프라인 메인 로직 (Open WebUI 표준 시그니처)

        Args:
            body: 요청 본문 (model, messages 등 포함)
            __event_emitter__: 이벤트 발송 함수 (프론트엔드 통신용)

        Returns:
            검색 결과 또는 body
        """
        try:
            # body에서 필요한 값 추출
            messages = body.get("messages", [])
            user_message = messages[-1].get("content", "") if messages else ""
            model_id = body.get("model", "")

            self._log("=" * 80)
            self._log("📋 [PIPELINE] edm_search_pipe")
            self._log("📋 [ACTION] EDM Search 파이프라인 시작")
            self._log(f"📋 [USER_MESSAGE] {user_message}")
            self._log(f"📋 [MODEL_ID] {model_id}")

            # 입력 파라미터 추출
            query = user_message
            categories = body.get("categories", self.valves.default_categories)
            chat_id = body.get("chat_id")
            user_id = body.get("user", {}).get("id") if isinstance(body.get("user"), dict) else None

            if not query:
                raise ValueError("검색 쿼리가 없습니다")

            self._log(f"📋 [QUERY] {query}")
            self._log(f"📋 [CATEGORIES] {categories}")
            self._log(f"📋 [CHAT_ID] {chat_id}")
            self._log(f"📋 [USER_ID] {user_id}")

            # 📥 직접 uploads 폴더에서 파일 목록 가져오기
            self._log("=" * 80)
            self._log("📥 [edm_search_pipe.py] 직접 파일 시스템에서 파일 검색")

            try:
                import glob
                uploads_dir = "/app/backend/data/uploads"

                # 파일 검색 패턴
                search_patterns = ["*.pdf", "*.docx", "*.xlsx", "*.txt", "*.doc", "*.pptx", "*.csv"]
                all_files = []

                for pattern in search_patterns:
                    files = glob.glob(os.path.join(uploads_dir, f"**/{pattern}"), recursive=True)
                    all_files.extend(files)

                self._log(f"📁 전체 파일 수: {len(all_files)}개")

                # 파일 메타데이터 생성
                documents = []
                for idx, file_path in enumerate(sorted(all_files), 1):
                    if not os.path.isfile(file_path):
                        continue

                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size
                    file_name = os.path.basename(file_path)

                    # UUID 추출
                    parts = file_name.split('_')
                    objid = parts[0] if parts else str(idx)
                    actual_name = '_'.join(parts[1:]) if len(parts) > 1 else file_name

                    # 검색어 필터링
                    if query and query.lower() not in actual_name.lower():
                        continue

                    file_ext = os.path.splitext(file_name)[1].replace('.', '')

                    documents.append({
                        "doc_id": f"DOC-{idx:05d}",
                        "title": actual_name,
                        "score": 0.95,
                        "objid": objid,  # 실제 파일 UUID
                        "objtNm": actual_name,
                        "fileName": actual_name,
                        "FILE_NAME": actual_name,
                        "fileExtNm": file_ext,
                        "workspaceNm": "기술문서팀",
                        "maxObjtSharePolicyId": "public",
                        "objtSize": f"{file_size / 1024:.1f}KB",
                        "filesize": file_size,
                        "regDt": "2025-01-15",
                        "filePath": file_path,  # 실제 파일 경로
                        "contents": []
                    })

                    if len(documents) >= self.valves.max_results:
                        break

                n8n_result = {
                    "documents": documents,
                    "total_count": len(documents)
                }
                self._log(f"✅ 파일 시스템에서 {len(documents)}개 파일 로드 완료")

            except Exception as e:
                self._log(f"⚠️ 파일 검색 실패: {str(e)}")
                n8n_result = {
                    "documents": [],
                    "total_count": 0
                }

            # N8N 웹훅 호출 (필요시 활성화)
            # n8n_result = self._call_n8n_webhook(
            #     query=query,
            #     categories=categories,
            #     chat_id=chat_id,
            #     user_id=user_id
            # )

            # 결과 포맷 변환
            documents = n8n_result.get("documents", [])
            total_count = n8n_result.get("total_count", len(documents))

            # 📄 [edm_search_pipe.py:157] 파일 리스트 상세 로그
            self._log("=" * 80)
            self._log(f"📄 [edm_search_pipe.py:157] N8N에서 파일 리스트 수신 완료")
            self._log(f"📄 [FILE_LIST_COUNT] {total_count}개 파일")
            for idx, doc in enumerate(documents, 1):
                self._log(f"📄 [FILE_{idx}] objid={doc.get('objid')}, name={doc.get('objtNm')}, workspace={doc.get('workspaceNm')}, permission={doc.get('maxObjtSharePolicyId')}")
            self._log("=" * 80)

            # 📤 파일 리스트를 프론트엔드로 전송 (팝업 표시용)
            if __event_emitter__ and documents:
                self._log("=" * 80)
                self._log(f"📤 [edm_search_pipe.py:170] __event_emitter__로 파일 리스트 전송")
                self._log(f"📤 [EVENT_TYPE] openEdmFileList")
                self._log(f"📤 [DESTINATION] Chat.svelte (message.info.edmFileList)")
                self._log(f"📤 [FILES_COUNT] {len(documents)}개 파일 전송")
                self._log("=" * 80)

                await __event_emitter__({
                    "type": "event",
                    "event": {
                        "type": "openEdmFileList",
                        "detail": {"files": documents}
                    }
                })

            self._log(f"📊 검색 결과: {total_count}개 문서")
            self._log("=" * 80)

            # 응답 메시지 생성 (파일 리스트를 HTML 주석으로 포함)
            import json
            files_json = json.dumps(documents, ensure_ascii=False)
            response_message = f"<!--EDM_FILES:{files_json}-->\nEDM 에서 관련 문서 {total_count}건을 찾았습니다. 상세 내용은 EDM 검색결과에서 확인 가능합니다."

            self._log(f"🔵 [YIELD] 응답 메시지 전송: {response_message}")
            yield response_message
            self._log(f"✅ [YIELD] 응답 메시지 전송 완료")

            self._log("✅ EDM Search 파이프라인 완료")
            self._log("=" * 80)

        except Exception as e:
            error_msg = f"❌ EDM Search 파이프라인 오류: {str(e)}"
            self._log(error_msg)
            self._log("=" * 80)

            # 오류 메시지 yield
            yield error_msg


