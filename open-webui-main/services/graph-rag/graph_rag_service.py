"""
Vector Graph RAG 서비스 (FastAPI)
====================================
포트: 8015
의존: vector-graph-rag==0.1.3, Milvus @ 192.168.122.85:19530
임베딩: BAAI/bge-m3 (로컬 HuggingFace 캐시)
LLM: http://192.168.0.14:8000/v1 (OpenAI 호환)

주요 API:
  GET  /health             - 서비스 상태 확인
  GET  /stats              - 그래프 통계 (graph_name 쿼리 파라미터)
  GET  /graphs             - 사용 가능한 그래프 목록
  POST /documents          - 문서를 그래프에 추가
  POST /texts              - 텍스트를 그래프에 추가
  POST /query              - 그래프 RAG 질의응답
  DELETE /collection       - 컬렉션 초기화 (graph_name 쿼리 파라미터)
"""

import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# .env 파일 로드 (서비스 디렉토리 기준)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path)

from vector_graph_rag import VectorGraphRAG
from vector_graph_rag.config import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("graph-rag-service")

# ─── 스레드 풀 (동기 VectorGraphRAG 메서드를 비동기로 실행) ──────────────────────
executor = ThreadPoolExecutor(max_workers=int(os.getenv("GRAPH_RAG_WORKERS", "1")))

# ─── 그래프 인스턴스 캐시 (graph_name → VectorGraphRAG) ──────────────────────────
_rag_instances: Dict[str, VectorGraphRAG] = {}


def _build_settings(graph_name: str = "default") -> Settings:
    """graph_name 별 Settings 생성. collection_prefix 로 Milvus 컬렉션을 분리."""
    base_prefix = os.getenv("VGRAG_COLLECTION_PREFIX", "vgrag")
    prefix = base_prefix if graph_name == "default" else f"{base_prefix}_{graph_name}"

    return Settings(
        openai_api_key=os.getenv("VGRAG_OPENAI_API_KEY", "sk-local"),
        openai_base_url=os.getenv("VGRAG_OPENAI_BASE_URL"),
        llm_model=os.getenv("VGRAG_LLM_MODEL", "gpt-4o"),
        llm_temperature=float(os.getenv("VGRAG_LLM_TEMPERATURE", "0.0")),
        llm_max_retries=int(os.getenv("VGRAG_LLM_MAX_RETRIES", "3")),
        use_llm_cache=os.getenv("VGRAG_USE_LLM_CACHE", "true").lower() == "true",
        embedding_model=os.getenv("VGRAG_EMBEDDING_MODEL", "BAAI/bge-m3"),
        embedding_dimension=int(os.getenv("VGRAG_EMBEDDING_DIMENSION", "1024")),
        milvus_uri=os.getenv("VGRAG_MILVUS_URI", "http://192.168.122.85:19530"),
        milvus_token=os.getenv("VGRAG_MILVUS_TOKEN") or None,
        milvus_db=os.getenv("VGRAG_MILVUS_DB") or None,
        collection_prefix=prefix,
        entity_top_k=int(os.getenv("VGRAG_ENTITY_TOP_K", "20")),
        relation_top_k=int(os.getenv("VGRAG_RELATION_TOP_K", "20")),
        entity_similarity_threshold=float(os.getenv("VGRAG_ENTITY_SIMILARITY_THRESHOLD", "0.9")),
        relation_similarity_threshold=float(os.getenv("VGRAG_RELATION_SIMILARITY_THRESHOLD", "-1.0")),
        expansion_degree=int(os.getenv("VGRAG_EXPANSION_DEGREE", "1")),
        relation_number_threshold=int(os.getenv("VGRAG_RELATION_NUMBER_THRESHOLD", "1000")),
        final_top_k=int(os.getenv("VGRAG_FINAL_TOP_K", "3")),
        batch_size=int(os.getenv("VGRAG_BATCH_SIZE", "32")),
    )


def _get_or_create_rag(graph_name: str = "default") -> VectorGraphRAG:
    """그래프 인스턴스를 반환하거나 새로 생성."""
    if graph_name not in _rag_instances:
        logger.info(f"[graph-rag] 새 RAG 인스턴스 생성: graph_name='{graph_name}'")
        settings = _build_settings(graph_name)
        _rag_instances[graph_name] = VectorGraphRAG(settings=settings)
        logger.info(
            f"[graph-rag] RAG 초기화 완료: milvus={settings.milvus_uri}, "
            f"prefix={settings.collection_prefix}, embed={settings.embedding_model}"
        )
    return _rag_instances[graph_name]


# ─── FastAPI Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 기본 그래프 인스턴스 사전 초기화
    logger.info("[graph-rag] 서비스 시작 중 ...")
    try:
        os.makedirs(os.getenv("LLM_CACHE_DIR", "./cache/llm"), exist_ok=True)
        os.makedirs(os.getenv("NER_CACHE_DIR", "./cache/ner"), exist_ok=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, _get_or_create_rag, "default")
        logger.info("[graph-rag] 기본 RAG 인스턴스 초기화 완료")
    except Exception as e:
        logger.error(f"[graph-rag] 초기화 오류: {e}")
        logger.warning("[graph-rag] 초기화 실패 - 첫 번째 요청 시 재시도합니다")
    yield
    logger.info("[graph-rag] 서비스 종료")
    executor.shutdown(wait=False)


# ─── FastAPI 앱 ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Vector Graph RAG Service",
    description="Zilliz vector-graph-rag 기반 그래프 RAG 서비스. Milvus 벡터 DB 사용.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 요청/응답 스키마 ─────────────────────────────────────────────────────────

class AddDocumentsRequest(BaseModel):
    documents: List[str]
    graph_name: str = "default"


class AddTextsRequest(BaseModel):
    texts: List[str]
    graph_name: str = "default"


class QueryRequest(BaseModel):
    question: str
    graph_name: str = "default"
    entity_top_k: Optional[int] = None
    relation_top_k: Optional[int] = None
    expansion_degree: Optional[int] = None
    final_top_k: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    graph_name: str
    query_entities: List[str] = []
    passages: List[str] = []
    reranked_relations: List[str] = []
    expanded_relations: List[str] = []


class StatsResponse(BaseModel):
    graph_name: str
    entity_count: int
    relation_count: int
    passage_count: int


# ─── 엔드포인트 ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """서비스 상태 확인."""
    return {
        "status": "ok",
        "service": "vector-graph-rag",
        "version": "0.1.0",
        "milvus_uri": os.getenv("VGRAG_MILVUS_URI"),
        "embedding_model": os.getenv("VGRAG_EMBEDDING_MODEL"),
        "llm_model": os.getenv("VGRAG_LLM_MODEL"),
        "loaded_graphs": list(_rag_instances.keys()),
    }


@app.get("/graphs")
async def list_graphs():
    """현재 로드된 그래프 목록 반환."""
    return {
        "graphs": list(_rag_instances.keys()),
        "milvus_uri": os.getenv("VGRAG_MILVUS_URI"),
        "collection_prefix": os.getenv("VGRAG_COLLECTION_PREFIX", "vgrag"),
    }


@app.get("/stats")
async def get_stats(graph_name: str = "default"):
    """그래프 통계 반환 (엔티티/관계/패시지 수)."""
    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, graph_name)
        stats = await loop.run_in_executor(executor, rag.get_stats)
        return StatsResponse(
            graph_name=graph_name,
            entity_count=stats.get("entities", 0),
            relation_count=stats.get("relations", 0),
            passage_count=stats.get("passages", 0),
        )
    except Exception as e:
        logger.error(f"[graph-rag] stats 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents")
async def add_documents(req: AddDocumentsRequest):
    """
    문서 리스트를 그래프에 추가.
    각 문서에서 LLM으로 트리플렛(주어-술어-목적어)을 추출하고 Milvus에 저장.
    """
    if not req.documents:
        raise HTTPException(status_code=400, detail="documents 리스트가 비어 있습니다")

    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, req.graph_name)

        def _add():
            result = rag.add_texts(req.documents)
            return result

        result = await loop.run_in_executor(executor, _add)
        logger.info(
            f"[graph-rag] 문서 {len(req.documents)}개 추가 완료: graph='{req.graph_name}'"
        )
        return {
            "status": "ok",
            "graph_name": req.graph_name,
            "added_count": len(req.documents),
        }
    except Exception as e:
        logger.error(f"[graph-rag] add_documents 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/texts")
async def add_texts(req: AddTextsRequest):
    """텍스트 리스트를 그래프에 추가 (/documents 와 동일, 호환성 유지용)."""
    doc_req = AddDocumentsRequest(documents=req.texts, graph_name=req.graph_name)
    return await add_documents(doc_req)


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """
    그래프 RAG 질의응답.
    1. 질문에서 엔티티 추출
    2. Milvus 벡터 검색으로 관련 노드 검색
    3. 서브그래프 확장
    4. LLM 리랭킹 후 최종 답변 생성
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question이 비어 있습니다")

    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, req.graph_name)

        def _query():
            return rag.query(req.question)

        result = await loop.run_in_executor(executor, _query)

        return QueryResponse(
            answer=result.answer or "",
            graph_name=req.graph_name,
            query_entities=result.query_entities or [],
            passages=result.passages or [],
            reranked_relations=result.reranked_relations or [],
            expanded_relations=result.expanded_relations or [],
        )
    except Exception as e:
        logger.error(f"[graph-rag] query 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collection")
async def delete_collection(graph_name: str = "default"):
    """
    그래프 컬렉션 초기화 (Milvus 데이터 삭제).
    주의: 되돌릴 수 없습니다.
    """
    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, graph_name)
        await loop.run_in_executor(executor, rag.reset)

        # 인스턴스 캐시에서 제거 (재초기화 강제)
        if graph_name in _rag_instances:
            del _rag_instances[graph_name]

        logger.info(f"[graph-rag] 컬렉션 초기화 완료: graph='{graph_name}'")
        return {"status": "ok", "graph_name": graph_name, "message": "컬렉션이 초기화되었습니다"}
    except Exception as e:
        logger.error(f"[graph-rag] delete_collection 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 직접 실행 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("GRAPH_RAG_HOST", "0.0.0.0")
    port = int(os.getenv("GRAPH_RAG_PORT", "8015"))

    logger.info(f"[graph-rag] 서비스 시작: http://{host}:{port}")
    uvicorn.run(
        "graph_rag_service:app",
        host=host,
        port=port,
        reload=False,
        workers=1,
        log_level="info",
    )
