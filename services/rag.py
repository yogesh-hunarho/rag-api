import logging
import json
from services.keyword_search import keyword_search
from services.reranker import rerank

logger = logging.getLogger(__name__)

QUERY_MAP = {
    "summary": "main ideas key concepts definitions",
    "notes": "important concepts definitions processes",
    "mindmap": "concept hierarchy main topics subtopics relationships",
    "worksheet": "facts concepts definitions terms",
    "lesson_plan": "learning objectives teaching steps assessment concepts",
    "question_paper": "important facts definitions concepts processes",
    "only_mcq": "important facts definitions key terms",
    "only_fill_blank": "key terms definitions vocabulary concepts",
    "only_short_question": "concepts explanations processes definitions",
    "only_long_question": "detailed explanations processes reasoning comparisons",
    "only_case_base": "real-world applications case studies experiments processes",
}


def get_context(vector_store, task: str, session_id: str, k: int = 6) -> str:
    """
    Hybrid retrieval: Vector MMR + BM25 keyword search → cross-encoder rerank.
    Returns the top-k most relevant chunks as formatted context.
    """
    query = QUERY_MAP.get(task, "important concepts")
    logger.info(f"Hybrid search: task={task}, query='{query}', k={k}")

    # Step 1: Vector search (retrieve k*3 candidates for reranking)
    vector_docs = vector_store.max_marginal_relevance_search(query, k=k * 3)
    logger.info(f"Vector MMR returned {len(vector_docs)} docs")

    # Step 2: BM25 keyword search
    chunks_path = f"tmp/sessions/{session_id}/vector_store/question_paper/chunks.json"

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    keyword_docs = keyword_search(query, chunks, k=k * 3, session_id=session_id)
    logger.info(f"BM25 keyword search returned {len(keyword_docs)} docs")

    # Step 3: Merge + deduplicate
    seen = set()
    combined = []

    for d in vector_docs:
        text = d.page_content
        if text not in seen:
            combined.append(text)
            seen.add(text)

    for c in keyword_docs:
        text = c["content"]
        if text not in seen:
            combined.append(text)
            seen.add(text)

    logger.info(f"Merged {len(combined)} unique candidate chunks")

    # Step 4: Cross-encoder rerank → top k
    combined_docs = rerank(query, combined, top_k=k)
    logger.info(f"Reranked to top {len(combined_docs)} chunks")

    # Step 5: Format with chunk attribution
    context = []
    for i, c in enumerate(combined_docs):
        context.append(f"[Chunk {i}]\n{c}")

    result = "\n\n".join(context)
    logger.info(f"Final context: {len(result)} chars")
    return result
