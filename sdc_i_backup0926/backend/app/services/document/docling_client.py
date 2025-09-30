"""
Docling Client Service - Document Processing Integration

이 모듈은 Docling 서비스와의 HTTP 클라이언트 통신을 담당합니다.
PDF, PPT, XLSX, DOC 등의 구조화된 문서를 텍스트로 변환합니다.
"""

import os
import aiohttp
import asyncio
from typing import Dict, Any, Optional, Tuple
import tempfile
import logging

logger = logging.getLogger(__name__)

class DoclingClient:
    """Docling 서비스와의 HTTP 클라이언트"""
    
    def __init__(self):
        self.base_url = f"http://{os.getenv('DOCLING_HOST', 'localhost')}:{os.getenv('DOCLING_PORT', '5000')}"
        self.health_url = f"{self.base_url}/health"
        # 공식 API 형식 지원을 위한 다중 엔드포인트
        self.convert_url = f"{self.base_url}/v1/convert/file"  # 공식 API 우선
        self.ocr_url = f"{self.base_url}/ocr"  # 기존 API fallback
        self.serialize_url = f"{self.base_url}/serialize"  # 추가 엔드포인트
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5분 타임아웃
        
    async def health_check(self) -> bool:
        """Docling 서비스 헬스 체크"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.health_url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Docling health check failed: {e}")
            return False
    
    async def convert_document(self, file_content: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
        """
        문서를 Docling 서비스를 통해 텍스트로 변환
        새로운 API를 사용하여 다양한 형식 지원

        Args:
            file_content: 파일의 바이트 내용
            filename: 파일명 (확장자 포함)

        Returns:
            (성공여부, 결과데이터)
        """
        # 파일 확장자 확인
        file_ext = os.path.splitext(filename.lower())[1]

        # 지원되는 형식 확인 (Docling 서비스가 실제로 지원하는 형식만)
        supported_formats = ['.pdf', '.docx', '.pptx', '.xlsx']

        if file_ext not in supported_formats:
            return False, {
                'method': 'docling',
                'error': f"Unsupported file format: {file_ext}. Supported formats: {', '.join(supported_formats)}",
                'status': 'unsupported_format'
            }

        # 새로운 /v1/convert/source API 시도
        success, result = await self._try_convert_source_api(file_content, filename, file_ext)
        if success:
            return success, result

        # 기존 OCR API로 fallback (PDF만 가능)
        if file_ext == '.pdf':
            success, result = await self._try_ocr_api(file_content, filename)
            if success:
                return success, result

        return False, {
            'method': 'docling',
            'error': f"Failed to process {file_ext} file with Docling service",
            'status': 'processing_failed'
        }

    async def _try_convert_source_api(self, file_content: bytes, filename: str, file_ext: str) -> Tuple[bool, Dict[str, Any]]:
        """새로운 Docling Serve API 시도 (/v1/convert/file - multipart)"""
        try:
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()

                # 형식 매핑 (Docling 서비스가 실제로 지원하는 형식만)
                format_mapping = {
                    '.pdf': 'pdf',
                    '.docx': 'docx',
                    '.pptx': 'pptx',
                    '.xlsx': 'xlsx'
                }

                format_name = format_mapping.get(file_ext, 'pdf')

                # Multipart form data 준비
                data = aiohttp.FormData()
                data.add_field('files',
                             open(temp_file.name, 'rb'),
                             filename=filename,
                             content_type='application/octet-stream')

                # 옵션 추가
                data.add_field('from_formats', format_name)
                data.add_field('to_formats', 'md')
                data.add_field('do_ocr', 'true')
                data.add_field('force_ocr', 'false')
                data.add_field('abort_on_error', 'false')
                data.add_field('do_table_structure', 'true')
                data.add_field('include_images', 'false')

                convert_url = f"{self.base_url}/v1/convert/file"

                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(convert_url, data=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            os.unlink(temp_file.name)  # 임시 파일 삭제

                            # 응답에서 텍스트 콘텐츠 추출
                            content = ""
                            if isinstance(result, dict):
                                # 실제 Docling API 응답 구조 처리
                                if 'document' in result and result['document']:
                                    doc = result['document']
                                    content = doc.get('md_content', doc.get('markdown', doc.get('text', doc.get('content', ''))))
                                elif 'documents' in result and result['documents']:
                                    doc = result['documents'][0]
                                    content = doc.get('markdown', doc.get('text', doc.get('content', '')))
                                elif 'markdown' in result:
                                    content = result['markdown']
                                elif 'text' in result:
                                    content = result['text']
                                elif 'content' in result:
                                    content = result['content']

                            return True, {
                                'method': 'docling_multipart',
                                'content': content,
                                'metadata': result.get('metadata', {}),
                                'status': 'success'
                            }
                        else:
                            os.unlink(temp_file.name)  # 임시 파일 삭제
                            logger.debug(f"Convert Multipart API failed with status {response.status}")
                            return False, {}

        except Exception as e:
            logger.debug(f"Convert Multipart API failed: {e}")
            return False, {}

    async def _try_official_api(self, file_content: bytes, filename: str, file_ext: str) -> Tuple[bool, Dict[str, Any]]:
        """공식 Docling Serve API 시도 (/v1/convert/file)"""
        try:
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()

                # 공식 API 형식 매개변수
                data = aiohttp.FormData()
                data.add_field('files',
                             open(temp_file.name, 'rb'),
                             filename=filename,
                             content_type='application/octet-stream')

                # 공식 API 매개변수 추가
                supported_formats = ['pdf', 'docx', 'pptx', 'html', 'image', 'asciidoc', 'md', 'xlsx']
                format_name = file_ext[1:]  # .pdf -> pdf

                if format_name in supported_formats:
                    data.add_field('from_formats', format_name)

                data.add_field('to_formats', 'md')  # markdown 출력
                data.add_field('do_ocr', 'true')
                data.add_field('force_ocr', 'false')
                data.add_field('abort_on_error', 'false')

                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(self.convert_url, data=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            os.unlink(temp_file.name)

                            # 공식 API 응답 형식 처리
                            content = ""
                            if 'documents' in result and result['documents']:
                                doc = result['documents'][0]
                                content = doc.get('markdown', doc.get('text', ''))

                            return True, {
                                'method': 'docling_official',
                                'content': content,
                                'metadata': result.get('metadata', {}),
                                'status': 'success'
                            }
                        else:
                            os.unlink(temp_file.name)
                            return False, {}

        except Exception as e:
            logger.debug(f"Official API failed: {e}")
            return False, {}

    async def _try_ocr_api(self, file_content: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
        """기존 OCR API 시도 (/ocr) - PDF 전용"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()

                data = aiohttp.FormData()
                data.add_field('file',
                             open(temp_file.name, 'rb'),
                             filename=filename,
                             content_type='application/pdf')

                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(self.ocr_url, data=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            os.unlink(temp_file.name)

                            return True, {
                                'method': 'docling_ocr',
                                'content': result.get('markdown', result.get('text', '')),
                                'metadata': result.get('metadata', {}),
                                'status': 'success'
                            }
                        else:
                            os.unlink(temp_file.name)
                            return False, {}

        except Exception as e:
            logger.debug(f"OCR API failed: {e}")
            return False, {}
    
    def is_supported_format(self, filename: str) -> bool:
        """지원되는 파일 형식인지 확인"""
        # Docling 서비스가 실제로 지원하는 형식만 포함
        supported_extensions = {'.pdf', '.docx', '.pptx', '.xlsx'}
        ext = os.path.splitext(filename.lower())[1]
        return ext in supported_extensions

# 전역 클라이언트 인스턴스
docling_client = DoclingClient()