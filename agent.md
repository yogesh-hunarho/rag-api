# 📘 Project Overview

### **AI-Powered CBSE Content Generator (RAG-based, Session-Driven, No DB)**

This project converts **school textbook PDFs** into **teacher-ready educational content** such as:

* Question Papers (with marks & difficulty)
* Answer Keys
* Chapter Summaries
* Student Notes
* Worksheets
* Lesson Plans
* Mind Maps (JSON-ready for UI rendering)

All content is generated **strictly from the uploaded PDF** using **Retrieval-Augmented Generation (RAG)**.
---

## 🎯 Core Problem We Solve

Teachers face:

* Time-consuming manual paper creation
* Inconsistent difficulty & marking schemes
* Repetitive work for summaries, worksheets, notes
* No structured digital output for UI tools

### ✅ Our Solution

A **session-based AI pipeline** that:

* Accepts a PDF once
* Reuses embeddings efficiently
* Generates **multiple types of outputs**
* Returns **strict JSON** usable by frontend tools
* Cleans itself automatically to control cost & storage

---

# 🧠 High-Level Architecture

```
Teacher (Frontend)
        |
        v
FastAPI Backend
        |
        v
Session Manager (UUID)
        |
        v
PDF → Text → Chunking
        |
        v
Embeddings (FAISS)
        |
        v
LLM (RAG prompts)
        |
        v
JSON Outputs (Saved per session)
```

---

# 🔁 Project Flow (Step-by-Step)

## 1️⃣ Session Creation (Multi-User Safe)

**Why?**

* No DB
* No login
* Full isolation per teacher

**What happens:**

* Backend generates a `session_id` (UUID)
* Creates folder:

```
tmp/sessions/{session_id}/
```

This `session_id` is used for **all future API calls**.

---

## 2️⃣ PDF Upload & Extraction

**Teacher uploads PDF**

Backend:

* Extracts text from PDF
* Normalizes encoding (important!)
* Saves:

```
chapter.txt
meta.json
```

> ❗ We don’t trust PDFs — encoding issues are handled safely.

---

## 3️⃣ Chunking (Optimized Per Content Type)

We **don’t chunk once for everything**.

| Content Type   | Chunk Size | Overlap | Reason                    |
| -------------- | ---------- | ------- | ------------------------- |
| Question Paper | 800–1000   | 150     | Needs conceptual coverage |
| Summary        | 1200–1500  | 200     | Needs flow                |
| Student Notes  | 600–800    | 120     | Bullet clarity            |
| Worksheet      | 500–700    | 100     | Precise recall            |
| Lesson Plan    | 1000–1200  | 150     | Structure & sequence      |

Chunks are stored **once per session**.

---

## 4️⃣ Embeddings (Cost Optimized)

**Libraries Used**

* `sentence-transformers`
* `FAISS`

**Key Design Decision**

* Embeddings are created **only once**
* Reused across:
  * question paper
  * answer key
  * summary
  * worksheet
  * lesson plan
💰 **Huge cost saving**
---

## 5️⃣ RAG (Retrieval-Augmented Generation)

Each API:
1. Retrieves top-K relevant chunks
2. Injects them into a **strict prompt**
3. Calls the LLM
4. Validates JSON output
5. Saves result

### Example:

```
Context (from PDF)
+ Prompt Rules
+ Teacher Controls (class, subject, difficulty)
→ JSON Output
```
---

## 6️⃣ Question Paper Generation (Core Feature)

### Teacher Controls:

* Class (6–12)
* Subject
* Difficulty (easy / medium / hard)
* Marks distribution

### Output:

```json
{
  "mcq": [...],
  "short": [...],
  "long": [...]
}
```

---

## 7️⃣ Answer Key Generation

**Important Design Choice**

Answer key is:

* Generated **after** question paper
* Uses:
  * Question JSON
  * Same RAG context

This ensures:

* No hallucination
* Answers align exactly with questions

---

## 8️⃣ Multiple Content APIs (Same PDF)

From the **same session**, teacher can generate:

* `/summary`
* `/student_notes`
* `/worksheet`
* `/lesson_plan`
* `/mindmap`

⚡ No re-upload
⚡ No re-embedding
⚡ Fast response

---

## 9️⃣ Storage & Cost Control (Critical)

### ❌ What we DON’T do

* No MongoDB
* No MySQL
* No permanent vector DB
* No infinite storage

### ✅ What we DO

* Session-scoped storage only
* Max size per session
* Manual delete API:
```
DELETE /session/{session_id}
```
After deletion:

* All chunks
* All embeddings
* All outputs
  are removed

📉 Keeps storage < 2GB
📉 Keeps cloud cost low

---

## 🔐 Multi-User Isolation

Each teacher:

```
tmp/sessions/{uuid}/
```

* No cross-session access
* No shared embeddings
* No data leakage

UUID = security boundary

---

# 📚 Libraries & Why We Use Them

| Library               | Purpose                   |
| --------------------- | ------------------------- |
| FastAPI               | High-performance API      |
| LangChain (light use) | RAG utilities             |
| FAISS                 | Vector search             |
| Sentence Transformers | Embeddings                |
| UUID                  | Session isolation         |
| ReportLab (optional)  | PDF export                |
| Pydantic              | Input validation (not DB) |
| Python stdlib         | File-based persistence    |

---

## ❓ Why No Database?

**Because:**

* Teachers regenerate content rarely
* Data is disposable
* Storage must be cheap
* System must scale horizontally

👉 UUID + filesystem = simplest & fastest

---

# 🧠 Key Engineering Principles (Explain This)

* **RAG over fine-tuning**
* **Session-based architecture**
* **Cost-aware embeddings**
* **Strict JSON contracts**
* **Teacher-in-control AI**
* **Stateless backend**

---

## 🧩 What Makes This Project Strong

✔ Production-ready thinking
✔ Cost optimized
✔ Scalable
✔ Safe for education
✔ UI-friendly JSON
✔ No vendor lock-in

---

## 🏁 One-Line Pitch (Use This)

> “We built a session-based RAG system that converts CBSE textbooks into structured, teacher-controlled educational content with zero permanent storage and optimized AI cost.” below my code

main.py
from fastapi import FastAPI
from api.session import router as session_router
from api.generate import router as generate_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

app = FastAPI(title="Paper Generator", version="1.0.0", description="NCERT Paper Generator", docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

app.include_router(session_router, prefix="/session")
app.include_router(generate_router, prefix="/generate")

<!-- generate.py -->
from schemas.paper_blueprint import PaperBlueprint
from fastapi import APIRouter, HTTPException
from services.chunking import ContentType, chunk_text
from services.vector_store import get_or_create_store
from services.rag import get_context
from services.prompts import *
from services.llm import get_llm
import json, os

router = APIRouter()

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

<!-- llm.py -->
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        response_mime_type="application/json"
    )

<!-- rag.py -->
def get_context(vector_store, k: int = 6):
    docs = vector_store.similarity_search("NCERT content", k=k)
    return "\n".join(d.page_content for d in docs)

<!-- verctor_store.py -->
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from utils.embeddings import get_embeddings

def get_or_create_store(session_id: str, chunks):
    path = f"tmp/sessions/{session_id}/vector_store"

    if os.path.exists(path):
        return FAISS.load_local(path, get_embeddings(), allow_dangerous_deserialization=True)

    db = FAISS.from_texts(chunks, get_embeddings())
    db.save_local(path)
    return db

<!-- chunking.py -->
import re
from enum import Enum
from langchain_text_splitters import RecursiveCharacterTextSplitter

class ContentType(str, Enum):
    question_paper = "question_paper"

def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def create_chunks_with_overlap(text, max_words=120, overlap_sentences=2):
    sentences = split_into_sentences(text)
    chunks = []
    current_chunk = []
    current_word_count = 0

    for sentence in sentences:
        words = sentence.split()
        word_count = len(words)

        if current_word_count + word_count > max_words:
            chunks.append(\" \".join(current_chunk))
            overlap = current_chunk[-overlap_sentences:] if overlap_sentences > 0 else []
            current_chunk = overlap + [sentence]
            current_word_count = sum(len(s.split()) for s in current_chunk)
        else:
            current_chunk.append(sentence)
            current_word_count += word_count

    if current_chunk:
        chunks.append(\" \".join(current_chunk))

    return chunks

<!-- file_parser.py -->
import docx
import pymupdf4llm
import pymupdf

def extract_text(file):
    name = file.filename.lower()

    if name.endswith(".pdf"):
        doc = pymupdf.open(stream=file.file.read(), filetype="pdf")
        try:
            return pymupdf4llm.to_markdown(doc)
        finally:
            doc.close()

    if name.endswith(".docx"):
        d = docx.Document(file.file)
        return "\n".join(p.text for p in d.paragraphs)

    if name.endswith(".txt"):
        return file.file.read().decode("utf-8")

    raise ValueError("Unsupported file")

<!-- session.py -->
from fastapi import APIRouter, UploadFile, HTTPException
from uuid import uuid4
import os, json, time, shutil
from utils.file_parser import extract_text

router = APIRouter()
BASE = "tmp/sessions"

@router.post("/start")
def start_session():
    session_id = str(uuid4())
    path = os.path.join(BASE, session_id)
    os.makedirs(path)

    meta = {
        "session_id": session_id,
        "created_at": int(time.time())
    }

    with open(os.path.join(path, "meta.json"), "w") as f:
        json.dump(meta, f)

    return {"session_id": session_id}


@router.post("/{session_id}/upload")
def upload_chapter(session_id: str, file: UploadFile):
    base = os.path.join(BASE, session_id)
    if not os.path.exists(base):
        raise HTTPException(404, "Invalid session")

    chapter_path = os.path.join(base, "chapter.txt")
    if os.path.exists(chapter_path):
        raise HTTPException(400, "Chapter already uploaded")

    text = extract_text(file)
    with open(chapter_path, "w", encoding="utf-8") as f:
        f.write(text)

    return {"status": "uploaded"}


@router.delete("/{session_id}")
def delete_session(session_id: str):
    path = os.path.join(BASE, session_id)
    if not os.path.exists(path):
        raise HTTPException(404, "Session not found")

    shutil.rmtree(path)
    return {"status": "deleted"}

<!-- prompts.py -->
QUESTION_PAPER_PROMPT ="""
You are a CBSE/NCERT exam paper setter.
DIFFICULTY RULES (STRICT):
- easy: direct definition, one-line fact, naming
- medium: explanation using 2–3 sentences from text
- hard: reasoning or comparison explicitly present in text

ABSOLUTE RULES (NO EXCEPTIONS):
- Use ONLY exact words, phrases, or sentences copied from the Chapter Text
- Do NOT paraphrase
- Do NOT summarize
- Do NOT introduce synonyms
- Do NOT use prior knowledge
- If an answer sentence is not present verbatim, DO NOT generate the question
- Match the marks blueprint EXACTLY
- Follow question counts EXACTLY
- JSON output ONLY
- NO extra keys
- NO wrapper objects
- NO comments
- NO trailing commas
- NO markdown

MATH RULES:
- For mathematics, represent equations using LaTeX
- LaTeX must be compatible with KaTeX
- Do NOT invent formulas
- Use ONLY formulas present in the text

FIGURE HANDLING (MANDATORY):
- If a question refers to any diagram, experiment, or illustration:
  - Set "figure_reference": "Fig. X"
- If figure number is mentioned in text, copy it exactly
- If no figure is referenced, set null

QUESTION TYPE RULES:

MCQ:
- Exactly 4 options
- ALL options must be copied EXACTLY from the text
- One and only one correct option
- Provide "correct_index"

Fill in the blanks:
- Remove EXACTLY ONE word or phrase
- The removed text must exist verbatim in the chapter

Short / Long Answer:
- Question sentence MUST match one of these patterns AND exist in text:
  - "Define ..."
  - "What is ..."
  - "Explain ..."
  - "Write ..."
  - "Name ..."
- Answer MUST be copied verbatim from the chapter text
- Multi-sentence answers must preserve original order

MARKS BLUEPRINT (STRICT):
{marks_json}

OUTPUT JSON FORMAT (STRICT — DO NOT CHANGE):
{{
  "mcq": [
    {{
      "question": "",
      "options": ["", "", "", ""],
      "correct_index": 0,
      "marks": 1,
      "difficulty": "easy",
      "figure_reference": null
    }}
  ],
  "fill_in_the_blanks": [
    {{
      "question": "",
      "answer": "",
      "figure_reference": null,
      "marks": 1,
      "difficulty": "easy",
    }}
  ],
  "short_answer": [
    {{
      "question": "",
      "answer": "",
      "figure_reference": null,
      "marks": 1,
      "difficulty": "easy",
    }}
  ],
  "long_answer": [
    {{
      "question": "",
      "answer": "",
      "figure_reference": null,
      "marks": 1,
      "difficulty": "easy",
    }}
  ]
}}

Chapter Text:
{context}
"""
