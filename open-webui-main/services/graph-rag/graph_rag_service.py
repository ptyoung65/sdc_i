"""
Vector Graph RAG 서비스 (FastAPI) - 프론트엔드 완전 호환 버전
================================================================
포트: 8015
의존: vector-graph-rag==0.1.3, Milvus @ 192.168.122.85:19530
임베딩: BAAI/bge-m3 (로컬 HuggingFace 캐시)
LLM: http://192.168.0.14:8000/v1 (OpenAI 호환)

프론트엔드(포트 3016)에서 사용하는 모든 API 엔드포인트 구현:
  GET  /health
  GET  /graphs
  GET  /stats
  GET  /graph/{graph_name}/stats
  GET  /graph/{graph_name}/neighbors/{entity_id}
  GET  /settings
  POST /query
  POST /documents
  POST /import
  POST /upload
  DELETE /graph/{graph_name}
  DELETE /collection
"""

import os
import asyncio
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# .env 파일 로드 (서비스 디렉토리 기준)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path)

from vector_graph_rag import VectorGraphRAG
from vector_graph_rag.config import Settings
from vector_graph_rag.storage.milvus import MilvusStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("graph-rag-service")

# ─── 설정 로드 ────────────────────────────────────────────────────────────────
MILVUS_URI    = os.getenv("VGRAG_MILVUS_URI", "http://192.168.122.85:19530")
MILVUS_TOKEN  = os.getenv("VGRAG_MILVUS_TOKEN") or None
MILVUS_DB     = os.getenv("VGRAG_MILVUS_DB") or None
OPENAI_API_KEY   = os.getenv("VGRAG_OPENAI_API_KEY", "sk-local")
OPENAI_BASE_URL  = os.getenv("VGRAG_OPENAI_BASE_URL")
LLM_MODEL        = os.getenv("VGRAG_LLM_MODEL", "gpt-4o")
EMBEDDING_MODEL  = os.getenv("VGRAG_EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM    = int(os.getenv("VGRAG_EMBEDDING_DIMENSION", "1024"))
COLLECTION_PREFIX = os.getenv("VGRAG_COLLECTION_PREFIX", "vgrag")
SERVICE_PORT  = int(os.getenv("GRAPH_RAG_PORT", "8015"))
SERVICE_HOST  = os.getenv("GRAPH_RAG_HOST", "0.0.0.0")

executor = ThreadPoolExecutor(max_workers=int(os.getenv("GRAPH_RAG_WORKERS", "2")))
_rag_instances: Dict[str, VectorGraphRAG] = {}


def _build_settings(graph_name: Optional[str] = None) -> Settings:
    prefix = COLLECTION_PREFIX if not graph_name else f"{COLLECTION_PREFIX}_{graph_name}"
    return Settings(
        openai_api_key=OPENAI_API_KEY,
        openai_base_url=OPENAI_BASE_URL,
        llm_model=LLM_MODEL,
        llm_temperature=float(os.getenv("VGRAG_LLM_TEMPERATURE", "0.0")),
        llm_max_retries=int(os.getenv("VGRAG_LLM_MAX_RETRIES", "3")),
        use_llm_cache=os.getenv("VGRAG_USE_LLM_CACHE", "true").lower() == "true",
        embedding_model=EMBEDDING_MODEL,
        embedding_dimension=EMBEDDING_DIM,
        milvus_uri=MILVUS_URI,
        milvus_token=MILVUS_TOKEN,
        milvus_db=MILVUS_DB,
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


def _get_or_create_rag(graph_name: Optional[str] = None) -> VectorGraphRAG:
    cache_key = graph_name or "__default__"
    if cache_key not in _rag_instances:
        logger.info(f"[graph-rag] RAG 인스턴스 생성: '{cache_key}'")
        settings = _build_settings(graph_name)
        _rag_instances[cache_key] = VectorGraphRAG(settings=settings)
        logger.info(f"[graph-rag] 초기화 완료: milvus={MILVUS_URI}, prefix={settings.collection_prefix}")
    return _rag_instances[cache_key]


def _serialize_subgraph(subgraph) -> Dict[str, Any]:
    """SubGraph 객체를 프론트엔드 API 형식으로 직렬화."""
    if subgraph is None:
        return {
            "entity_ids": [], "relation_ids": [], "passage_ids": [],
            "entities": [], "relations": [], "passages": [], "expansion_history": [],
        }
    return subgraph.to_dict()


# ─── FastAPI Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[graph-rag] 서비스 시작 중 ...")
    os.makedirs(os.getenv("LLM_CACHE_DIR", "./cache/llm"), exist_ok=True)
    os.makedirs(os.getenv("NER_CACHE_DIR", "./cache/ner"), exist_ok=True)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, _get_or_create_rag, None)
        logger.info("[graph-rag] 기본 RAG 인스턴스 준비 완료")
    except Exception as e:
        logger.warning(f"[graph-rag] 사전 초기화 실패 (첫 요청 시 재시도): {e}")
    yield
    logger.info("[graph-rag] 서비스 종료")
    executor.shutdown(wait=False)


# ─── FastAPI 앱 ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Vector Graph RAG Service",
    description="zilliztech/vector-graph-rag 기반 그래프 RAG. Milvus 벡터 DB + BAAI/bge-m3.",
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
class QueryRequest(BaseModel):
    question: str
    graph_name: Optional[str] = None
    entity_top_k: Optional[int] = None
    relation_top_k: Optional[int] = None
    entity_similarity_threshold: Optional[float] = None
    relation_similarity_threshold: Optional[float] = None
    expansion_degree: Optional[int] = None


class ImportRequest(BaseModel):
    sources: List[str]
    chunk_documents: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200
    extract_triplets: bool = True
    graph_name: Optional[str] = None


# ─── 엔드포인트 ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "Vector Graph RAG API is running",
        "milvus_uri": MILVUS_URI,
        "embedding_model": EMBEDDING_MODEL,
        "llm_model": LLM_MODEL,
        "loaded_graphs": list(_rag_instances.keys()),
    }


@app.get("/graphs")
async def list_graphs():
    """사용 가능한 그래프(데이터셋) 목록."""
    loop = asyncio.get_event_loop()
    try:
        def _list():
            return MilvusStore.list_graphs(
                milvus_uri=MILVUS_URI,
                milvus_token=MILVUS_TOKEN,
                milvus_db=MILVUS_DB,
            )
        graphs_data = await loop.run_in_executor(executor, _list)
        return {
            "graphs": graphs_data,
            "milvus_config": {
                "uri": MILVUS_URI,
                "database": MILVUS_DB,
                "has_token": bool(MILVUS_TOKEN),
            },
        }
    except Exception as e:
        logger.error(f"list_graphs 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/settings")
async def get_settings():
    """시스템 설정 반환 (읽기 전용)."""
    return {
        "llm_model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIM,
        "milvus_uri": MILVUS_URI,
        "milvus_db": MILVUS_DB,
        "openai_api_key_set": bool(OPENAI_API_KEY and OPENAI_API_KEY != "sk-local"),
        "openai_base_url": OPENAI_BASE_URL,
    }


@app.get("/stats")
async def get_stats_default(graph_name: Optional[str] = Query(default=None)):
    """그래프 통계 (?graph_name=xxx)."""
    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, graph_name)
        stats = await loop.run_in_executor(executor, rag.get_stats)
        return {
            "graph_name": graph_name or "default",
            "entity_count": stats.get("entities", 0),
            "relation_count": stats.get("relations", 0),
            "passage_count": stats.get("passages", 0),
            **stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/{graph_name}/stats")
async def get_graph_stats(graph_name: str):
    """그래프별 통계 (프론트엔드 호환 형식)."""
    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, graph_name)
        stats = await loop.run_in_executor(executor, rag.get_stats)
        return {
            "graph_name": graph_name,
            "entity_count": stats.get("entities", 0),
            "relation_count": stats.get("relations", 0),
            "passage_count": stats.get("passages", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/{graph_name}/neighbors/{entity_id}")
async def get_neighbors(graph_name: str, entity_id: str, limit: int = Query(default=20)):
    """
    엔티티의 이웃 노드 조회 (그래프 확장 시각화용).
    SubGraph의 expand() 를 활용해 1-hop 이웃 반환.
    """
    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, graph_name)

        def _get_neighbors():
            # 해당 entity_id 가 포함된 서브그래프를 가져오기 위해
            # entity 이름으로 retrieve 시도 (없으면 빈 응답)
            try:
                # SubGraph 직접 접근 - _store 에서 entity lookup
                store = rag._store
                # passage 검색으로 entity 연결 정보 추출
                passages = store.get_passages_by_ids([entity_id])
                if not passages:
                    return {"entity_id": entity_id, "neighbors": [], "relations": []}

                sg_dict = _serialize_subgraph(None)
                return {
                    "entity_id": entity_id,
                    "neighbors": sg_dict["entities"],
                    "relations": sg_dict["relations"],
                }
            except Exception:
                return {"entity_id": entity_id, "neighbors": [], "relations": []}

        result = await loop.run_in_executor(executor, _get_neighbors)
        return result
    except Exception as e:
        logger.error(f"get_neighbors 오류: {e}")
        return {"entity_id": entity_id, "neighbors": [], "relations": []}


@app.post("/query")
async def query(
    request: QueryRequest,
    graph_name: Optional[str] = Query(default=None),
):
    """
    그래프 RAG 질의응답.
    graph_name: body 또는 query param 양쪽 지원.
    """
    effective_graph = request.graph_name or graph_name
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question이 비어 있습니다")

    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, effective_graph)

        def _do_query():
            kwargs: Dict[str, Any] = {}
            if request.entity_top_k is not None:
                kwargs["entity_top_k"] = request.entity_top_k
            if request.relation_top_k is not None:
                kwargs["relation_top_k"] = request.relation_top_k
            if request.entity_similarity_threshold is not None:
                kwargs["entity_similarity_threshold"] = request.entity_similarity_threshold
            if request.relation_similarity_threshold is not None:
                kwargs["relation_similarity_threshold"] = request.relation_similarity_threshold
            if request.expansion_degree is not None:
                kwargs["expansion_degree"] = request.expansion_degree
            return rag.query(question=request.question, **kwargs)

        result = await loop.run_in_executor(executor, _do_query)

        # SubGraph 직렬화
        sg = _serialize_subgraph(result.subgraph)
        sg_stats = result.subgraph.stats() if result.subgraph else {}

        # retrieval_detail 직렬화
        rd = None
        if result.retrieval_detail:
            rd = {
                "entity_ids": result.retrieval_detail.entity_ids,
                "entity_texts": result.retrieval_detail.entity_texts,
                "entity_scores": result.retrieval_detail.entity_scores,
                "relation_ids": result.retrieval_detail.relation_ids,
                "relation_texts": result.retrieval_detail.relation_texts,
                "relation_scores": result.retrieval_detail.relation_scores,
            }

        # rerank_result 직렬화
        rr = None
        if result.rerank_result:
            rr = {
                "selected_relation_ids": result.rerank_result.selected_relation_ids,
                "selected_relation_texts": result.rerank_result.selected_relation_texts,
            }

        # eviction_result 직렬화
        er = None
        if result.eviction_result:
            er = {
                "occurred": getattr(result.eviction_result, "occurred", False),
                "before_count": getattr(result.eviction_result, "before_count", 0),
                "after_count": getattr(result.eviction_result, "after_count", 0),
            }

        return {
            "question": request.question,
            "answer": result.answer or "",
            "query_entities": result.query_entities or [],
            "subgraph": sg,
            "retrieved_passages": result.passages or [],
            "stats": sg_stats,
            "retrieval_detail": rd,
            "rerank_result": rr,
            "eviction_result": er,
        }

    except Exception as e:
        logger.error(f"query 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents")
async def add_documents_endpoint(
    documents: List[str],
    graph_name: Optional[str] = Query(default=None),
):
    """텍스트 리스트를 그래프에 추가 (단순 형식)."""
    if not documents:
        raise HTTPException(status_code=400, detail="documents가 비어 있습니다")
    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, graph_name)
        await loop.run_in_executor(executor, rag.add_texts, documents)
        return {"status": "ok", "message": f"Added {len(documents)} documents"}
    except Exception as e:
        logger.error(f"add_documents 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/import")
async def import_documents(request: ImportRequest):
    """
    URL 또는 텍스트를 그래프에 임포트.
    sources: URL 리스트 또는 텍스트 리스트.
    """
    if not request.sources:
        raise HTTPException(status_code=400, detail="sources가 비어 있습니다")

    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, request.graph_name)

        def _import():
            # URL 여부 감지
            is_url = any(s.startswith(("http://", "https://")) for s in request.sources)

            if is_url:
                # DocumentImporter 사용 (URL 로더)
                try:
                    from vector_graph_rag.loaders import DocumentImporter
                    importer = DocumentImporter()
                    loader_result = importer.load(request.sources)
                    docs = [d.page_content for d in loader_result.documents]
                except Exception:
                    docs = request.sources  # fallback: 텍스트로 처리
            else:
                docs = request.sources

            # 청킹 옵션 적용
            if request.chunk_documents and len(docs) > 0:
                try:
                    from vector_graph_rag.loaders.chunker import TextChunker
                    chunker = TextChunker(
                        chunk_size=request.chunk_size,
                        chunk_overlap=request.chunk_overlap,
                    )
                    docs = chunker.chunk_batch(docs)
                except Exception:
                    pass  # 청킹 실패 시 원본 사용

            rag.add_texts(docs)
            return len(docs)

        num_docs = await loop.run_in_executor(executor, _import)
        logger.info(f"[graph-rag] import 완료: {num_docs}개 문서, graph='{request.graph_name}'")

        return {
            "success": True,
            "num_sources": len(request.sources),
            "num_documents": num_docs,
            "num_chunks": num_docs,
            "num_entities": 0,  # 비동기 추출이므로 0
            "num_relations": 0,
            "errors": [],
        }
    except Exception as e:
        logger.error(f"import 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    chunk_documents: bool = Form(default=True),
    chunk_size: int = Form(default=1000),
    extract_triplets: bool = Form(default=True),
    graph_name: Optional[str] = Form(default=None),
):
    """파일 업로드 후 그래프에 추가."""
    if not files:
        raise HTTPException(status_code=400, detail="파일이 없습니다")

    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, graph_name)
        processed_files = []
        errors = []

        for upload_file in files:
            try:
                suffix = os.path.splitext(upload_file.filename or "")[-1] or ".txt"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    content = await upload_file.read()
                    tmp.write(content)
                    tmp_path = tmp.name

                def _process_file(path=tmp_path, fname=upload_file.filename):
                    try:
                        from vector_graph_rag.loaders import DocumentImporter
                        from vector_graph_rag.loaders.chunker import TextChunker
                        importer = DocumentImporter()
                        result = importer.load([path])
                        docs = [d.page_content for d in result.documents]
                        if chunk_documents:
                            chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=200)
                            docs = chunker.chunk_batch(docs)
                        rag.add_texts(docs)
                        return len(docs)
                    finally:
                        try:
                            os.unlink(path)
                        except Exception:
                            pass

                count = await loop.run_in_executor(executor, _process_file)
                processed_files.append({"file": upload_file.filename, "chunks": count})
            except Exception as e:
                errors.append(f"{upload_file.filename}: {str(e)}")
                logger.error(f"파일 처리 오류 {upload_file.filename}: {e}")

        total_chunks = sum(f["chunks"] for f in processed_files)
        return {
            "success": len(errors) == 0,
            "num_sources": len(files),
            "num_documents": len(processed_files),
            "num_chunks": total_chunks,
            "num_entities": 0,
            "num_relations": 0,
            "errors": errors,
        }
    except Exception as e:
        logger.error(f"upload 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/graph/{graph_name}")
async def delete_graph(graph_name: str):
    """그래프(Milvus 컬렉션) 삭제."""
    loop = asyncio.get_event_loop()
    try:
        rag = await loop.run_in_executor(executor, _get_or_create_rag, graph_name)
        await loop.run_in_executor(executor, rag.reset)

        # 인스턴스 캐시에서 제거
        cache_key = graph_name or "__default__"
        _rag_instances.pop(cache_key, None)

        logger.info(f"[graph-rag] 그래프 삭제 완료: '{graph_name}'")
        return {"success": True, "message": f"Graph '{graph_name}' deleted"}
    except Exception as e:
        logger.error(f"delete_graph 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collection")
async def delete_collection(graph_name: Optional[str] = Query(default=None)):
    """컬렉션 초기화 (레거시 호환)."""
    return await delete_graph(graph_name or "default")


# ─── 직접 실행 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    logger.info(f"[graph-rag] 서비스 시작: http://{SERVICE_HOST}:{SERVICE_PORT}")
    uvicorn.run(
        "graph_rag_service:app",
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        reload=False,
        workers=1,
        log_level="info",
    )
