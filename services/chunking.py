from enum import Enum
from langchain_text_splitters import RecursiveCharacterTextSplitter

class ContentType(str, Enum):
    summary = "summary"
    notes = "notes"
    mindmap = "mindmap"
    worksheet = "worksheet"
    lesson_plan = "lesson_plan",
    question_paper = "question_paper" 

CHUNK_CONFIG = {
    ContentType.summary: (1500, 200),
    ContentType.notes: (1000, 150),
    ContentType.mindmap: (800, 100),
    ContentType.worksheet: (700, 100),
    ContentType.lesson_plan: (1200, 200),
    ContentType.question_paper: (900, 150),
}

def chunk_text(text: str, content_type: ContentType):
    size, overlap = CHUNK_CONFIG[content_type]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
    )
    return splitter.split_text(text)
