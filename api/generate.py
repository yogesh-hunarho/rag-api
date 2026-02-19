from schemas.paper_blueprint import PaperBlueprint
from fastapi import APIRouter, HTTPException
from services.chunking import ContentType, chunk_text
from services.vector_store import get_or_create_store
from services.rag import get_context
from services.prompts import *
from services.llm import get_llm
import json, os

router = APIRouter()

PROMPT_MAP = {
    ContentType.summary: SUMMARY_PROMPT,
    ContentType.notes: NOTES_PROMPT,
    ContentType.mindmap: MINDMAP_PROMPT,
    ContentType.worksheet: WORKSHEET_PROMPT,
    ContentType.lesson_plan: LESSON_PLAN_PROMPT,
    ContentType.question_paper: QUESTION_PAPER_PROMPT,
}

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
        marks_json=json.dumps(blueprint.marks, indent=2),
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

    # ---------- ANSWER KEY ----------
    answer_prompt = ANSWER_KEY_PROMPT.format(
        paper_json=json.dumps(paper, indent=2),
        context=context
    )

    answer_response = llm.invoke(answer_prompt)

    try:
        answers = json.loads(answer_response.content)
    except Exception:
        raise HTTPException(500, "Invalid answer key JSON")

    with open(f"{out}/answer_key.json", "w", encoding="utf-8") as f:
        json.dump(answers, f, indent=2)

    return {
        "question_paper": paper,
        "answer_key": answers
    }



# POST /generate/question_paper?session_id=UUID
# POST /generate/summary?session_id=UUID
# POST /generate/notes?session_id=UUID
# POST /generate/mindmap?session_id=UUID
# POST /generate/worksheet?session_id=UUID
# POST /generate/lesson_plan?session_id=UUID