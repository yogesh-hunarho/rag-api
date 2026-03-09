from sentence_transformers import CrossEncoder

_reranker = None


def get_reranker():
    global _reranker

    if _reranker is None:
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    return _reranker


def preload_reranker():
    """Download and load the reranker model into memory."""
    get_reranker()


def rerank(query, docs, top_k=6):
    model = get_reranker()

    pairs = [[query, d] for d in docs]

    scores = model.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

    return [d for d, _ in ranked[:top_k]]