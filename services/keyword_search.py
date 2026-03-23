from rank_bm25 import BM25Okapi
import re
from typing import Dict, List, Any


_bm25_cache = {}
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u0900-\u097F]+")
STOPWORDS = {
    "the", "is", "are", "was", "were", "to", "of", "and", "in", "on", "for", "with",
    "from", "by", "at", "an", "a", "or", "as", "be", "this", "that", "it", "its",
    "into", "can", "only", "based", "using", "about"
}


def _tokenize(text: str) -> List[str]:
    if not text:
        return []

    raw = TOKEN_RE.findall(text.lower())
    return [tok for tok in raw if len(tok) > 1 and tok not in STOPWORDS]


def keyword_search(query: str, chunks: List[Dict[str, Any]], k: int = 5, session_id: str | None = None):
    """
    BM25 keyword search over raw chunk text.
    Caches the BM25 index per session to avoid rebuilding on every call.
    """
    global _bm25_cache

    chunk_count = len(chunks)
    if chunk_count == 0:
        return []

    if session_id and session_id in _bm25_cache and _bm25_cache[session_id]["count"] == chunk_count:
        bm25 = _bm25_cache[session_id]["bm25"]
    else:
        corpus = [_tokenize(str(c.get("content", ""))) for c in chunks]
        bm25 = BM25Okapi(corpus)
        if session_id:
            _bm25_cache[session_id] = {"bm25": bm25, "count": chunk_count}

    query_tokens = _tokenize(query)
    if not query_tokens:
        query_tokens = query.lower().split()

    scores = bm25.get_scores(query_tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

    results = []
    for i in top_indices:
        chunk = dict(chunks[i])
        chunk["bm25_score"] = float(scores[i])
        chunk["source"] = "keyword"
        results.append(chunk)

    return results
