from sentence_transformers import CrossEncoder
from typing import Any, Dict, List

_reranker = None


def get_reranker():
    global _reranker

    if _reranker is None:
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    return _reranker


def preload_reranker():
    """Download and load the reranker model into memory."""
    get_reranker()


def _doc_to_text(doc: Any) -> str:
    if isinstance(doc, dict):
        return str(doc.get("content", "")).strip()
    if hasattr(doc, "page_content"):
        return str(doc.page_content).strip()
    return str(doc).strip()


def rerank(query: str, docs: List[Any], top_k: int = 6, return_scores: bool = False):
    if not docs:
        return []

    model = get_reranker()

    normalized_docs = []
    for doc in docs:
        text = _doc_to_text(doc)
        if not text:
            continue
        normalized_docs.append((doc, text))

    if not normalized_docs:
        return []

    # Limit text size per pair to reduce truncation noise and keep inference stable.
    pairs = [[query, text[:3000]] for _, text in normalized_docs]
    scores = model.predict(pairs)

    ranked = sorted(
        zip(normalized_docs, scores),
        key=lambda x: x[1],
        reverse=True
    )[:top_k]

    if not return_scores:
        return [doc for (doc, _), _ in ranked]

    results: List[Dict[str, Any]] = []
    for (doc, text), score in ranked:
        if isinstance(doc, dict):
            row = dict(doc)
            row.setdefault("content", text)
        else:
            row = {"content": text}
        row["rerank_score"] = float(score)
        results.append(row)

    return results
