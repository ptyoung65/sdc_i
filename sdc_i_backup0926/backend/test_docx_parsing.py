#!/usr/bin/env python3
"""
DOCX 파싱 기능 테스트 스크립트
새로 설치된 라이브러리들이 정상적으로 작동하는지 확인
"""

import sys
import requests
import json
from pathlib import Path

def test_docx_parsing():
    """DOCX 파싱 API 테스트"""

    print("🧪 DOCX 파싱 기능 테스트 시작...")

    # 테스트 DOCX 파일 생성
    print("📄 테스트 DOCX 파일 생성 중...")
    try:
        from docx import Document

        # 테스트 문서 생성
        doc = Document()
        doc.add_heading('SDC DOCX 파싱 테스트 문서', 0)

        doc.add_heading('1. 개요', level=1)
        doc.add_paragraph('이 문서는 SDC 시스템의 DOCX 파싱 기능을 테스트하기 위한 문서입니다.')
        doc.add_paragraph('새로 설치된 python-docx 라이브러리가 정상적으로 작동하는지 확인합니다.')

        doc.add_heading('2. 주요 기능', level=1)
        doc.add_paragraph('다음과 같은 기능들이 테스트됩니다:')
        doc.add_paragraph('• DOCX 파일 읽기')
        doc.add_paragraph('• 텍스트 추출')
        doc.add_paragraph('• 한국어 문장 청킹')
        doc.add_paragraph('• 메타데이터 추출')

        doc.add_heading('3. 예상 결과', level=1)
        doc.add_paragraph('이 문서를 업로드하면 다음과 같은 결과를 얻을 수 있습니다:')
        doc.add_paragraph('✅ 성공적인 텍스트 추출')
        doc.add_paragraph('✅ 한국어 문장 단위 청킹')
        doc.add_paragraph('✅ 정확한 메타데이터 파싱')

        # 파일 저장
        test_file_path = Path('test_docx_parsing.docx')
        doc.save(test_file_path)
        print(f"✅ 테스트 파일 생성 완료: {test_file_path}")

        return test_file_path

    except Exception as e:
        print(f"❌ 테스트 파일 생성 실패: {e}")
        return None

def upload_and_test_file(file_path):
    """파일 업로드 및 파싱 테스트"""

    print(f"📤 파일 업로드 테스트: {file_path}")

    try:
        # API 엔드포인트
        upload_url = "http://localhost:8000/api/v1/documents"

        # 파일 업로드
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            data = {'user_id': 'test_user'}

            response = requests.post(upload_url, files=files, data=data)

        print(f"📊 응답 상태: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ 업로드 성공!")
            print(f"📄 문서 ID: {result.get('document_id', 'N/A')}")
            print(f"📝 추출된 텍스트 길이: {len(result.get('content', ''))} 문자")
            print(f"🔧 처리 방법: {result.get('processing_method', 'N/A')}")

            # 추출된 텍스트 일부 확인
            content = result.get('content', '')
            if content:
                print("📖 추출된 텍스트 미리보기:")
                print(content[:200] + "..." if len(content) > 200 else content)

            return True
        else:
            print(f"❌ 업로드 실패: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

def test_chat_with_document():
    """문서 기반 채팅 테스트"""

    print("💬 문서 기반 채팅 테스트...")

    try:
        chat_url = "http://localhost:8000/api/v1/chat"

        payload = {
            "message": "업로드된 문서의 주요 내용을 요약해 주세요",
            "user_id": "test_user"
        }

        response = requests.post(chat_url, json=payload)

        if response.status_code == 200:
            result = response.json()
            print("✅ 채팅 응답 성공!")
            print(f"🤖 AI 응답: {result.get('response', 'N/A')}")

            sources = result.get('sources', [])
            if sources:
                print(f"📚 참조 소스: {len(sources)}개")
                for i, source in enumerate(sources[:2]):  # 처음 2개만 표시
                    print(f"  {i+1}. {source.get('content', '')[:100]}...")

            return True
        else:
            print(f"❌ 채팅 실패: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 채팅 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""

    print("🚀 SDC DOCX 파싱 기능 통합 테스트")
    print("=" * 50)

    # 1. 테스트 파일 생성
    test_file = test_docx_parsing()
    if not test_file:
        print("❌ 테스트 파일 생성 실패로 테스트 중단")
        return False

    # 2. 파일 업로드 및 파싱 테스트
    upload_success = upload_and_test_file(test_file)
    if not upload_success:
        print("❌ 파일 업로드 실패로 테스트 중단")
        return False

    # 3. 문서 기반 채팅 테스트
    chat_success = test_chat_with_document()

    # 4. 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약:")
    print(f"✅ 테스트 파일 생성: {'성공' if test_file else '실패'}")
    print(f"✅ DOCX 파싱: {'성공' if upload_success else '실패'}")
    print(f"✅ 문서 기반 채팅: {'성공' if chat_success else '실패'}")

    if test_file and upload_success and chat_success:
        print("\n🎉 모든 테스트 통과! DOCX 파싱 기능이 정상적으로 작동합니다.")
        return True
    else:
        print("\n⚠️ 일부 테스트 실패. 추가 확인이 필요합니다.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)