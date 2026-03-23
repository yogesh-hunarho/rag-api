import json
import logging
import re
from typing import Any, Dict, List

from services.keyword_search import keyword_search
from services.reranker import rerank

logger = logging.getLogger(__name__)

QUERY_MAP = {
    "summary": "chapter main ideas key concepts definitions process cause effect",
    "notes": "important concepts definitions processes formulas and examples from chapter",
    "mindmap": "concept hierarchy chapter topic subtopic relationships dependencies",
    "worksheet": "facts concepts definitions key terms classroom practice",
    "lesson_plan": "learning objectives concept flow teaching sequence assessment checkpoints",
    "question_paper": "exam-worthy concepts definitions reasoning facts formulas with topic and subtopic context",
    "only_mcq": "objective questions key facts definitions terms misconceptions with topic and subtopic",
    "only_fill_blank": "key terms definitions vocabulary formula fragments concept statements",
    "only_short_question": "short answer concepts explanations processes definitions observations",
    "only_long_question": "long answer detailed explanation reasoning comparison derivation process flow",
    "only_case_base": "case based scenarios passage context mixed question types sub questions",
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _load_chunks(chunks_path: str) -> List[Dict[str, Any]]:
    try:
        with open(chunks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [c for c in data if isinstance(c, dict) and c.get("content")]
    except FileNotFoundError:
        logger.warning(f"Chunks file missing: {chunks_path}")
    except Exception as exc:
        logger.warning(f"Failed to load chunks ({chunks_path}): {exc}")
    return []


def _make_row(content: str, source: str, **meta: Any) -> Dict[str, Any]:
    row: Dict[str, Any] = {"content": content, "source": source}
    for key, value in meta.items():
        if value is not None:
            row[key] = value
    return row


def get_context(vector_store, task: str, session_id: str, k: int = 6) -> str:
    """
    Hybrid retrieval: Vector MMR + BM25 keyword search -> cross-encoder rerank.
    Returns the top-k most relevant chunks as formatted context.
    """
    query = QUERY_MAP.get(task, "important concepts")
    logger.info(f"Hybrid search: task={task}, query='{query}', k={k}")

    # Step 1: Vector search (wider candidate pool for better reranking).
    vector_k = max(20, k * 5)
    try:
        vector_docs = vector_store.max_marginal_relevance_search(
            query,
            k=vector_k,
            fetch_k=max(40, vector_k * 2),
        )
    except TypeError:
        # Backward compatibility for vector stores that do not accept fetch_k.
        vector_docs = vector_store.max_marginal_relevance_search(query, k=vector_k)

    logger.info(f"Vector MMR returned {len(vector_docs)} docs")

    # Step 2: BM25 keyword search
    chunks_path = f"tmp/sessions/{session_id}/vector_store/question_paper/chunks.json"
    chunks = _load_chunks(chunks_path)
    keyword_docs = keyword_search(query, chunks, k=max(12, k * 4), session_id=session_id) if chunks else []
    logger.info(f"BM25 keyword search returned {len(keyword_docs)} docs")

    # Step 3: Merge + deduplicate
    seen = set()
    combined: List[Dict[str, Any]] = []

    for idx, doc in enumerate(vector_docs):
        text = str(getattr(doc, "page_content", "")).strip()
        if not text:
            continue

        key = _normalize_text(text)
        if key not in seen:
            metadata = getattr(doc, "metadata", {}) or {}
            combined.append(
                _make_row(
                    content=text,
                    source="vector",
                    vector_rank=idx + 1,
                    chunk_id=metadata.get("id"),
                )
            )
            seen.add(key)

    for chunk in keyword_docs:
        text = str(chunk.get("content", "")).strip()
        if not text:
            continue

        key = _normalize_text(text)
        if key not in seen:
            combined.append(
                _make_row(
                    content=text,
                    source=chunk.get("source", "keyword"),
                    bm25_score=chunk.get("bm25_score"),
                    chunk_id=chunk.get("id"),
                )
            )
            seen.add(key)

    logger.info(f"Merged {len(combined)} unique candidate chunks")

    # Step 4: Cross-encoder rerank -> top k
    reranked_rows = rerank(query, combined, top_k=k, return_scores=True)
    logger.info(f"Reranked to top {len(reranked_rows)} chunks")

    if not reranked_rows:
        reranked_rows = combined[:k]

    # Step 5: Format with chunk attribution
    context = []
    for i, row in enumerate(reranked_rows):
        score = row.get("rerank_score")
        score_text = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
        source = row.get("source", "unknown")
        chunk_id = row.get("chunk_id")
        chunk_ref = f" | id={chunk_id}" if chunk_id is not None else ""
        header = f"[Chunk {i + 1} | source={source}{chunk_ref} | rerank={score_text}]"
        context.append(f"{header}\n{row.get('content', '')}")

    result = "\n\n".join(context)
    logger.info(f"Final context: {len(result)} chars")
    return result
