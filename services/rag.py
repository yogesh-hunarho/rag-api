import logging

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


def get_context(vector_store, task: str, k: int = 6) -> str:
    """
    Retrieve context from the vector store using MMR search.
    Includes source attribution via chunk IDs to reduce hallucination.
    """
    query = QUERY_MAP.get(task, "important concepts")
    logger.info(f"MMR search: task={task}, query='{query}', k={k}")

    docs = vector_store.max_marginal_relevance_search(query, k=k)

    context = []
    for d in docs:
        context.append(
            f"[Chunk {d.metadata['chunk_id']}]\n{d.page_content}"
        )

    result = "\n\n".join(context)
    logger.info(f"Retrieved {len(docs)} chunks, total context length: {len(result)} chars")
    return result
