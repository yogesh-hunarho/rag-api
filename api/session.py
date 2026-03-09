import os
import json
import time
import shutil
import logging
from uuid import uuid4, UUID

from fastapi import APIRouter, UploadFile, HTTPException
from utils.file_parser import extract_text

logger = logging.getLogger(__name__)

router = APIRouter()
BASE = "tmp/sessions"


def _validate_session_id(session_id: str) -> str:
    """Validate that session_id is a proper UUID."""
    try:
        UUID(session_id, version=4)
    except ValueError:
        raise HTTPException(400, "Invalid session ID format")
    return session_id


@router.post("/start")
def start_session():
    session_id = str(uuid4())
    path = os.path.join(BASE, session_id)
    os.makedirs(path)

    meta = {
        "session_id": session_id,
        "created_at": int(time.time()),
    }

    with open(os.path.join(path, "meta.json"), "w") as f:
        json.dump(meta, f)

    logger.info(f"Session started: {session_id}")
    return {"session_id": session_id}


@router.post("/{session_id}/upload")
def upload_chapter(session_id: str, file: UploadFile):
    session_id = _validate_session_id(session_id)
    base = os.path.join(BASE, session_id)

    if not os.path.exists(base):
        raise HTTPException(404, "Invalid session")

    chapter_path = os.path.join(base, "chapter.txt")
    if os.path.exists(chapter_path):
        raise HTTPException(400, "Chapter already uploaded")

    text = extract_text(file)
    with open(chapter_path, "w", encoding="utf-8") as f:
        f.write(text)

    logger.info(f"Chapter uploaded: session={session_id}, file={file.filename}, length={len(text)}")
    return {"status": "uploaded"}


@router.delete("/{session_id}")
def delete_session(session_id: str):
    session_id = _validate_session_id(session_id)
    path = os.path.join(BASE, session_id)

    if not os.path.exists(path):
        raise HTTPException(404, "Session not found")

    shutil.rmtree(path)
    logger.info(f"Session deleted: {session_id}")
    return {"status": "deleted"}
