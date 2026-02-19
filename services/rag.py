def get_context(vector_store, k: int = 6):
    docs = vector_store.similarity_search("NCERT content", k=k)
    return "\n".join(d.page_content for d in docs)
