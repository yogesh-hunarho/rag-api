from enum import Enum
from langchain_text_splitters import RecursiveCharacterTextSplitter

class ContentType(str, Enum):
    question_paper = "question_paper" 
class GenerateType(str, Enum):
    only_mcq = "only_mcq"
    only_fill_blank = "only_fill_blank"
    only_short_question = "only_short_question"
    only_long_question = "only_long_question"
    only_case_base = "only_case_base"

    summary = "summary"
    notes = "notes"
    worksheet = "worksheet"
    lesson_plan = "lesson_plan"

CHUNK_CONFIG = {
    ContentType.question_paper: (900, 150),

    GenerateType.summary: (1500, 200),
    GenerateType.notes: (1000, 150),
    GenerateType.worksheet: (700, 100),
    GenerateType.lesson_plan: (1200, 200),
    GenerateType.only_mcq: (900, 150),
    GenerateType.only_fill_blank: (900, 150),
    GenerateType.only_short_question: (900, 150),
    GenerateType.only_long_question: (900, 150),
    GenerateType.only_case_base: (900, 150),
}

def chunk_text(text: str, content_type: ContentType):
    size, overlap = CHUNK_CONFIG[content_type]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            " ",
        ],
    )

    chunks = splitter.split_text(text)
    return [
        {
            "content": chunk,
            "metadata": {"chunk_id": i},
        }
        for i, chunk in enumerate(chunks)
    ]
