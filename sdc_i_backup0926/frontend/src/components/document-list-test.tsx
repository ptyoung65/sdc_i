"use client"

import React, { useEffect } from 'react'
import { useDocumentStore } from '@/store/document-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

// 파싱 방법을 사용자 친화적으로 표시하는 함수
const getParsingMethodDisplay = (method: string): { label: string; color: string } => {
  switch (method) {
    case 'docling':
      return { label: 'Docling 서비스', color: 'text-blue-600 bg-blue-50' }
    case 'python_libraries':
      return { label: 'Python 라이브러리', color: 'text-green-600 bg-green-50' }
    case 'alternative_processor':
      return { label: '대체 프로세서', color: 'text-orange-600 bg-orange-50' }
    case 'text_fallback':
      return { label: '텍스트 대체', color: 'text-yellow-600 bg-yellow-50' }
    case 'basic_fallback':
      return { label: '기본 대체', color: 'text-gray-600 bg-gray-50' }
    case 'basic':
      return { label: '기본 처리', color: 'text-gray-600 bg-gray-50' }
    case 'korean_rag':
      return { label: '한국어 RAG', color: 'text-purple-600 bg-purple-50' }
    case 'local_storage':
      return { label: '로컬 저장소', color: 'text-indigo-600 bg-indigo-50' }
    default:
      return { label: '알 수 없음', color: 'text-gray-500 bg-gray-100' }
  }
}

export function DocumentListTest() {
  const { documents, isLoading, error, loadDocuments } = useDocumentStore()

  // 컴포넌트가 마운트되면 자동으로 문서 로드
  useEffect(() => {
    loadDocuments('default_user')
  }, [loadDocuments])

  const handleLoadDocuments = () => {
    loadDocuments('default_user')
  }

  return (
    <div className="space-y-2">
      {error && (
        <div className="p-2 bg-red-50 border border-red-200 rounded text-red-700 text-xs">
          오류: {error}
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-2 text-xs text-gray-500">
          문서 로딩 중...
        </div>
      ) : documents && documents.length > 0 ? (
        <div className="space-y-1">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="p-2 border border-gray-200 rounded-md hover:bg-gray-50"
            >
              <div className="flex justify-between items-start">
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-medium truncate">{doc.title}</h4>
                  <p className="text-xs text-gray-500">
                    {doc.type} • {(doc.size / 1024).toFixed(1)} KB
                  </p>
                  <p className="text-xs text-gray-400">
                    {new Date(doc.uploadedAt).toLocaleDateString('ko-KR')}
                  </p>
                  {/* 파싱 방법 정보 표시 */}
                  {doc.metadata?.processingMethod && (
                    <div className="mt-1">
                      <span
                        className={`inline-block px-2 py-0.5 text-xs rounded-full border ${
                          getParsingMethodDisplay(doc.metadata.processingMethod).color
                        }`}
                      >
                        📄 {getParsingMethodDisplay(doc.metadata.processingMethod).label}
                      </span>
                      {doc.metadata?.chunkCount > 0 && (
                        <span className="ml-1 text-xs text-gray-500">
                          • {doc.metadata.chunkCount}개 청크
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          
          <div className="pt-2 border-t">
            <Button 
              onClick={handleLoadDocuments} 
              disabled={isLoading}
              variant="outline" 
              size="sm"
              className="w-full h-8 text-xs"
            >
              {isLoading ? '새로고침 중...' : '새로고침'}
            </Button>
          </div>
        </div>
      ) : (
        <div className="text-center py-4">
          <div className="text-xs text-gray-500 mb-2">저장된 문서가 없습니다.</div>
          <Button 
            onClick={handleLoadDocuments} 
            disabled={isLoading}
            variant="outline" 
            size="sm"
            className="h-8 text-xs"
          >
            {isLoading ? '확인 중...' : '다시 확인'}
          </Button>
        </div>
      )}
    </div>
  )
}