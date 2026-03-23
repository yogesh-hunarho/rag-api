import re
import unicodedata
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
# Split sentences on terminal punctuation with or without spaces.
# Indic OCR often omits spaces after "।" and ".".
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\u0964\u0965])(?:\s+|(?=\S))")
LETTER_RE = re.compile(r"[A-Za-z\u0900-\u097F]")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
UNICODE_ESCAPE_RE = re.compile(r"\\u[0-9a-fA-F]{4}")
ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
MOJIBAKE_MARKERS = ("à¤", "Ã", "Â", "�")


def _text_quality_score(text: str) -> float:
    if not text:
        return float("-inf")

    letters = len(LETTER_RE.findall(text))
    devanagari = len(DEVANAGARI_RE.findall(text))
    escaped = len(UNICODE_ESCAPE_RE.findall(text))
    marker_hits = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
    control_chars = sum(1 for ch in text if ord(ch) < 32 and ch not in ("\n", "\t"))
    return (letters + (0.5 * devanagari)) - (3 * escaped) - (4 * marker_hits) - (2 * control_chars)


def _maybe_decode_unicode_escapes(text: str) -> str:
    if len(UNICODE_ESCAPE_RE.findall(text)) < 3:
        return text

    def repl(match: re.Match[str]) -> str:
        return chr(int(match.group(0)[2:], 16))

    candidate = UNICODE_ESCAPE_RE.sub(repl, text)
    return candidate if _text_quality_score(candidate) > _text_quality_score(text) else text


def _maybe_fix_mojibake(text: str) -> str:
    if not any(marker in text for marker in MOJIBAKE_MARKERS):
        return text

    candidates = [text]
    for source_encoding in ("latin-1", "cp1252"):
        try:
            candidates.append(text.encode(source_encoding).decode("utf-8"))
        except UnicodeError:
            continue

    return max(candidates, key=_text_quality_score)


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _maybe_decode_unicode_escapes(text)
    text = _maybe_fix_mojibake(text)

    text = ZERO_WIDTH_RE.sub("", text)
    text = text.replace("\ufffd", "")
    text = text.replace("\u00a0", " ")
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
