import os
import json
import time
import shutil
import logging
from uuid import uuid4, UUID

from fastapi import APIRouter, UploadFile, HTTPException
from utils.file_parser import extract_text
from utils.errors import APIError, ErrorCode
from services.chunking import chunk_text, ContentType
from services.vector_store import get_or_create_store
from schemas.responses import SessionStartResponse, UploadResponse, DeleteResponse

logger = logging.getLogger(__name__)

router = APIRouter()
BASE = "tmp/sessions"


def _validate_session_id(session_id: str) -> str:
    """Validate that session_id is a proper UUID."""
    try:
        UUID(session_id, version=4)
    except ValueError:
        raise APIError(400, ErrorCode.INVALID_SESSION, "Invalid session ID format. Must be a valid UUID.")
    return session_id


@router.post("/start", response_model=SessionStartResponse)
def start_session():
    try:
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
        return SessionStartResponse(session_id=session_id)
    except OSError as exc:
        logger.error(f"Failed to create session: {exc}")
        raise APIError(500, ErrorCode.FILE_IO_ERROR, "Failed to create session directory.")


@router.post("/{session_id}/upload", response_model=UploadResponse)
def upload_chapter(session_id: str, file: UploadFile):
    session_id = _validate_session_id(session_id)
    base = os.path.join(BASE, session_id)

    if not os.path.exists(base):
        raise APIError(404, ErrorCode.SESSION_NOT_FOUND, "Session not found. Please start a new session.")

    chapter_path = os.path.join(base, "chapter.txt")
    if os.path.exists(chapter_path):
        raise APIError(400, ErrorCode.FILE_ALREADY_UPLOADED, "Chapter already uploaded for this session.")

    # Validate file type
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in [".pdf", ".docx", ".txt"]):
        raise APIError(
            400, ErrorCode.UNSUPPORTED_FILE,
            "Unsupported file type. Please upload a PDF, DOCX, or TXT file.",
        )

    try:
        text = extract_text(file)
    except ValueError as exc:
        raise APIError(400, ErrorCode.UNSUPPORTED_FILE, str(exc))
    except Exception as exc:
        logger.error(f"File extraction failed: {exc}")
        raise APIError(500, ErrorCode.FILE_IO_ERROR, "Failed to extract text from the uploaded file.")

    if not text.strip():
        raise APIError(400, ErrorCode.CHAPTER_EMPTY, "The uploaded file contains no readable text.")

    try:
        with open(chapter_path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError as exc:
        logger.error(f"Failed to save chapter text: {exc}")
        raise APIError(500, ErrorCode.FILE_IO_ERROR, "Failed to save chapter text.")

    # Create vector store immediately
    try:
        chunks = chunk_text(text, content_type=ContentType.question_paper)
        get_or_create_store(session_id, chunks, content_type="question_paper")
    except Exception as exc:
        logger.error(f"Vector store creation failed: {exc}")
        raise APIError(
            500, ErrorCode.VECTOR_STORE_ERROR,
            "Failed to create vector store from the uploaded chapter. Please try again.",
        )

    logger.info(f"Chapter uploaded: session={session_id}, file={file.filename}, length={len(text)}")
    return UploadResponse()


@router.delete("/{session_id}", response_model=DeleteResponse)
def delete_session(session_id: str):
    session_id = _validate_session_id(session_id)
    path = os.path.join(BASE, session_id)

    if not os.path.exists(path):
        raise APIError(404, ErrorCode.SESSION_NOT_FOUND, "Session not found.")

    try:
        shutil.rmtree(path)
    except OSError as exc:
        logger.error(f"Failed to delete session: {exc}")
        raise APIError(500, ErrorCode.FILE_IO_ERROR, "Failed to delete session.")

    logger.info(f"Session deleted: {session_id}")
    return {"status": "deleted"}
