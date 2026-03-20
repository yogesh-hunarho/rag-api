import re
from enum import Enum
from typing import Dict, List


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


CHUNK_SIZE = 1200
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\u0964\u0965])\s+")
LETTER_RE = re.compile(r"[A-Za-z\u0900-\u097F]")


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x0c", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_signal_text(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 8:
        return False
    letters = len(LETTER_RE.findall(text))
    return letters >= max(3, int(len(compact) * 0.25))


def _split_long_text(text: str, limit: int) -> List[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []

    parts: List[str] = []
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if not sentences:
        sentences = [text]

    current = ""
    for sentence in sentences:
        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            parts.append(current)
            current = ""

        if len(sentence) <= limit:
            current = sentence
            continue

        words = sentence.split()
        if not words:
            for i in range(0, len(sentence), limit):
                part = sentence[i : i + limit].strip()
                if part:
                    parts.append(part)
            continue

        word_acc = ""
        for word in words:
            word_candidate = word if not word_acc else f"{word_acc} {word}"
            if len(word_candidate) <= limit:
                word_acc = word_candidate
            else:
                if word_acc:
                    parts.append(word_acc)
                if len(word) <= limit:
                    word_acc = word
                else:
                    for i in range(0, len(word), limit):
                        slice_part = word[i : i + limit].strip()
                        if slice_part:
                            parts.append(slice_part)
                    word_acc = ""
        if word_acc:
            parts.append(word_acc)

    if current:
        parts.append(current)
    return parts


def chunk_text(text: str, chapter: str) -> List[Dict]:
    _ = chapter

    source = clean_text(text)
    if not source:
        return []

    paragraphs = [p.strip() for p in source.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: List[Dict] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        content = current.strip()
        if content and _is_signal_text(content):
            chunks.append({"id": len(chunks) + 1, "content": content})
        current = ""

    for paragraph in paragraphs:
        for segment in _split_long_text(paragraph, CHUNK_SIZE):
            if not _is_signal_text(segment):
                continue

            candidate = segment if not current else f"{current}\n\n{segment}"
            if len(candidate) <= CHUNK_SIZE:
                current = candidate
            else:
                flush_current()
                current = segment

    flush_current()

    return chunks
