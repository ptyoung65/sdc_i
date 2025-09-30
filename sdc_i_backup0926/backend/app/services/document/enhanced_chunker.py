"""
Enhanced Document Chunking System
두 가지 청킹 방법 지원:
1. 일반 청킹: Python 라이브러리 (python-docx, python-pptx, openpyxl, PyPDF2)
2. Docling 청킹: Docling 고급 파싱 기능
"""

import os
import io
import json
import uuid
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import logging

# 문서 처리 라이브러리
try:
    import docx
    from docx import Document as DocxDocument
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import _Cell, Table
    from docx.text.paragraph import Paragraph
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Docling 클라이언트
try:
    from .docling_client import DoclingClient
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# 고급 전처리기
try:
    from .advanced_preprocessor import get_advanced_preprocessor
    ADVANCED_PREPROCESSOR_AVAILABLE = True
except ImportError:
    ADVANCED_PREPROCESSOR_AVAILABLE = False

# 다중 포맷 파서
try:
    from .multi_format_parser import get_multi_format_parser
    MULTI_FORMAT_PARSER_AVAILABLE = True
except ImportError:
    MULTI_FORMAT_PARSER_AVAILABLE = False

# 텍스트 청킹
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

logger = logging.getLogger(__name__)

class ChunkingMethod(Enum):
    """청킹 방법 열거형"""
    PYTHON_LIBRARIES = "python_libraries"  # 일반 청킹
    DOCLING = "docling"  # Docling 청킹

class DocumentFormat(Enum):
    """지원되는 문서 형식"""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    PPTX = "pptx"
    PPT = "ppt"
    XLSX = "xlsx"
    XLS = "xls"
    TXT = "txt"
    MD = "md"

@dataclass
class ChunkMetadata:
    """청크 메타데이터"""
    chunk_id: str
    chunk_index: int
    source_page: Optional[int] = None
    source_slide: Optional[int] = None
    source_sheet: Optional[str] = None
    content_type: Optional[str] = None  # text, table, image_caption 등
    confidence_score: Optional[float] = None

@dataclass
class DocumentChunk:
    """문서 청크"""
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    length: int
    embedding: Optional[List[float]] = None

@dataclass
class ProcessingResult:
    """처리 결과"""
    success: bool
    chunks: List[DocumentChunk]
    method_used: ChunkingMethod
    processing_time: float
    error_message: Optional[str] = None
    total_chunks: int = 0

class EnhancedChunker:
    """향상된 문서 청킹 시스템"""

    def __init__(self,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 docling_host: str = "localhost",
                 docling_port: int = 5000):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.docling_client = DoclingClient(host=docling_host, port=docling_port) if DOCLING_AVAILABLE else None

        # 텍스트 분할기 초기화
        if LANGCHAIN_AVAILABLE:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )
        else:
            self.text_splitter = None

    async def process_document(self,
                              file_path: str,
                              filename: str,
                              method: ChunkingMethod = ChunkingMethod.PYTHON_LIBRARIES,
                              prefer_docling: bool = True) -> ProcessingResult:
        """
        문서를 처리하여 청크로 분할

        Args:
            file_path: 파일 경로
            filename: 파일명
            method: 청킹 방법
            prefer_docling: Docling 우선 사용 여부
        """
        start_time = datetime.now()

        # 파일 형식 감지
        file_format = self._detect_format(filename)

        try:
            # 청킹 방법 결정
            if prefer_docling and DOCLING_AVAILABLE and self.docling_client:
                # Docling 먼저 시도
                if file_format in [DocumentFormat.PDF, DocumentFormat.DOCX, DocumentFormat.PPTX, DocumentFormat.XLSX]:
                    try:
                        result = await self._process_with_docling(file_path, filename, file_format)
                        if result.success:
                            return result
                    except Exception as e:
                        logger.warning(f"Docling 처리 실패, Python 라이브러리로 대체: {e}")

            # Python 라이브러리로 처리
            result = await self._process_with_python_libraries(file_path, filename, file_format)

            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time = processing_time

            return result

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"문서 처리 실패: {e}")
            return ProcessingResult(
                success=False,
                chunks=[],
                method_used=method,
                processing_time=processing_time,
                error_message=str(e)
            )

    async def _process_with_docling(self, file_path: str, filename: str, file_format: DocumentFormat) -> ProcessingResult:
        """Docling을 사용한 문서 처리"""
        try:
            # Docling으로 문서 파싱
            parsed_data = await self.docling_client.parse_document(file_path)

            chunks = []
            for i, content_block in enumerate(parsed_data.get('content_blocks', [])):
                # Docling의 구조화된 데이터를 청크로 변환
                text = content_block.get('text', '')
                if not text.strip():
                    continue

                chunk_id = str(uuid.uuid4())
                metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    chunk_index=i,
                    source_page=content_block.get('page_number'),
                    content_type=content_block.get('content_type', 'text'),
                    confidence_score=content_block.get('confidence', 1.0)
                )

                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    text=text,
                    metadata=metadata,
                    length=len(text)
                )
                chunks.append(chunk)

            return ProcessingResult(
                success=True,
                chunks=chunks,
                method_used=ChunkingMethod.DOCLING,
                processing_time=0,  # 나중에 설정됨
                total_chunks=len(chunks)
            )

        except Exception as e:
            logger.error(f"Docling 처리 실패: {e}")
            raise

    async def _process_with_python_libraries(self, file_path: str, filename: str, file_format: DocumentFormat) -> ProcessingResult:
        """Python 라이브러리를 사용한 문서 처리 - 다중 포맷 파서 우선 사용"""

        # 다중 포맷 파서 사용 시도 (최우선)
        if MULTI_FORMAT_PARSER_AVAILABLE:
            try:
                logger.info(f"🚀 [ENHANCED] Using multi-format parser for {filename}")
                parser = get_multi_format_parser()
                parse_result = await parser.parse_document(file_path, filename)

                if parse_result.success and parse_result.extracted_text.strip():
                    logger.info(f"✅ [ENHANCED] Multi-format parsing successful: {parse_result.char_count} chars, method: {parse_result.method_used}")

                    # 이미 한글 청킹이 적용된 경우 chunks 반환, 아니면 기본 청킹 적용
                    if parse_result.chunks:
                        # 한글 청킹이 이미 적용된 경우
                        chunks = []
                        for chunk_data in parse_result.chunks:
                            chunk = DocumentChunk(
                                chunk_id=str(chunk_data.get('chunk_id', uuid.uuid4())),
                                text=chunk_data['text'],
                                length=chunk_data.get('length', len(chunk_data['text'])),
                                metadata=ChunkMetadata(
                                    chunk_id=str(chunk_data.get('chunk_id', uuid.uuid4())),
                                    chunk_index=chunk_data.get('chunk_id', 0),
                                    content_type="multi_format_parsed"
                                )
                            )
                            chunks.append(chunk)

                        logger.info(f"✅ [ENHANCED] Using Korean chunking from multi-format parser: {len(chunks)} chunks")
                    else:
                        # 기본 청킹 적용
                        chunks = self._split_text_into_chunks(parse_result.extracted_text)

                    return ProcessingResult(
                        success=True,
                        chunks=chunks,
                        method_used=ChunkingMethod.PYTHON_LIBRARIES,
                        processing_time=parse_result.processing_time,
                        total_chunks=len(chunks),
                        error_message=None
                    )
                else:
                    logger.warning(f"⚠️ [ENHANCED] Multi-format parsing failed: {parse_result.error_message}")
            except Exception as e:
                logger.warning(f"⚠️ [ENHANCED] Multi-format parser error: {e}")

        # 고급 전처리기 사용 시도 (fallback)
        if ADVANCED_PREPROCESSOR_AVAILABLE:
            try:
                logger.info(f"🔧 [ENHANCED] Using advanced preprocessor for {filename}")
                preprocessor = get_advanced_preprocessor()
                preprocess_result = await preprocessor.preprocess_document(file_path, filename)

                if preprocess_result.success and preprocess_result.extracted_text.strip():
                    logger.info(f"✅ [ENHANCED] Advanced preprocessing successful: {preprocess_result.char_count} chars, method: {preprocess_result.method_used}")
                    text_content = preprocess_result.extracted_text

                    # 텍스트를 청크로 분할
                    chunks = self._split_text_into_chunks(text_content)

                    return ProcessingResult(
                        success=True,
                        chunks=chunks,
                        method_used=ChunkingMethod.PYTHON_LIBRARIES,
                        processing_time=preprocess_result.processing_time,
                        total_chunks=len(chunks),
                        error_message=None
                    )
                else:
                    logger.warning(f"⚠️ [ENHANCED] Advanced preprocessing failed: {preprocess_result.error_message}")
            except Exception as e:
                logger.warning(f"⚠️ [ENHANCED] Advanced preprocessor error: {e}")

        # 기존 방법으로 fallback
        logger.info(f"🔄 [ENHANCED] Falling back to basic extraction for {filename}")

        # 문서 형식별 텍스트 추출
        if file_format == DocumentFormat.PDF:
            text_content = self._extract_pdf_text(file_path)
        elif file_format in [DocumentFormat.DOCX, DocumentFormat.DOC]:
            text_content = self._extract_docx_text(file_path)
        elif file_format in [DocumentFormat.PPTX, DocumentFormat.PPT]:
            text_content = self._extract_pptx_text(file_path)
        elif file_format in [DocumentFormat.XLSX, DocumentFormat.XLS]:
            text_content = self._extract_excel_text(file_path)
        elif file_format in [DocumentFormat.TXT, DocumentFormat.MD]:
            text_content = self._extract_text_file(file_path)
        else:
            raise ValueError(f"지원되지 않는 파일 형식: {file_format}")

        # 텍스트를 청크로 분할
        chunks = self._split_text_into_chunks(text_content)

        return ProcessingResult(
            success=True,
            chunks=chunks,
            method_used=ChunkingMethod.PYTHON_LIBRARIES,
            processing_time=0,  # 나중에 설정됨
            total_chunks=len(chunks)
        )

    def _detect_format(self, filename: str) -> DocumentFormat:
        """파일 확장자로 형식 감지"""
        ext = filename.lower().split('.')[-1]

        format_map = {
            'pdf': DocumentFormat.PDF,
            'docx': DocumentFormat.DOCX,
            'doc': DocumentFormat.DOC,
            'pptx': DocumentFormat.PPTX,
            'ppt': DocumentFormat.PPT,
            'xlsx': DocumentFormat.XLSX,
            'xls': DocumentFormat.XLS,
            'txt': DocumentFormat.TXT,
            'md': DocumentFormat.MD
        }

        return format_map.get(ext, DocumentFormat.TXT)

    def _extract_pdf_text(self, file_path: str) -> str:
        """PDF 텍스트 추출"""
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2가 설치되지 않음")

        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += f"\n--- 페이지 {page_num + 1} ---\n{page_text}\n"
        return text

    def _extract_docx_text(self, file_path: str) -> str:
        """강화된 DOCX 텍스트 추출 - 구조 정보 보존 및 다양한 요소 처리"""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx가 설치되지 않음")

        try:
            doc = DocxDocument(file_path)
            text_parts = []

            logger.info(f"📄 [DOCX] Processing document with {len(doc.paragraphs)} paragraphs and {len(doc.tables)} tables")

            # 문서의 모든 블록 요소를 순서대로 처리
            for element in doc.element.body:
                if element.tag.endswith('}p'):  # 단락
                    paragraph = Paragraph(element, doc)
                    if paragraph.text.strip():
                        # 스타일 정보 추가
                        style_info = ""
                        if paragraph.style.name != 'Normal':
                            style_info = f"[{paragraph.style.name}] "
                        text_parts.append(f"{style_info}{paragraph.text}")

                elif element.tag.endswith('}tbl'):  # 표
                    table = Table(element, doc)
                    text_parts.append("\n=== 표 시작 ===")

                    for i, row in enumerate(table.rows):
                        if i == 0:  # 헤더 행
                            header_cells = [cell.text.strip() for cell in row.cells]
                            text_parts.append(f"[헤더] {' | '.join(header_cells)}")
                            text_parts.append("-" * 50)
                        else:
                            row_cells = [cell.text.strip() for cell in row.cells]
                            text_parts.append(f"[행{i}] {' | '.join(row_cells)}")

                    text_parts.append("=== 표 끝 ===\n")

            # 추가적인 메타데이터 정보 수집
            core_props = doc.core_properties
            if core_props.title:
                text_parts.insert(0, f"문서 제목: {core_props.title}\n")
            if core_props.subject:
                text_parts.insert(-1 if core_props.title else 0, f"문서 주제: {core_props.subject}\n")

            # 헤더/푸터 내용 추출
            for section in doc.sections:
                if section.header:
                    header_text = self._extract_header_footer_text(section.header)
                    if header_text.strip():
                        text_parts.insert(0, f"[헤더] {header_text}\n")

                if section.footer:
                    footer_text = self._extract_header_footer_text(section.footer)
                    if footer_text.strip():
                        text_parts.append(f"\n[푸터] {footer_text}")

            final_text = "\n".join(text_parts)

            logger.info(f"📄 [DOCX] Extracted {len(final_text)} characters from document")

            # 빈 텍스트 처리
            if not final_text.strip():
                logger.warning("📄 [DOCX] No text extracted, trying fallback methods")
                return self._extract_docx_fallback(file_path)

            return final_text

        except Exception as e:
            logger.error(f"❌ [DOCX] Enhanced extraction failed: {e}")
            logger.info("📄 [DOCX] Trying fallback extraction method...")
            return self._extract_docx_fallback(file_path)

    def _extract_header_footer_text(self, header_or_footer) -> str:
        """헤더/푸터에서 텍스트 추출"""
        text_parts = []
        for paragraph in header_or_footer.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text.strip())
        return " ".join(text_parts)

    def _extract_docx_fallback(self, file_path: str) -> str:
        """DOCX 대체 추출 방법 - 다양한 접근법 시도"""
        try:
            # 방법 1: 기본 python-docx 방법
            doc = DocxDocument(file_path)
            text_parts = []

            # 모든 단락 텍스트
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            # 모든 표 내용
            for table in doc.tables:
                table_text = []
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        # 셀 내부의 모든 단락 텍스트 추출
                        cell_paragraphs = []
                        for para in cell.paragraphs:
                            if para.text.strip():
                                cell_paragraphs.append(para.text.strip())
                        if cell_paragraphs:
                            row_text.append(" ".join(cell_paragraphs))
                        else:
                            row_text.append("")
                    if any(cell.strip() for cell in row_text):
                        table_text.append(" | ".join(row_text))

                if table_text:
                    text_parts.extend(table_text)

            result = "\n".join(text_parts)

            if not result.strip():
                # 방법 2: 원시 XML 파싱 시도
                logger.info("📄 [DOCX] Trying raw XML parsing...")
                result = self._extract_docx_raw_xml(file_path)

            return result if result.strip() else "문서에서 텍스트를 추출할 수 없습니다."

        except Exception as e:
            logger.error(f"❌ [DOCX] Fallback extraction failed: {e}")
            return f"DOCX 텍스트 추출 실패: {str(e)}"

    def _extract_docx_raw_xml(self, file_path: str) -> str:
        """원시 XML 파싱을 통한 DOCX 텍스트 추출"""
        try:
            import zipfile
            import xml.etree.ElementTree as ET

            text_parts = []

            with zipfile.ZipFile(file_path, 'r') as docx_zip:
                # document.xml 읽기
                if 'word/document.xml' in docx_zip.namelist():
                    with docx_zip.open('word/document.xml') as doc_xml:
                        tree = ET.parse(doc_xml)
                        root = tree.getroot()

                        # 모든 텍스트 노드 찾기 (네임스페이스 무시)
                        for elem in root.iter():
                            if elem.tag.endswith('}t'):  # 텍스트 요소
                                if elem.text:
                                    text_parts.append(elem.text)
                            elif elem.tag.endswith('}tab'):  # 탭
                                text_parts.append('\t')
                            elif elem.tag.endswith('}br'):  # 줄바꿈
                                text_parts.append('\n')

            return " ".join(text_parts) if text_parts else ""

        except Exception as e:
            logger.error(f"❌ [DOCX] Raw XML parsing failed: {e}")
            return ""

    def _extract_pptx_text(self, file_path: str) -> str:
        """PPTX 텍스트 추출"""
        if not PPTX_AVAILABLE:
            raise ImportError("python-pptx가 설치되지 않음")

        prs = Presentation(file_path)
        text = ""

        for slide_num, slide in enumerate(prs.slides):
            text += f"\n--- 슬라이드 {slide_num + 1} ---\n"

            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"

        return text

    def _extract_excel_text(self, file_path: str) -> str:
        """Excel 텍스트 추출"""
        if not EXCEL_AVAILABLE:
            raise ImportError("openpyxl이 설치되지 않음")

        workbook = openpyxl.load_workbook(file_path, data_only=True)
        text = ""

        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            text += f"\n--- 시트: {sheet_name} ---\n"

            for row in sheet.iter_rows(values_only=True):
                row_text = "\t".join(str(cell) if cell is not None else "" for cell in row)
                if row_text.strip():
                    text += row_text + "\n"

        return text

    def _extract_text_file(self, file_path: str) -> str:
        """텍스트 파일 추출"""
        encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue

        # 모든 인코딩 실패시 바이너리로 읽고 에러 무시
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()

    def _split_text_into_chunks(self, text: str) -> List[DocumentChunk]:
        """텍스트를 청크로 분할"""
        if self.text_splitter and LANGCHAIN_AVAILABLE:
            # LangChain 텍스트 분할기 사용
            text_chunks = self.text_splitter.split_text(text)
        else:
            # 간단한 분할 로직
            text_chunks = self._simple_text_split(text)

        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            if not chunk_text.strip():
                continue

            chunk_id = str(uuid.uuid4())
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                chunk_index=i,
                content_type='text'
            )

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                text=chunk_text.strip(),
                metadata=metadata,
                length=len(chunk_text)
            )
            chunks.append(chunk)

        return chunks

    def _simple_text_split(self, text: str) -> List[str]:
        """간단한 텍스트 분할"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # 단어 경계에서 분할
            if end < len(text):
                while end > start and text[end] not in [' ', '\n', '.', '!', '?']:
                    end -= 1
                if end == start:  # 적절한 분할점을 찾지 못한 경우
                    end = start + self.chunk_size

            chunk = text[start:end]
            chunks.append(chunk)

            start = end - self.chunk_overlap
            if start < 0:
                start = 0

        return chunks

# 유틸리티 함수
async def create_enhanced_chunker(chunk_size: int = 1000,
                                 chunk_overlap: int = 200) -> EnhancedChunker:
    """향상된 청킹기 생성"""
    return EnhancedChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )