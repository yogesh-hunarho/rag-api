import json
import logging
import re
from collections import Counter
from typing import Any, Dict, List

from services.keyword_search import keyword_search
from services.reranker import rerank

logger = logging.getLogger(__name__)
SIM_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u0900-\u097F]+")

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

_COVERAGE_TASKS = {
    "question_paper",
    "summary",
    "lesson_plan",
    "only_mcq",
    "only_fill_blank",
    "only_short_question",
    "only_long_question",
    "only_case_base",
    "worksheet",
    "notes",
    "mindmap",
}

_CHAPTER_LEVEL_TASKS = {"mindmap", "summary", "notes", "worksheet", "lesson_plan"}

_CONTEXT_BUDGET_MAP = {
    "mindmap": 70000,
    "summary": 62000,
    "notes": 62000,
    "worksheet": 56000,
    "lesson_plan": 62000,
    "question_paper": 32000,
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _context_char_budget(task: str) -> int:
    return _CONTEXT_BUDGET_MAP.get(task, 26000)


def _estimate_max_chunks_by_budget(rows: List[Dict[str, Any]], task: str) -> int:
    if not rows:
        return 1
    budget = _context_char_budget(task)
    sample = rows[: min(20, len(rows))]
    avg_chunk_chars = sum(len(str(r.get("content", ""))) for r in sample) / max(1, len(sample))
    # Include attribution/header overhead per chunk.
    avg_with_overhead = max(220, int(avg_chunk_chars + 90))
    return max(1, min(len(rows), budget // avg_with_overhead))


def _format_context_with_budget(rows: List[Dict[str, Any]], task: str) -> str:
    budget = _context_char_budget(task)
    parts: List[str] = []
    used = 0

    for i, row in enumerate(rows):
        score = row.get("rerank_score")
        score_text = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
        source = row.get("source", "unknown")
        chunk_id = row.get("chunk_id")
        chunk_ref = f" | id={chunk_id}" if chunk_id is not None else ""
        header = f"[Chunk {i + 1} | source={source}{chunk_ref} | rerank={score_text}]"
        block = f"{header}\n{row.get('content', '')}"

        if parts and (used + len(block) + 2) > budget:
            break
        if not parts and len(block) > budget:
            # Always include at least one chunk even if it alone exceeds budget.
            parts.append(block)
            used += len(block)
            break

        parts.append(block)
        used += len(block) + (2 if parts else 0)

    return "\n\n".join(parts)


def _target_k(task: str, requested_k: int, total_chunks: int) -> int:
    if total_chunks <= 0:
        return requested_k
    if task in _CHAPTER_LEVEL_TASKS:
        ratio_map = {
            "mindmap": 0.90,
            "summary": 0.85,
            "notes": 0.85,
            "worksheet": 0.80,
            "lesson_plan": 0.85,
        }
        ratio = ratio_map.get(task, 0.80)
        adaptive = max(requested_k + 6, int(total_chunks * ratio))
        # Keep a hard cap to prevent very large prompts on huge books.
        return min(max(adaptive, requested_k), min(44, total_chunks))
    if task != "question_paper":
        return min(requested_k, total_chunks)
    # For full paper generation, slightly expand k on long chapters for wider topic coverage.
    adaptive = max(requested_k, requested_k + 4, int(total_chunks * 0.45))
    return min(max(adaptive, requested_k), min(28, total_chunks))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _topic_key(text: str) -> str:
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    for line in lines[:4]:
        if len(line) < 4 or len(line) > 90:
            continue
        if not re.search(r"[A-Za-z\u0900-\u097F]", line):
            continue
        cleaned = re.sub(r"^\d+(?:\s*\.\s*\d+)*\s*", "", line).strip(" -:|")
        if len(cleaned) >= 4:
            return cleaned.lower()
    return "unknown"


def _build_chunk_lookup(chunks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    total = len(chunks)
    for idx, chunk in enumerate(chunks):
        content = str(chunk.get("content", "")).strip()
        if not content:
            continue
        key = _normalize_text(content)
        if key in lookup:
            continue
        chunk_id = _safe_int(chunk.get("id"), idx + 1)
        lookup[key] = {
            "chunk_id": chunk_id,
            "chunk_position": idx + 1,
            "chunk_total": total,
            "topic_key": _topic_key(content),
        }
    return lookup


def _enrich_row_with_lookup(row: Dict[str, Any], lookup: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    key = _normalize_text(str(row.get("content", "")))
    meta = lookup.get(key, {})

    if meta.get("chunk_id") is not None and row.get("chunk_id") is None:
        row["chunk_id"] = meta["chunk_id"]
    if meta.get("chunk_position") is not None and row.get("chunk_position") is None:
        row["chunk_position"] = meta["chunk_position"]
    if meta.get("chunk_total") is not None and row.get("chunk_total") is None:
        row["chunk_total"] = meta["chunk_total"]
    if meta.get("topic_key") and not row.get("topic_key"):
        row["topic_key"] = meta["topic_key"]

    if not row.get("topic_key"):
        row["topic_key"] = _topic_key(row.get("content", ""))
    return row


def _sim_tokens(text: str) -> set[str]:
    return {tok for tok in SIM_TOKEN_RE.findall(text.lower()) if len(tok) > 2}


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _bucket_index(row: Dict[str, Any], bucket_count: int, fallback_index: int) -> int:
    chunk_id = _safe_int(row.get("chunk_id"), 0)
    chunk_total = max(_safe_int(row.get("chunk_total"), 0), 1)
    if chunk_id > 0:
        ratio = min(max((chunk_id - 1) / chunk_total, 0.0), 0.9999)
        return int(ratio * bucket_count)
    return fallback_index % bucket_count


def _select_diverse_chunks(reranked_rows: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    if not reranked_rows:
        return []
    if len(reranked_rows) <= k:
        return reranked_rows

    scores = [float(row.get("rerank_score", 0.0)) for row in reranked_rows]
    min_score, max_score = min(scores), max(scores)
    denom = (max_score - min_score) if max_score > min_score else 1.0

    bucket_count = min(8, max(3, k // 3))
    candidates: List[Dict[str, Any]] = []
    for idx, row in enumerate(reranked_rows):
        row_copy = dict(row)
        row_copy["_score_norm"] = (float(row_copy.get("rerank_score", 0.0)) - min_score) / denom
        row_copy["_tokens"] = _sim_tokens(str(row_copy.get("content", "")))
        row_copy["_bucket"] = _bucket_index(row_copy, bucket_count, idx)
        row_copy["_topic"] = str(row_copy.get("topic_key", "unknown")).strip().lower() or "unknown"
        candidates.append(row_copy)

    selected: List[Dict[str, Any]] = []
    selected_ids: set[int] = set()
    bucket_usage: Counter[int] = Counter()
    topic_usage: Counter[str] = Counter()

    # Pass 1: pick best chunk from each bucket (coverage first).
    for bucket in range(bucket_count):
        if len(selected) >= k:
            break
        bucket_candidates = [
            (i, c) for i, c in enumerate(candidates)
            if i not in selected_ids and c.get("_bucket") == bucket
        ]
        if not bucket_candidates:
            continue
        best_idx, best = max(bucket_candidates, key=lambda item: item[1]["_score_norm"])
        selected.append(best)
        selected_ids.add(best_idx)
        bucket_usage[best["_bucket"]] += 1
        topic_usage[best["_topic"]] += 1

    # Pass 2: greedy MMR-style selection for novelty + topic spread.
    while len(selected) < k and len(selected_ids) < len(candidates):
        best_idx = -1
        best_score = float("-inf")

        for idx, candidate in enumerate(candidates):
            if idx in selected_ids:
                continue

            redundancy = 0.0
            if selected:
                redundancy = max(
                    _jaccard_similarity(candidate["_tokens"], s["_tokens"])
                    for s in selected
                )

            novelty = 1.0 - redundancy
            bucket = candidate["_bucket"]
            topic = candidate["_topic"]

            score = (
                0.60 * candidate["_score_norm"]
                + 0.30 * novelty
                + (0.08 if bucket_usage[bucket] == 0 else 0.0)
                + (0.06 if topic_usage[topic] == 0 and topic != "unknown" else 0.0)
                - (0.05 * bucket_usage[bucket])
                - (0.03 * topic_usage[topic])
            )

            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx < 0:
            break

        chosen = candidates[best_idx]
        selected.append(chosen)
        selected_ids.add(best_idx)
        bucket_usage[chosen["_bucket"]] += 1
        topic_usage[chosen["_topic"]] += 1

    out: List[Dict[str, Any]] = []
    for row in selected[:k]:
        clean = {key: value for key, value in row.items() if not key.startswith("_")}
        out.append(clean)
    return out


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
    target_k = _target_k(task, k, len(chunks))
    logger.info(
        "Context target chunks: task=%s requested_k=%d target_k=%d total_chunks=%d",
        task,
        k,
        target_k,
        len(chunks),
    )
    chunk_lookup = _build_chunk_lookup(chunks)
    keyword_docs = keyword_search(query, chunks, k=max(12, target_k * 4), session_id=session_id) if chunks else []
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
            row = _make_row(
                content=text,
                source="vector",
                vector_rank=idx + 1,
                chunk_id=metadata.get("id"),
                chunk_position=metadata.get("position"),
                chunk_total=metadata.get("total_chunks"),
            )
            combined.append(
                _enrich_row_with_lookup(row, chunk_lookup)
            )
            seen.add(key)

    for chunk in keyword_docs:
        text = str(chunk.get("content", "")).strip()
        if not text:
            continue

        key = _normalize_text(text)
        if key not in seen:
            row = _make_row(
                content=text,
                source=chunk.get("source", "keyword"),
                bm25_score=chunk.get("bm25_score"),
                chunk_id=chunk.get("id"),
            )
            combined.append(_enrich_row_with_lookup(row, chunk_lookup))
            seen.add(key)

    logger.info(f"Merged {len(combined)} unique candidate chunks")

    max_by_budget = _estimate_max_chunks_by_budget(combined, task)
    if max_by_budget < target_k:
        logger.info(
            "Reducing target_k by context budget: task=%s target_k=%d budget_k=%d",
            task,
            target_k,
            max_by_budget,
        )
        target_k = max_by_budget

    # Step 4: Cross-encoder rerank over a larger pool.
    rerank_pool = min(len(combined), max(30, target_k * 4))
    reranked_pool = rerank(query, combined, top_k=rerank_pool, return_scores=True)
    logger.info(f"Reranked to pool size {len(reranked_pool)} (pool_target={rerank_pool})")

    if not reranked_pool:
        reranked_pool = combined[:rerank_pool]

    # Step 5: Coverage-aware final selection.
    if task in _COVERAGE_TASKS:
        reranked_rows = _select_diverse_chunks(reranked_pool, target_k)
        logger.info(
            "Coverage selection: task=%s requested=%d selected=%d unique_chunk_ids=%d",
            task,
            target_k,
            len(reranked_rows),
            len({row.get("chunk_id") for row in reranked_rows if row.get("chunk_id") is not None}),
        )
    else:
        reranked_rows = reranked_pool[:target_k]

    if not reranked_rows:
        reranked_rows = combined[:target_k]

    # Step 6: Format with chunk attribution
    result = _format_context_with_budget(reranked_rows, task)
    logger.info(f"Final context: {len(result)} chars")
    return result
