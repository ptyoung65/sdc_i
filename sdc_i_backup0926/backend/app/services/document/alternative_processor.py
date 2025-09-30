"""
Alternative Document Processor - 로컬 Python 라이브러리를 사용한 문서 처리

Docling 서비스가 사용 불가능할 때의 대안 처리기입니다.
python-docx, python-pptx, openpyxl, PyPDF2 등을 사용합니다.
"""

import os
import io
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class AlternativeProcessor:
    """로컬 Python 라이브러리를 사용한 문서 처리기"""
    
    def __init__(self):
        self.available_libraries = self._check_available_libraries()
        
    def _check_available_libraries(self) -> Dict[str, bool]:
        """사용 가능한 라이브러리 확인"""
        libraries = {}

        try:
            import docx
            libraries['docx'] = True
            logger.info("✅ python-docx library available")
        except ImportError:
            libraries['docx'] = False
            logger.warning("❌ python-docx library not available")

        try:
            import docx2txt
            libraries['docx2txt'] = True
            logger.info("✅ docx2txt library available for legacy .doc files")
        except ImportError:
            libraries['docx2txt'] = False
            logger.warning("❌ docx2txt library not available")

        try:
            from pptx import Presentation
            libraries['pptx'] = True
            logger.info("✅ python-pptx library available")
        except ImportError:
            libraries['pptx'] = False
            logger.warning("❌ python-pptx library not available")

        try:
            import openpyxl
            libraries['openpyxl'] = True
            logger.info("✅ openpyxl library available")
        except ImportError:
            libraries['openpyxl'] = False
            logger.warning("❌ openpyxl library not available")

        try:
            import PyPDF2
            libraries['pypdf2'] = True
            logger.info("✅ PyPDF2 library available")
        except ImportError:
            libraries['pypdf2'] = False
            logger.warning("❌ PyPDF2 library not available")

        return libraries
    
    def is_available(self) -> bool:
        """최소 하나의 라이브러리라도 사용 가능한지 확인"""
        return any(self.available_libraries.values())
    
    async def process_document(self, file_content: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
        """
        문서를 로컬 라이브러리로 처리
        
        Args:
            file_content: 파일의 바이트 내용
            filename: 파일명 (확장자 포함)
            
        Returns:
            (성공여부, 결과데이터)
        """
        ext = os.path.splitext(filename.lower())[1]
        
        try:
            if ext == '.docx' and self.available_libraries.get('docx'):
                return await self._process_docx(file_content, filename)
            elif ext == '.doc' and self.available_libraries.get('docx2txt'):
                return await self._process_legacy_doc(file_content, filename)
            elif ext == '.pptx' and self.available_libraries.get('pptx'):
                return await self._process_pptx(file_content, filename)
            elif ext == '.ppt':
                return await self._process_legacy_ppt(file_content, filename)
            elif ext in ['.xlsx', '.xls'] and self.available_libraries.get('openpyxl'):
                return await self._process_excel(file_content, filename)
            elif ext == '.pdf' and self.available_libraries.get('pypdf2'):
                return await self._process_pdf(file_content, filename)
            else:
                return False, {
                    'method': 'alternative_processor',
                    'error': f'Unsupported file type {ext} or missing library',
                    'status': 'failed'
                }
                
        except Exception as e:
            logger.error(f"Alternative processor error: {e}")
            return False, {
                'method': 'alternative_processor',
                'error': str(e),
                'status': 'failed'
            }
    
    async def _process_docx(self, file_content: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
        """DOCX 파일 처리"""
        try:
            import docx
            
            doc_stream = io.BytesIO(file_content)
            doc = docx.Document(doc_stream)
            
            text_content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text.strip())
                    
            content = '\n\n'.join(text_content)
            
            return True, {
                'method': 'alternative_processor',
                'content': content,
                'metadata': {
                    'paragraphs': len(doc.paragraphs),
                    'characters': len(content)
                },
                'status': 'success'
            }
            
        except Exception as e:
            return False, {
                'method': 'alternative_processor',
                'error': f'DOCX processing failed: {str(e)}',
                'status': 'failed'
            }

    async def _process_legacy_doc(self, file_content: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
        """Legacy DOC 파일 처리 (.doc)"""
        try:
            import docx2txt
            import tempfile
            import os

            print(f"📄 [LEGACY-DOC] Processing legacy DOC file: {filename}")

            # 임시 파일 생성 (docx2txt는 파일 경로가 필요)
            with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name

            try:
                # docx2txt로 텍스트 추출
                text_content = docx2txt.process(temp_file_path)

                # 임시 파일 삭제
                os.unlink(temp_file_path)

                if text_content and text_content.strip():
                    content = text_content.strip()

                    print(f"📄 [LEGACY-DOC] Successfully extracted {len(content)} characters from {filename}")

                    return True, {
                        'method': 'alternative_processor',
                        'content': content,
                        'metadata': {
                            'file_type': 'legacy_doc',
                            'characters': len(content),
                            'extraction_library': 'docx2txt'
                        },
                        'status': 'success'
                    }
                else:
                    # 텍스트가 추출되지 않은 경우
                    fallback_content = f"""Legacy DOC 파일 '{filename}' 처리 결과:

⚠️ 이 파일에서 텍스트를 추출할 수 없었습니다.

가능한 원인:
• 파일이 손상되었거나 암호로 보호되어 있습니다
• 파일이 주로 이미지나 그래픽으로 구성되어 있습니다
• 특수한 문서 구조로 인해 텍스트 추출이 어렵습니다

권장 해결 방법:
1. 파일을 Microsoft Word에서 열어 정상 작동 확인
2. '다른 이름으로 저장'으로 DOCX 형식으로 변환
3. 변환된 DOCX 파일을 다시 업로드"""

                    print(f"⚠️ [LEGACY-DOC] No text extracted from {filename}")

                    return True, {
                        'method': 'alternative_processor',
                        'content': fallback_content,
                        'metadata': {
                            'file_type': 'legacy_doc',
                            'characters': len(fallback_content),
                            'extraction_library': 'docx2txt',
                            'extraction_status': 'no_text_found'
                        },
                        'status': 'success'
                    }

            except Exception as extract_error:
                # 임시 파일 삭제 (오류 발생 시에도)
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

                error_msg = f'Legacy DOC text extraction failed: {str(extract_error)}'
                print(f"❌ [LEGACY-DOC] {error_msg}")

                return False, {
                    'method': 'alternative_processor',
                    'error': error_msg,
                    'status': 'failed'
                }

        except Exception as e:
            error_msg = f'Legacy DOC processing failed: {str(e)}'
            print(f"❌ [LEGACY-DOC] {error_msg}")
            return False, {
                'method': 'alternative_processor',
                'error': error_msg,
                'status': 'failed'
            }

    async def _process_pptx(self, file_content: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
        """PPTX 파일 처리 (개선된 버전)"""
        try:
            from pptx import Presentation
            from pptx.enum.shapes import MSO_SHAPE_TYPE

            ppt_stream = io.BytesIO(file_content)
            prs = Presentation(ppt_stream)

            text_content = []
            slide_count = 0
            total_shapes = 0
            extracted_text_count = 0

            print(f"📄 [PPTX] Processing {filename} with {len(prs.slides)} slides")

            for slide in prs.slides:
                slide_count += 1
                slide_text = []

                # 슬라이드의 모든 도형 처리
                for shape in slide.shapes:
                    total_shapes += 1

                    try:
                        # 텍스트 박스, 제목, 내용 등 처리
                        if hasattr(shape, 'text') and shape.text.strip():
                            text = shape.text.strip()
                            slide_text.append(text)
                            extracted_text_count += 1
                            print(f"📄 [PPTX] Slide {slide_count}: Extracted text: {text[:50]}...")

                        # 테이블 처리
                        elif shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                            table = shape.table
                            table_text = []
                            for row in table.rows:
                                row_text = []
                                for cell in row.cells:
                                    if cell.text.strip():
                                        row_text.append(cell.text.strip())
                                if row_text:
                                    table_text.append(' | '.join(row_text))
                            if table_text:
                                slide_text.append("테이블:\n" + '\n'.join(table_text))
                                extracted_text_count += 1

                        # 그룹 도형 처리
                        elif shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                            for grouped_shape in shape.shapes:
                                if hasattr(grouped_shape, 'text') and grouped_shape.text.strip():
                                    slide_text.append(grouped_shape.text.strip())
                                    extracted_text_count += 1

                    except Exception as shape_error:
                        print(f"⚠️ [PPTX] Shape processing error in slide {slide_count}: {shape_error}")
                        continue

                # 슬라이드에 노트가 있는 경우 처리
                if hasattr(slide, 'notes_slide') and slide.notes_slide:
                    try:
                        notes_text = slide.notes_slide.notes_text_frame.text.strip()
                        if notes_text:
                            slide_text.append(f"노트: {notes_text}")
                            extracted_text_count += 1
                    except:
                        pass

                # 슬라이드별 텍스트 정리
                if slide_text:
                    slide_content = f"=== 슬라이드 {slide_count} ===\n" + '\n'.join(slide_text)
                    text_content.append(slide_content)
                else:
                    # 텍스트가 없는 슬라이드도 기록
                    text_content.append(f"=== 슬라이드 {slide_count} ===\n(이미지 또는 그래픽 요소만 포함)")

            content = '\n\n'.join(text_content)

            # 처리 결과 로깅
            print(f"📄 [PPTX] Processing complete:")
            print(f"  - Total slides: {slide_count}")
            print(f"  - Total shapes: {total_shapes}")
            print(f"  - Extracted text elements: {extracted_text_count}")
            print(f"  - Final content length: {len(content)} characters")

            # 최소한의 텍스트도 추출되지 않은 경우
            if not content.strip() or len(content.strip()) < 10:
                fallback_content = f"""PPT 파일 '{filename}' 분석 결과:

슬라이드 수: {slide_count}개
처리된 도형: {total_shapes}개

이 PPT 파일은 주로 이미지, 그래픽, 또는 특수 요소로 구성되어 있어
텍스트를 추출할 수 없었습니다.

파일을 다시 확인하거나 텍스트가 포함된 슬라이드로
다시 업로드해 주세요."""

                return True, {
                    'method': 'alternative_processor',
                    'content': fallback_content,
                    'metadata': {
                        'slides': slide_count,
                        'total_shapes': total_shapes,
                        'extracted_elements': extracted_text_count,
                        'characters': len(fallback_content),
                        'extraction_status': 'fallback_used'
                    },
                    'status': 'success'
                }

            return True, {
                'method': 'alternative_processor',
                'content': content,
                'metadata': {
                    'slides': slide_count,
                    'total_shapes': total_shapes,
                    'extracted_elements': extracted_text_count,
                    'characters': len(content),
                    'extraction_status': 'success'
                },
                'status': 'success'
            }

        except Exception as e:
            error_msg = f'PPTX processing failed: {str(e)}'
            print(f"❌ [PPTX] {error_msg}")
            return False, {
                'method': 'alternative_processor',
                'error': error_msg,
                'status': 'failed'
            }
    
    async def _process_excel(self, file_content: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
        """Excel 파일 처리"""
        try:
            import openpyxl
            
            excel_stream = io.BytesIO(file_content)
            workbook = openpyxl.load_workbook(excel_stream)
            
            text_content = []
            total_rows = 0
            
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                sheet_text = [f"시트: {sheet_name}"]
                
                for row in sheet.iter_rows(values_only=True):
                    if any(cell is not None and str(cell).strip() for cell in row):
                        row_text = '\t'.join([str(cell) if cell is not None else '' for cell in row])
                        sheet_text.append(row_text)
                        total_rows += 1
                        
                if len(sheet_text) > 1:  # 시트 제목 외에 데이터가 있는 경우
                    text_content.append('\n'.join(sheet_text))
                    
            content = '\n\n'.join(text_content)
            
            return True, {
                'method': 'alternative_processor',
                'content': content,
                'metadata': {
                    'sheets': len(workbook.sheetnames),
                    'rows': total_rows,
                    'characters': len(content)
                },
                'status': 'success'
            }
            
        except Exception as e:
            return False, {
                'method': 'alternative_processor',
                'error': f'Excel processing failed: {str(e)}',
                'status': 'failed'
            }
    
    async def _process_pdf(self, file_content: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
        """PDF 파일 처리"""
        try:
            import PyPDF2
            
            pdf_stream = io.BytesIO(file_content)
            reader = PyPDF2.PdfReader(pdf_stream)
            
            text_content = []
            page_count = len(reader.pages)
            
            for i, page in enumerate(reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(f"페이지 {i}:\n{page_text.strip()}")
                except Exception as e:
                    logger.warning(f"페이지 {i} 추출 실패: {e}")
                    continue
                    
            content = '\n\n'.join(text_content)
            
            return True, {
                'method': 'alternative_processor',
                'content': content,
                'metadata': {
                    'pages': page_count,
                    'characters': len(content)
                },
                'status': 'success'
            }
            
        except Exception as e:
            return False, {
                'method': 'alternative_processor',
                'error': f'PDF processing failed: {str(e)}',
                'status': 'failed'
            }

    async def _process_legacy_ppt(self, file_content: bytes, filename: str) -> Tuple[bool, Dict[str, Any]]:
        """Legacy PPT 파일 처리 (.ppt)"""
        try:
            print(f"📄 [LEGACY-PPT] Processing legacy PPT file: {filename}")

            # Legacy PPT 파일은 python-pptx로 직접 처리할 수 없으므로 안내 메시지 제공
            content = f"""Legacy PPT 파일 '{filename}' 처리 결과:

⚠️ 이 파일은 구형 PowerPoint 형식(.ppt)입니다.

현재 시스템의 제한사항:
• Legacy PPT 파일은 직접 텍스트 추출이 어렵습니다
• 최적의 처리를 위해서는 PPTX 형식으로 변환해 주세요

권장 해결 방법:
1. PowerPoint에서 파일을 열고 '다른 이름으로 저장'
2. 파일 형식을 'PowerPoint 프레젠테이션(*.pptx)'로 선택
3. 저장된 PPTX 파일을 다시 업로드

또는 Docling 서비스를 통한 처리를 시도할 수 있습니다."""

            print(f"📄 [LEGACY-PPT] Providing user guidance for {filename}")

            return True, {
                'method': 'alternative_processor',
                'content': content,
                'metadata': {
                    'file_type': 'legacy_ppt',
                    'characters': len(content),
                    'processing_note': 'Legacy format requires conversion to PPTX'
                },
                'status': 'success'
            }

        except Exception as e:
            error_msg = f'Legacy PPT processing failed: {str(e)}'
            print(f"❌ [LEGACY-PPT] {error_msg}")
            return False, {
                'method': 'alternative_processor',
                'error': error_msg,
                'status': 'failed'
            }

    def is_supported_format(self, filename: str) -> bool:
        """지원되는 파일 형식인지 확인"""
        ext = os.path.splitext(filename.lower())[1]

        if ext == '.docx':
            return self.available_libraries.get('docx', False)
        elif ext == '.doc':
            return self.available_libraries.get('docx2txt', False)
        elif ext == '.pptx':
            return self.available_libraries.get('pptx', False)
        elif ext == '.ppt':
            return True  # Legacy PPT는 항상 처리 가능 (안내 메시지 제공)
        elif ext in ['.xlsx', '.xls']:
            return self.available_libraries.get('openpyxl', False)
        elif ext == '.pdf':
            return self.available_libraries.get('pypdf2', False)

        return False

# 전역 프로세서 인스턴스
alternative_processor = AlternativeProcessor()