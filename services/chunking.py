import re
from enum import Enum
from typing import Dict, List

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


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chapter: str) -> List[Dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=[
            "\n## ",
            "\n### ",
            "\n\n",
            "\n",
            ". ",
        ],
    )

    chunks = splitter.split_text(text)

    return [
        {
            "content": chunk,
            "metadata": {
                "chapter": chapter,
                "has_math": "$" in chunk or "\\(" in chunk,
            },
        }
        for chunk in chunks
        if chunk.strip()
    ]
