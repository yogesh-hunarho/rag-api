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
