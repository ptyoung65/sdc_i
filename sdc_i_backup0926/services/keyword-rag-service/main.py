#!/usr/bin/env python3
"""
Keyword RAG Service - Dummy Version
키워드 기반 RAG 서비스의 더미 버전
"""

import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import argparse

# 기본 FastAPI 앱 생성
app = FastAPI(
    title="Keyword RAG Service",
    description="키워드 기반 RAG 서비스 - 더미 버전",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    query: str
    keywords: Optional[List[str]] = None
    max_results: Optional[int] = 10

class QueryResponse(BaseModel):
    query: str
    results: List[dict]
    status: str

@app.get("/")
async def root():
    return {"message": "Keyword RAG Service", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "keyword-rag", "port": 8011}

@app.get("/status")
async def status():
    return {
        "service": "keyword-rag",
        "status": "healthy",
        "features": ["keyword_extraction", "semantic_search", "rag_pipeline"],
        "version": "1.0.0"
    }

@app.post("/search")
async def search(request: QueryRequest):
    """키워드 기반 검색 엔드포인트"""
    return QueryResponse(
        query=request.query,
        results=[
            {
                "id": 1,
                "content": f"Sample result for query: {request.query}",
                "score": 0.95,
                "keywords": request.keywords or ["sample", "keyword"]
            }
        ],
        status="success"
    )

@app.post("/extract_keywords")
async def extract_keywords(text: str):
    """텍스트에서 키워드 추출"""
    # 더미 키워드 추출
    words = text.split()[:5]  # 처음 5개 단어를 키워드로
    return {
        "keywords": words,
        "text_length": len(text),
        "status": "success"
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Keyword RAG Service")
    parser.add_argument("--port", type=int, default=8011, help="Port to run the service on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the service on")
    args = parser.parse_args()

    print(f"🚀 Keyword RAG Service Starting...")
    print(f"📍 Running on http://{args.host}:{args.port}")
    print(f"📚 Keyword-based RAG service ready")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )