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

            # 📥 [edm_search_pipe.py:145] Mock 데이터 사용 (테스트 모드)
            self._log("=" * 80)
            self._log("📥 [edm_search_pipe.py:145] Mock 데이터 사용 (테스트 모드)")

            # Mock 데이터
            n8n_result = {
                "documents": [
                    {
                        "doc_id": "DOC-2025-001",
                        "title": "삼성디스플레이 회사생활가이드 - 제1장",
                        "score": 0.95,
                        "objid": "edm-obj-001",
                        "objtNm": "회사생활가이드_제1장.pdf",
                        "workspaceNm": "인사총무",
                        "maxObjtSharePolicyId": "public",
                        "objtSize": "2.5MB",
                        "regDt": "2025-01-15",
                        "contents": [
                            "1.1 입사 절차 및 준비사항",
                            "1.2 첫 출근일 안내",
                            "1.3 회사 시설 이용 방법",
                            "1.4 복리후생 제도 소개",
                            "1.5 인사 규정 개요",
                            "1.6 급여 및 복지 혜택",
                            "1.7 근무 시간 및 휴가 제도",
                            "1.8 교육 훈련 프로그램",
                            "1.9 경력 개발 지원",
                            "1.10 회사 문화 및 가치"
                        ]
                    },
                    {
                        "doc_id": "DOC-2025-002",
                        "title": "디스플레이 용어사전 - 기술편",
                        "score": 0.88,
                        "objid": "edm-obj-002",
                        "objtNm": "디스플레이_용어사전_기술편.docx",
                        "workspaceNm": "기술개발",
                        "maxObjtSharePolicyId": "internal",
                        "objtSize": "1.8MB",
                        "regDt": "2025-01-10",
                        "contents": [
                            "OLED (Organic Light Emitting Diode) - 유기발광다이오드",
                            "TFT (Thin Film Transistor) - 박막트랜지스터",
                            "LCD (Liquid Crystal Display) - 액정디스플레이",
                            "AMOLED (Active Matrix OLED) - 능동형 유기발광다이오드",
                            "백라이트 (Backlight) - 액정 패널 뒤에서 빛을 제공하는 광원",
                            "해상도 (Resolution) - 화면에 표시되는 픽셀의 수",
                            "리프레시율 (Refresh Rate) - 화면이 1초에 갱신되는 횟수",
                            "명암비 (Contrast Ratio) - 가장 밝은 부분과 어두운 부분의 밝기 차이",
                            "색재현율 (Color Gamut) - 디스플레이가 표현할 수 있는 색상 범위",
                            "응답속도 (Response Time) - 픽셀이 색을 변경하는데 걸리는 시간"
                        ]
                    }
                ],
                "total_count": 2
            }

            # N8N 웹훅 호출 (Mock 사용 시 주석 처리)
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


