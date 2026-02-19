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

> “We built a session-based RAG system that converts CBSE textbooks into structured, teacher-controlled educational content with zero permanent storage and optimized AI cost.”
