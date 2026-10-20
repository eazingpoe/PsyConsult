import os
import json
import time
from threading import Lock
from dotenv import load_dotenv
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_milvus import Milvus
from pymilvus import connections
from langchain_core.tools import tool
from .community_kb_config import connection_args, embedding_model, embedding_key

# ==============================================================================
# 修复 pymilvus 2.6.x 与 langchain-milvus 0.3.x 之间的兼容性问题
# ==============================================================================
original_fetch = connections._fetch_handler
def patched_fetch(alias):
    try:
        return original_fetch(alias)
    except Exception:
        from pymilvus.client.connection_manager import ConnectionManager
        mgr = ConnectionManager.get_instance()
        for mc in mgr._registry.values():
            if f"cm-{id(mc.handler)}" == alias:
                return mc.handler
        for mc in mgr._dedicated.values():
            if f"cm-{id(mc.handler)}" == alias:
                return mc.handler
        raise
connections._fetch_handler = patched_fetch
# ==============================================================================

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path, override=False)

_milvus_instance = None
_milvus_lock = Lock()

def _log_elapsed(scope: str, label: str, start: float) -> float:
    now = time.perf_counter()
    print(f"⏱️ [{scope}] {label}: {now - start:.2f}s")
    return now

def _get_embedding_api_key() -> str | None:
    return embedding_key()

def _get_milvus_store():
    global _milvus_instance
    if _milvus_instance is not None:
        return _milvus_instance

    with _milvus_lock:
        if _milvus_instance is not None:
            return _milvus_instance

        api_key = _get_embedding_api_key()
        if not api_key:
            raise RuntimeError(
                "未配置 DashScope embedding key。若聊天模型使用 DeepSeek，请设置 "
                "DASHSCOPE_EMBEDDING_API_KEY 或 EMBEDDING_API_KEY 后再启用向量检索。"
            )

        conn = connection_args()
        milvus_uri = conn["uri"]

        total_start = time.perf_counter()
        step_start = total_start
        print(f"🔌 [Init] 正在连接 Milvus 向量数据库: {milvus_uri}")
        embeddings = DashScopeEmbeddings(
            dashscope_api_key=api_key,
            model=embedding_model()
        )
        step_start = _log_elapsed("milvus:init", "初始化 DashScopeEmbeddings", step_start)

        _milvus_instance = Milvus(
            embedding_function=embeddings,
            connection_args=conn,
            collection_name=os.getenv(
                "MILVUS_COLLECTION_NAME",
                "community_mental_health_docs_v1_0_2",
            ),
            auto_id=True,
            drop_old=False
        )
        _log_elapsed("milvus:init", "创建 Milvus VectorStore", step_start)
        _log_elapsed("milvus:init", "Milvus 向量工具初始化总耗时", total_start)
    return _milvus_instance

@tool
def query_vector_db(query: str) -> str:
    """
    通过 Milvus 语义检索知识文档。

    返回 JSON 格式的检索证据，包括实际文档内容、来源、
    可用元数据及原始检索分数。原始分数不是置信度或概率。
    """
    try:
        total_start = time.perf_counter()
        step_start = total_start
        print(f"🔎 [MilvusTool] query={query[:120]!r}")

        store = _get_milvus_store()
        step_start = _log_elapsed(
            "milvus:tool", "获取 Milvus VectorStore", step_start
        )

        results = store.similarity_search_with_score(query, k=3)
        _log_elapsed(
            "milvus:tool",
            f"similarity_search_with_score rows={len(results)}",
            step_start,
        )

        if not results:
            _log_elapsed("milvus:tool", "向量工具总耗时", total_start)
            return json.dumps(
                {
                    "status": "no_results",
                    "query": query,
                    "evidence": [],
                    "message": "未检索到相关文档，不能据此声称已有知识库证据支持答案。",
                },
                ensure_ascii=False,
            )

        # 只保留明确允许输出的来源元数据。
        # 仅输出文档中实际存在的字段，不推测页码或章节。
        allowed_metadata = (
            "doc_id", "source_ids", "source_url", "source_urls",
            "source_title", "section_path", "review_status", "source_scope",
            "title",
            "page",
            "page_number",
            "section",
            "chunk_id",
            "document_id",
            "url",
            "guideline_source",
            "updated_at",
            "author",
            "publisher",
            "date",
            "doi",
        )

        evidence = []

        for rank, (doc, score) in enumerate(results, start=1):
            metadata = doc.metadata or {}
            raw_source = metadata.get("source")
            source_text = str(raw_source).strip() if raw_source else ""

            if source_text and "://" in source_text:
                display_source = source_text
            elif source_text:
                display_source = (
                    os.path.basename(source_text.rstrip("/")) or source_text
                )
            else:
                display_source = "Unknown"

            public_metadata = {
                key: metadata[key]
                for key in allowed_metadata
                if key in metadata and metadata[key] is not None
            }

            try:
                raw_score = float(score)
            except (TypeError, ValueError):
                raw_score = str(score)

            evidence.append(
                {
                    "rank": rank,
                    "source": display_source,
                    "metadata": public_metadata,
                    "raw_score": raw_score,
                    "content": doc.page_content.strip(),
                }
            )

        _log_elapsed("milvus:tool", "向量工具总耗时", total_start)

        return json.dumps(
            {
                "status": "success",
                "query": query,
                "retrieval": {
                    "backend": "Milvus",
                    "top_k": 3,
                    "score_field": "raw_score",
                    "score_note": (
                        "原始检索分数；其方向和含义取决于向量集合的距离度量"
                        "及检索配置，不代表答案正确概率或置信度。"
                    ),
                },
                "evidence": evidence,
            },
            ensure_ascii=False,
            default=str,
        )

    except Exception as exc:
        print(
            f"❌ [MilvusTool] 检索失败："
            f"{type(exc).__name__}: {exc}"
        )
        return json.dumps(
            {
                "status": "error",
                "query": query,
                "evidence": [],
                "message": "向量检索暂时不可用，当前没有可供本次回答使用的检索证据。",
                "error_type": type(exc).__name__,
            },
            ensure_ascii=False,
        )
