import json
import os
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from schemas.paper_blueprint import PaperBlueprint
from services.chunking import ContentType, GenerateType, chunk_text
from services.vector_store import get_or_create_store
from services.rag import get_context
from services.prompts import (
    QUESTION_PAPER_PROMPT,
    MCQ_ONLY_PROMPT,
    FILL_BLANK_ONLY_PROMPT,
    SHORT_QUESTION_ONLY_PROMPT,
    LONG_QUESTION_ONLY_PROMPT,
    CASE_BASE_ONLY_PROMPT,
    SUMMARY_PROMPT,
    NOTES_PROMPT,
    MINDMAP_PROMPT,
    WORKSHEET_PROMPT,
    LESSON_PLAN_PROMPT,
)
from services.llm import get_llm, get_llm_for_mindmap, invoke_llm

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared RAG Pipeline
# ---------------------------------------------------------------------------

def _validate_session_id(session_id: str) -> str:
    """Validate that session_id is a proper UUID to prevent path traversal."""
    try:
        UUID(session_id, version=4)
    except ValueError:
        raise HTTPException(400, "Invalid session ID format")
    return session_id


def _load_chapter_text(session_id: str) -> tuple[str, str]:
    """
    Load chapter text for a session.
    Returns (text, base_path).
    Raises HTTPException if session/chapter is missing or empty.
    """
    base = f"tmp/sessions/{session_id}"
    chapter_path = f"{base}/chapter.txt"

    if not os.path.exists(chapter_path):
        raise HTTPException(404, "Chapter not uploaded")

    with open(chapter_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    if not text.strip():
        raise HTTPException(400, "Extracted chapter text is empty")

    return text, base


def _run_rag_pipeline(session_id: str, content_type, k: int = 6) -> tuple[str, str]:
    """
    Run the common RAG pipeline: validate → chunk → vector store → context.
    Returns (context, base_path).
    """
    session_id = _validate_session_id(session_id)
    text, base = _load_chapter_text(session_id)

    content_key = content_type.value if hasattr(content_type, "value") else str(content_type)

    logger.info(f"Pipeline: session={session_id}, type={content_key}, k={k}")

    chunks = chunk_text(text, content_type)
    store = get_or_create_store(session_id, chunks, content_type=content_key)
    context = get_context(store, content_key, k)

    return context, base


def _save_output(base: str, filename: str, content, as_json: bool = True):
    """Save output to the session's outputs directory."""
    out_dir = f"{base}/outputs"
    os.makedirs(out_dir, exist_ok=True)

    filepath = f"{out_dir}/{filename}"
    with open(filepath, "w", encoding="utf-8") as f:
        if as_json:
            json.dump(content, f, ensure_ascii=False, indent=2)
        else:
            f.write(content)

    logger.info(f"Saved output: {filepath}")


# ---------------------------------------------------------------------------
# Prompt & LLM Config Maps
# ---------------------------------------------------------------------------

GENERATE_TYPE_PROMPT_MAP = {
    GenerateType.only_mcq: MCQ_ONLY_PROMPT,
    GenerateType.only_fill_blank: FILL_BLANK_ONLY_PROMPT,
    GenerateType.only_short_question: SHORT_QUESTION_ONLY_PROMPT,
    GenerateType.only_long_question: LONG_QUESTION_ONLY_PROMPT,
    GenerateType.only_case_base: CASE_BASE_ONLY_PROMPT,
    GenerateType.summary: SUMMARY_PROMPT,
    GenerateType.notes: NOTES_PROMPT,
    GenerateType.worksheet: WORKSHEET_PROMPT,
    GenerateType.lesson_plan: LESSON_PLAN_PROMPT,
}

LLM_CONFIG_MAP = {
    GenerateType.only_mcq: {"temperature": 0.2, "top_p": 0.8, "max_tokens": 6000},
    GenerateType.only_fill_blank: {"temperature": 0.1, "top_p": 0.7, "max_tokens": 4000},
    GenerateType.only_short_question: {"temperature": 0.2, "top_p": 0.8, "max_tokens": 6000},
    GenerateType.only_long_question: {"temperature": 0.3, "top_p": 0.9, "max_tokens": 8000},
    GenerateType.only_case_base: {"temperature": 0.3, "top_p": 0.9, "max_tokens": 8000},
    GenerateType.summary: {"temperature": 0.4, "top_p": 0.9, "max_tokens": 4000},
    GenerateType.notes: {"temperature": 0.3, "top_p": 0.85, "max_tokens": 6000},
    GenerateType.worksheet: {"temperature": 0.3, "top_p": 0.9, "max_tokens": 8000},
    GenerateType.lesson_plan: {"temperature": 0.5, "top_p": 0.95, "max_tokens": 8000},
}

# How many chunks to retrieve per content type
K_CONFIG = {
    GenerateType.summary: 8,
    GenerateType.notes: 8,
    GenerateType.only_mcq: 6,
    GenerateType.only_fill_blank: 6,
    GenerateType.only_short_question: 6,
    GenerateType.only_long_question: 6,
    GenerateType.only_case_base: 6,
    GenerateType.worksheet: 6,
    GenerateType.lesson_plan: 8,
}


# ---------------------------------------------------------------------------
# Endpoints (IMPORTANT: specific routes BEFORE dynamic /{question_type})
# ---------------------------------------------------------------------------

@router.post("/question_paper")
def generate_question_paper(session_id: str, blueprint: PaperBlueprint):
    """Generate a structured question paper based on the blueprint."""
    context, base = _run_rag_pipeline(session_id, ContentType.question_paper)

    llm = get_llm()
    prompt = QUESTION_PAPER_PROMPT.format(
        class_=blueprint.class_,
        subject=blueprint.subject,
        difficulty=blueprint.difficulty,
        marks_json=json.dumps(
            {k: v.model_dump() for k, v in blueprint.marks.items()}, indent=2
        ),
        context=context,
    )

    response = invoke_llm(llm, prompt)

    try:
        paper = json.loads(response.content)
    except Exception:
        logger.error(f"Invalid JSON from LLM for question_paper: {response.content[:200]}")
        raise HTTPException(500, "Invalid question paper JSON")

    _save_output(base, "question_paper.json", paper)
    return paper


@router.post("/mindmap")
def generate_mindmap(session_id: str):
    """Generate a Mermaid mindmap from the chapter text."""
    context, base = _run_rag_pipeline(
        session_id, ContentType.question_paper, k=10  # Reuse generic chunking for mindmap
    )

    llm = get_llm_for_mindmap()
    prompt = MINDMAP_PROMPT.format(context=context)

    response = invoke_llm(llm, prompt)

    result = response.content.strip()

    if not result.startswith("mindmap"):
        logger.error(f"Invalid Mermaid output: {result[:200]}")
        raise HTTPException(500, "Invalid Mermaid mindmap generated")

    _save_output(base, "mindmap.md", result, as_json=False)
    return result


@router.post("/{question_type}")
def generate_question_type(question_type: GenerateType, session_id: str):
    """Generate content based on question/content type (MCQ, notes, summary, etc.)."""
    k = K_CONFIG.get(question_type, 6)

    context, base = _run_rag_pipeline(session_id, question_type, k=k)

    config = LLM_CONFIG_MAP[question_type]
    llm = get_llm(
        temperature=config["temperature"],
        top_p=config["top_p"],
        max_tokens=config["max_tokens"],
    )
    prompt = GENERATE_TYPE_PROMPT_MAP[question_type].format(context=context)

    response = invoke_llm(llm, prompt)

    try:
        result = json.loads(response.content)
    except Exception:
        logger.error(f"Invalid JSON from LLM for {question_type.value}: {response.content[:200]}")
        raise HTTPException(500, "LLM returned invalid JSON")

    _save_output(base, f"{question_type.value}.json", result)
    return result