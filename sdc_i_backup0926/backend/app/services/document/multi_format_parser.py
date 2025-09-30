"""
Multi-Format Document Parser
Excel, PowerPoint, PDF, Word 문서를 위한 종합적인 파서 시스템
한글 전용 센텐스 기반 청킹 로직과 통합
"""

import os
import time
import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# 라이브러리 가용성 확인
try:
    from docx import Document
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False
    logger.warning("⚠️ [PARSER] python-docx not available")

try:
    from pptx import Presentation
    PYTHON_PPTX_AVAILABLE = True
except ImportError:
    PYTHON_PPTX_AVAILABLE = False
    logger.warning("⚠️ [PARSER] python-pptx not available")

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger.warning("⚠️ [PARSER] openpyxl not available")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("⚠️ [PARSER] PyPDF2 not available")

# Korean chunker integration
try:
    from ...services.korean_chunker import get_korean_chunker
    KOREAN_CHUNKER_AVAILABLE = True
except ImportError:
    try:
        from backend.services.korean_chunker import get_korean_chunker
        KOREAN_CHUNKER_AVAILABLE = True
    except ImportError:
        KOREAN_CHUNKER_AVAILABLE = False
        logger.warning("⚠️ [PARSER] Korean chunker not available")

@dataclass
class ParsingResult:
    """파싱 결과"""
    success: bool
    extracted_text: str
    method_used: str
    metadata: Dict[str, Any]
    processing_time: float
    char_count: int
    chunks: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    fallback_attempts: List[str] = None

class MultiFormatDocumentParser:
    """다중 포맷 문서 파서"""

    def __init__(self):
        self.supported_formats = ['.docx', '.doc', '.pdf', '.pptx', '.ppt', '.xlsx', '.xls']

    async def parse_document(self, file_path: str, filename: str) -> ParsingResult:
        """문서 파싱 메인 함수"""
        start_time = time.time()

        try:
            file_extension = Path(filename).suffix.lower()
            logger.info(f"🔍 [PARSER] Starting parsing for {filename} ({file_extension})")

            if file_extension in ['.docx', '.doc']:
                result = await self._parse_word_document(file_path, filename)
            elif file_extension in ['.xlsx', '.xls']:
                result = await self._parse_excel_document(file_path, filename)
            elif file_extension in ['.pptx', '.ppt']:
                result = await self._parse_powerpoint_document(file_path, filename)
            elif file_extension == '.pdf':
                result = await self._parse_pdf_document(file_path, filename)
            else:
                result = ParsingResult(
                    success=False,
                    extracted_text="",
                    method_used="none",
                    metadata={"format": file_extension, "error": "Unsupported format"},
                    processing_time=0,
                    char_count=0,
                    fallback_attempts=["unsupported_format"]
                )

            # 처리 시간 업데이트
            result.processing_time = time.time() - start_time

            # 성공한 경우 한글 청킹 적용
            if result.success and result.extracted_text.strip() and KOREAN_CHUNKER_AVAILABLE:
                try:
                    logger.info(f"🔧 [PARSER] Applying Korean chunking to {filename}")
                    chunker = get_korean_chunker()
                    chunks = chunker.chunk_document(
                        result.extracted_text,
                        metadata={
                            "filename": filename,
                            "format": file_extension,
                            "parsing_method": result.method_used
                        }
                    )

                    result.chunks = chunks
                    result.metadata["chunks_count"] = len(chunks)
                    result.metadata["korean_chunking"] = True

                    logger.info(f"✅ [PARSER] Korean chunking applied: {len(chunks)} chunks created")

                except Exception as e:
                    logger.warning(f"⚠️ [PARSER] Korean chunking failed: {e}")
                    result.metadata["korean_chunking"] = False
                    result.metadata["chunking_error"] = str(e)

            return result

        except Exception as e:
            logger.error(f"❌ [PARSER] Document parsing failed: {e}")
            return ParsingResult(
                success=False,
                extracted_text="",
                method_used="none",
                metadata={"error": str(e)},
                processing_time=time.time() - start_time,
                char_count=0,
                fallback_attempts=["parsing_error"]
            )

    async def _parse_word_document(self, file_path: str, filename: str) -> ParsingResult:
        """Word 문서 파싱"""
        fallback_attempts = []

        if not PYTHON_DOCX_AVAILABLE:
            return ParsingResult(
                success=False,
                extracted_text="",
                method_used="none",
                metadata={"format": "docx", "error": "python-docx not available"},
                processing_time=0,
                char_count=0,
                fallback_attempts=["python_docx_unavailable"]
            )

        try:
            fallback_attempts.append("python_docx")
            doc = Document(file_path)
            extracted_text = ""

            # 문서 정보 수집
            doc_info = {
                "paragraphs_count": len(doc.paragraphs),
                "tables_count": len(doc.tables),
                "sections_count": len(doc.sections)
            }

            # 단락 텍스트 추출
            for para in doc.paragraphs:
                if para.text.strip():
                    extracted_text += para.text.strip() + "\n"

            # 표 데이터 추출
            for table_idx, table in enumerate(doc.tables):
                extracted_text += f"\n=== 표 {table_idx + 1} ===\n"
                for row_idx, row in enumerate(table.rows):
                    row_data = [cell.text.strip() for cell in row.cells]
                    if any(row_data):
                        if row_idx == 0:
                            extracted_text += "헤더: " + " | ".join(row_data) + "\n"
                        else:
                            extracted_text += f"행{row_idx}: " + " | ".join(row_data) + "\n"

            # 머리글/바닥글 추출
            for section in doc.sections:
                if section.header.paragraphs:
                    header_text = " ".join([p.text for p in section.header.paragraphs if p.text.strip()])
                    if header_text:
                        extracted_text += f"\n머리글: {header_text}\n"

                if section.footer.paragraphs:
                    footer_text = " ".join([p.text for p in section.footer.paragraphs if p.text.strip()])
                    if footer_text:
                        extracted_text += f"\n바닥글: {footer_text}\n"

            return ParsingResult(
                success=True,
                extracted_text=extracted_text.strip(),
                method_used="python_docx",
                metadata={
                    "format": "docx",
                    "method": "python_docx",
                    **doc_info
                },
                processing_time=0,
                char_count=len(extracted_text),
                fallback_attempts=fallback_attempts
            )

        except Exception as e:
            logger.error(f"❌ [PARSER] Word parsing failed: {e}")
            return ParsingResult(
                success=False,
                extracted_text="",
                method_used="none",
                metadata={"format": "docx", "error": str(e)},
                processing_time=0,
                char_count=0,
                fallback_attempts=fallback_attempts
            )

    async def _parse_excel_document(self, file_path: str, filename: str) -> ParsingResult:
        """Excel 문서 파싱"""
        fallback_attempts = []

        # 방법 1: openpyxl 사용
        if OPENPYXL_AVAILABLE:
            try:
                fallback_attempts.append("openpyxl")
                workbook = openpyxl.load_workbook(file_path, data_only=True)
                extracted_text = ""
                sheets_info = []

                for sheet_name in workbook.sheetnames:
                    sheet = workbook[sheet_name]
                    sheet_text = f"\n=== 시트: {sheet_name} ===\n"

                    rows_data = []
                    for row in sheet.iter_rows(values_only=True):
                        row_data = [str(cell) if cell is not None else "" for cell in row]
                        if any(cell.strip() for cell in row_data if cell):
                            rows_data.append(row_data)

                    for i, row in enumerate(rows_data):
                        if i == 0:
                            sheet_text += "헤더: " + " | ".join(row) + "\n"
                        else:
                            sheet_text += f"행{i}: " + " | ".join(row) + "\n"

                    extracted_text += sheet_text
                    sheets_info.append({
                        "name": sheet_name,
                        "rows": len(rows_data),
                        "has_data": len(rows_data) > 0
                    })

                if extracted_text.strip():
                    return ParsingResult(
                        success=True,
                        extracted_text=extracted_text.strip(),
                        method_used="openpyxl",
                        metadata={
                            "format": "xlsx",
                            "method": "openpyxl",
                            "sheets": sheets_info
                        },
                        processing_time=0,
                        char_count=len(extracted_text),
                        fallback_attempts=fallback_attempts
                    )

            except Exception as e:
                logger.warning(f"⚠️ [PARSER] Excel openpyxl failed: {e}")

        # 방법 2: pandas 사용 (fallback)
        try:
            fallback_attempts.append("pandas")
            excel_data = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            extracted_text = ""

            for sheet_name, df in excel_data.items():
                extracted_text += f"\n=== 시트: {sheet_name} ===\n"

                if not df.empty:
                    # 컬럼명 추가
                    extracted_text += "컬럼: " + " | ".join(df.columns.astype(str)) + "\n"

                    # 데이터 행 추가 (최대 100행까지)
                    for idx, row in df.head(100).iterrows():
                        row_text = " | ".join([str(val) if pd.notna(val) else "" for val in row.values])
                        if row_text.strip():
                            extracted_text += f"행{idx+1}: {row_text}\n"
                else:
                    extracted_text += "빈 시트\n"

            return ParsingResult(
                success=True,
                extracted_text=extracted_text.strip(),
                method_used="pandas",
                metadata={
                    "format": "xlsx",
                    "method": "pandas",
                    "sheets": list(excel_data.keys())
                },
                processing_time=0,
                char_count=len(extracted_text),
                fallback_attempts=fallback_attempts
            )

        except Exception as e:
            logger.error(f"❌ [PARSER] Excel pandas failed: {e}")
            return ParsingResult(
                success=False,
                extracted_text="",
                method_used="none",
                metadata={"format": "xlsx", "error": "All Excel methods failed"},
                processing_time=0,
                char_count=0,
                fallback_attempts=fallback_attempts
            )

    async def _parse_powerpoint_document(self, file_path: str, filename: str) -> ParsingResult:
        """PowerPoint 문서 파싱"""
        fallback_attempts = []

        if not PYTHON_PPTX_AVAILABLE:
            return ParsingResult(
                success=False,
                extracted_text="",
                method_used="none",
                metadata={"format": "pptx", "error": "python-pptx not available"},
                processing_time=0,
                char_count=0,
                fallback_attempts=["python_pptx_unavailable"]
            )

        try:
            fallback_attempts.append("python_pptx")
            presentation = Presentation(file_path)
            extracted_text = ""
            slides_info = []

            for i, slide in enumerate(presentation.slides, 1):
                slide_text = f"\n=== 슬라이드 {i} ===\n"
                slide_content = []

                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        # 텍스트 상자 유형 구분
                        if hasattr(shape, 'placeholder_format'):
                            if shape.placeholder_format.type == 1:  # 제목
                                slide_text += f"제목: {shape.text.strip()}\n"
                            elif shape.placeholder_format.type == 7:  # 내용
                                slide_text += f"내용: {shape.text.strip()}\n"
                            else:
                                slide_text += f"텍스트: {shape.text.strip()}\n"
                        else:
                            slide_text += f"텍스트: {shape.text.strip()}\n"

                        slide_content.append(shape.text.strip())

                    # 표 데이터 추출
                    if shape.has_table:
                        table = shape.table
                        slide_text += "표 데이터:\n"
                        for row_idx, row in enumerate(table.rows):
                            row_data = [cell.text.strip() for cell in row.cells]
                            if any(row_data):
                                if row_idx == 0:
                                    slide_text += "  헤더: " + " | ".join(row_data) + "\n"
                                else:
                                    slide_text += f"  행{row_idx}: " + " | ".join(row_data) + "\n"

                    # 차트나 이미지가 있는 경우 표시
                    if shape.shape_type == 3:  # 이미지
                        slide_text += "[이미지 포함]\n"
                    elif shape.shape_type == 24:  # 차트
                        slide_text += "[차트 포함]\n"

                extracted_text += slide_text
                slides_info.append({
                    "slide_number": i,
                    "content_length": len(" ".join(slide_content)),
                    "has_content": len(slide_content) > 0
                })

            return ParsingResult(
                success=True,
                extracted_text=extracted_text.strip(),
                method_used="python_pptx",
                metadata={
                    "format": "pptx",
                    "method": "python_pptx",
                    "slides_count": len(presentation.slides),
                    "slides_info": slides_info
                },
                processing_time=0,
                char_count=len(extracted_text),
                fallback_attempts=fallback_attempts
            )

        except Exception as e:
            logger.error(f"❌ [PARSER] PowerPoint parsing failed: {e}")
            return ParsingResult(
                success=False,
                extracted_text="",
                method_used="none",
                metadata={"format": "pptx", "error": str(e)},
                processing_time=0,
                char_count=0,
                fallback_attempts=fallback_attempts
            )

    async def _parse_pdf_document(self, file_path: str, filename: str) -> ParsingResult:
        """PDF 문서 파싱"""
        fallback_attempts = []

        if not PYPDF2_AVAILABLE:
            return ParsingResult(
                success=False,
                extracted_text="",
                method_used="none",
                metadata={"format": "pdf", "error": "PyPDF2 not available"},
                processing_time=0,
                char_count=0,
                fallback_attempts=["pypdf2_unavailable"]
            )

        try:
            fallback_attempts.append("pypdf2")

            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                extracted_text = ""
                pages_info = []

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            extracted_text += f"\n=== 페이지 {page_num} ===\n"
                            extracted_text += page_text.strip() + "\n"

                            pages_info.append({
                                "page_number": page_num,
                                "char_count": len(page_text),
                                "has_content": bool(page_text.strip())
                            })
                        else:
                            pages_info.append({
                                "page_number": page_num,
                                "char_count": 0,
                                "has_content": False
                            })

                    except Exception as e:
                        logger.warning(f"⚠️ [PARSER] PDF page {page_num} extraction failed: {e}")
                        pages_info.append({
                            "page_number": page_num,
                            "char_count": 0,
                            "has_content": False,
                            "error": str(e)
                        })

                return ParsingResult(
                    success=True,
                    extracted_text=extracted_text.strip(),
                    method_used="pypdf2",
                    metadata={
                        "format": "pdf",
                        "method": "pypdf2",
                        "pages_count": len(pdf_reader.pages),
                        "pages_info": pages_info
                    },
                    processing_time=0,
                    char_count=len(extracted_text),
                    fallback_attempts=fallback_attempts
                )

        except Exception as e:
            logger.error(f"❌ [PARSER] PDF parsing failed: {e}")
            return ParsingResult(
                success=False,
                extracted_text="",
                method_used="none",
                metadata={"format": "pdf", "error": str(e)},
                processing_time=0,
                char_count=0,
                fallback_attempts=fallback_attempts
            )

# 싱글톤 인스턴스
_parser_instance = None

def get_multi_format_parser() -> MultiFormatDocumentParser:
    """다중 포맷 파서 인스턴스 반환"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = MultiFormatDocumentParser()
    return _parser_instance

# 편의 함수
async def parse_document(file_path: str, filename: str) -> ParsingResult:
    """문서 파싱 편의 함수"""
    parser = get_multi_format_parser()
    return await parser.parse_document(file_path, filename)

if __name__ == "__main__":
    import asyncio

    async def test_parser():
        parser = MultiFormatDocumentParser()

        # 테스트 파일 경로 (실제 파일이 있는 경우)
        test_files = [
            ("test.docx", "Word document"),
            ("test.xlsx", "Excel document"),
            ("test.pptx", "PowerPoint document"),
            ("test.pdf", "PDF document")
        ]

        for filename, description in test_files:
            if os.path.exists(filename):
                print(f"\n🔍 Testing {description}: {filename}")
                result = await parser.parse_document(filename, filename)
                print(f"Success: {result.success}")
                print(f"Method: {result.method_used}")
                print(f"Text length: {result.char_count}")
                if result.chunks:
                    print(f"Chunks: {len(result.chunks)}")
                if result.error_message:
                    print(f"Error: {result.error_message}")

    # asyncio.run(test_parser())