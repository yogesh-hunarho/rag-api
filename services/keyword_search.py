from rank_bm25 import BM25Okapi


_bm25_cache = {}


def keyword_search(query, chunks, k=5, session_id=None):
    """
    BM25 keyword search over raw chunk text.
    Caches the BM25 index per session to avoid rebuilding on every call.
    """
    global _bm25_cache

    if session_id and session_id in _bm25_cache:
        bm25 = _bm25_cache[session_id]
    else:
        corpus = [c["content"].split() for c in chunks]
        bm25 = BM25Okapi(corpus)
        if session_id:
            _bm25_cache[session_id] = bm25

    scores = bm25.get_scores(query.split())
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

    return [chunks[i] for i in top_indices]