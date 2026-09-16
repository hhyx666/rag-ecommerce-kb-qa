"""检索模块:混合检索(BM25 关键词 + 向量语义)→ RRF 融合 → 重排序

这是整个 RAG 系统的核心:在知识库里把和问题最相关的片段找出来。
"""
import chromadb
import jieba
from langchain_chroma import Chroma
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from sqlalchemy.orm import Session

from .. import models
from ..config import CANDIDATE_K, CHROMA_DIR, RERANK_MODEL, RETRIEVE_TOP_K
from .embeddings import get_embeddings

# Chroma 底层客户端(整个进程共用一个,避免多开导致文件锁冲突)
_client = chromadb.PersistentClient(path=CHROMA_DIR)

_stores: dict[int, Chroma] = {}  # kb_id -> 向量库(懒加载)
_bm25: dict[int, BM25Okapi] = {}  # kb_id -> BM25 关键词索引
_bm25_meta: dict[int, tuple[list[int], list[str], list[str]]] = {}
# kb_id -> (切片id列表, 内容列表, 文件名列表)
_reranker: CrossEncoder | None = None


def get_store(kb_id: int) -> Chroma:
    """获取知识库对应的向量库(第一次用时加载)"""
    if kb_id not in _stores:
        _client.get_or_create_collection(name=f"kb_{kb_id}")
        _stores[kb_id] = Chroma(
            client=_client,
            collection_name=f"kb_{kb_id}",
            embedding_function=get_embeddings(),
        )
    return _stores[kb_id]


def get_chroma_client() -> chromadb.PersistentClient:
    """Chroma 底层客户端(删除整个知识库时用)"""
    return _client


def get_reranker() -> CrossEncoder:
    """重排序模型(全局只加载一次)"""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANK_MODEL)
    return _reranker


def invalidate_cache(kb_id: int):
    """文档变动后调用:清掉缓存,下次检索时重建"""
    _stores.pop(kb_id, None)
    _bm25.pop(kb_id, None)
    _bm25_meta.pop(kb_id, None)


def _get_bm25(kb_id: int, db: Session):
    """BM25 关键词索引(首次查询时从数据库构建,之后走缓存)"""
    if kb_id not in _bm25:
        rows = (
            db.query(models.Chunk.id, models.Chunk.content, models.Document.filename)
            .join(models.Document, models.Chunk.document_id == models.Document.id)
            .filter(models.Document.kb_id == kb_id)
            .order_by(models.Chunk.id)
            .all()
        )
        ids = [r[0] for r in rows]
        contents = [r[1] for r in rows]
        filenames = [r[2] for r in rows]
        _bm25_meta[kb_id] = (ids, contents, filenames)
        # 中文要先分词,BM25 才能按词匹配
        _bm25[kb_id] = BM25Okapi([list(jieba.cut(t)) for t in contents])
    return _bm25[kb_id], _bm25_meta[kb_id]


def retrieve(
    kb_id: int, query: str, db: Session, top_k: int = RETRIEVE_TOP_K
) -> list[dict]:
    """完整检索流程:两条路召回 → RRF 融合 → 精排,返回 top_k 个片段"""
    store = get_store(kb_id)

    # 1) 向量语义检索:找"意思相近"的片段
    vec_hits = store.similarity_search_with_relevance_scores(query, k=CANDIDATE_K)

    # 2) BM25 关键词检索:找"包含同样词"的片段(商品型号这类精确词很依赖它)
    bm25, (chunk_ids, contents, filenames) = _get_bm25(kb_id, db)
    bm25_scores = bm25.get_scores(list(jieba.cut(query)))
    bm25_top = sorted(
        range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True
    )[:CANDIDATE_K]

    # 3) RRF 融合:两条路都命中的片段得分叠加,排名更靠前
    rrf: dict[int, dict] = {}
    k = 60
    for rank, (doc, _score) in enumerate(vec_hits):
        chunk_id = int(doc.metadata["chunk_id"])
        item = rrf.setdefault(
            chunk_id,
            {
                "content": doc.page_content,
                "source": doc.metadata.get("filename", "未知文档"),
                "score": 0.0,
            },
        )
        item["score"] += 1 / (k + rank + 1)
    for rank, idx in enumerate(bm25_top):
        chunk_id = chunk_ids[idx]
        item = rrf.setdefault(
            chunk_id,
            {
                "content": contents[idx],
                "source": filenames[idx],
                "score": 0.0,
            },
        )
        item["score"] += 1 / (k + rank + 1)

    candidates = sorted(rrf.values(), key=lambda x: x["score"], reverse=True)
    if not candidates:
        return []

    # 4) 重排序:精排模型对"问题-片段"逐对打分,取最相关的几条
    rerank_scores = get_reranker().predict(
        [(query, c["content"]) for c in candidates]
    )
    for c, s in zip(candidates, rerank_scores):
        c["score"] = round(float(s), 4)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_k]
