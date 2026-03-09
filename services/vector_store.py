import os
import logging
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from utils.embeddings import get_embeddings
import json

logger = logging.getLogger(__name__)

def get_or_create_store(session_id: str, chunks, content_type: str = "default"):
    """
    Get or create a FAISS vector store for a session + content type.
    Different content types use different chunk sizes, so each gets its own store.
    """
    path = f"tmp/sessions/{session_id}/vector_store/{content_type}"

    if os.path.exists(path):
        logger.info(f"Loading existing FAISS store: {path}")
        return FAISS.load_local(path, get_embeddings(), allow_dangerous_deserialization=True)

    logger.info(f"Creating new FAISS store: {path} ({len(chunks)} chunks)")
    docs = [
        Document(page_content=c["content"], metadata=c["metadata"])
        for c in chunks
    ]

    db = FAISS.from_documents(docs, get_embeddings())
    db.save_local(path)

    chunks_path = f"{path}/chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f)
        
    return db
