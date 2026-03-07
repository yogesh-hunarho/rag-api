from schemas.paper_blueprint import PaperBlueprint
from fastapi import APIRouter, HTTPException
from services.chunking import ContentType, GenerateType, chunk_text
from services.vector_store import get_or_create_store
from services.rag import get_context
from services.prompts import *
from services.llm import get_llm, get_llm_for_mindmap
import json, os

router = APIRouter()

# PROMPT_MAP = {
#     ContentType.summary: SUMMARY_PROMPT,
#     ContentType.notes: NOTES_PROMPT,
#     ContentType.mindmap: MINDMAP_PROMPT,
#     ContentType.worksheet: WORKSHEET_PROMPT,
#     ContentType.lesson_plan: LESSON_PLAN_PROMPT,
#     ContentType.question_paper: QUESTION_PAPER_PROMPT,
# }

# @router.post("/{content_type}")
# def generate(content_type: ContentType, session_id: str):
#     base = f"tmp/sessions/{session_id}"
#     chapter = f"{base}/chapter.txt"

#     if not os.path.exists(chapter):
#         raise HTTPException(404, "Invalid session or chapter missing")

#     text = open(chapter).read()
#     chunks = chunk_text(text, content_type)
#     store = get_or_create_store(session_id, chunks)
#     context = get_context(store)

#     llm = get_llm()
#     prompt = PROMPT_MAP[content_type].format(context=context)

#     response = llm.invoke(prompt)

#     try:
#         result = json.loads(response.content)
#     except Exception:
#         raise HTTPException(500, "LLM returned invalid JSON")



#     out = f"{base}/outputs"
#     os.makedirs(out, exist_ok=True)

#     with open(f"{out}/{content_type}.json", "w",  encoding="utf-8") as f:
#         json.dump(result, f, ensure_ascii=False, indent=2)

#     return result


    

@router.post("/question_paper")
def generate_question_paper(
    session_id: str,
    blueprint: PaperBlueprint
):
    base = f"tmp/sessions/{session_id}"
    chapter_path = f"{base}/chapter.txt"

    if not os.path.exists(chapter_path):
        raise HTTPException(404, "Chapter not uploaded")

    # Always read text files with explicit encoding (Windows-safe)
    with open(chapter_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    if not text.strip():
        raise HTTPException(400, "Extracted chapter text is empty")


    chunks = chunk_text(text, ContentType.question_paper)
    store = get_or_create_store(session_id, chunks)
    context = get_context(store)

    llm = get_llm()

    prompt = QUESTION_PAPER_PROMPT.format(
        class_=blueprint.class_,
        subject=blueprint.subject,
        difficulty=blueprint.difficulty,
        marks_json=json.dumps({k: v.model_dump() for k, v in blueprint.marks.items()}, indent=2),
        context=context
    )

    paper_response = llm.invoke(prompt)

    try:
        paper = json.loads(paper_response.content)
    except Exception:
        raise HTTPException(500, "Invalid question paper JSON")

    # Save question paper
    out = f"{base}/outputs"
    os.makedirs(out, exist_ok=True)

    with open(f"{out}/question_paper.json", "w", encoding="utf-8") as f:
        json.dump(paper, f, indent=2)

    return paper


GENERATE_TYPE_PROMPT_MAP = {
    GenerateType.only_mcq: MCQ_ONLY_PROMPT,
    GenerateType.only_fill_blank: FILL_BLANK_ONLY_PROMPT,
    GenerateType.only_short_question: SHORT_QUESTION_ONLY_PROMPT,
    GenerateType.only_long_question: LONG_QUESTION_ONLY_PROMPT,
    GenerateType.only_case_base: CASE_BASE_ONLY_PROMPT,
    
    GenerateType.summary: SUMMARY_PROMPT,
    GenerateType.notes: NOTES_PROMPT,
    GenerateType.mindmap: MINDMAP_PROMPT,
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

@router.post("/{question_type}")
def generate_question_type(question_type: GenerateType, session_id: str):
    print("question_type",question_type)
    base = f"tmp/sessions/{session_id}"
    chapter_path = f"{base}/chapter.txt"

    if not os.path.exists(chapter_path):
        raise HTTPException(404, "Chapter not uploaded")

    with open(chapter_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    if not text.strip():
        raise HTTPException(400, "Extracted chapter text is empty")

    chunks = chunk_text(text, question_type)
    store = get_or_create_store(session_id, chunks)
    context = get_context(store)
    
    config = LLM_CONFIG_MAP[question_type]
    llm = get_llm(temperature=config["temperature"], top_p=config["top_p"], max_tokens=config["max_tokens"])
    prompt = GENERATE_TYPE_PROMPT_MAP[question_type].format(context=context)

    response = llm.invoke(prompt)

    try:
        result = json.loads(response.content)
    except Exception:
        raise HTTPException(500, "LLM returned invalid JSON")

    # Save output
    out = f"{base}/outputs"
    os.makedirs(out, exist_ok=True)
    
    with open(f"{out}/context.txt", "w") as f:
        f.write(context)

    with open(f"{out}/{question_type.value}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result



@router.post("/mindmap")
def generate_mindmap(session_id: str):
    base = f"tmp/sessions/{session_id}"
    chapter_path = f"{base}/chapter.txt"

    if not os.path.exists(chapter_path):
        raise HTTPException(404, "Chapter not uploaded")

    with open(chapter_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    if not text.strip():
        raise HTTPException(400, "Extracted chapter text is empty")

    chunks = chunk_text(text, GenerateType.mindmap)
    store = get_or_create_store(session_id, chunks)
    context = get_context(store)

    llm = get_llm_for_mindmap()
    prompt = MINDMAP_PROMPT.format(context=context)

    response = llm.invoke(prompt)

    result = response.content.strip()
    print("result",result)

    if not result.startswith("mindmap"):
        raise HTTPException(500, "Invalid Mermaid mindmap generated")
   
    out = f"{base}/outputs"
    os.makedirs(out, exist_ok=True)

    with open(f"{out}/mindmap.md", "w", encoding="utf-8") as f:
        f.write(result)

    return result