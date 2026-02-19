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
