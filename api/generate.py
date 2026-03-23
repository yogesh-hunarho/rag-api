import json
import os
import logging
import re
import csv
import io
from uuid import UUID
from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response
from pydantic import ValidationError

from schemas.paper_blueprint import PaperBlueprint
from services.chunking import ContentType, GenerateType
from services.vector_store import get_or_create_store
from services.rag import get_context
from services.prompts import (
    QUESTION_PAPER_PROMPT,
    MCQ_ONLY_PROMPT,
    FILL_BLANK_ONLY_PROMPT,
    SHORT_QUESTION_ONLY_PROMPT,
    LONG_QUESTION_ONLY_PROMPT,
    CASE_BASE_ONLY_PROMPT,
    SUMMARY_PROMPT,
    NOTES_PROMPT,
    MINDMAP_PROMPT,
    WORKSHEET_PROMPT,
    LESSON_PLAN_PROMPT,
)
from services.llm import get_llm, get_llm_for_mindmap, invoke_llm
from utils.errors import APIError, ErrorCode
from schemas.responses import CSVQuestionRow
from json_repair import repair_json


logger = logging.getLogger(__name__)

router = APIRouter()


def _normalize_mindmap_output(text: str) -> str:
    """Normalize possible fenced Mermaid output to raw 'mindmap' text."""
    content = (text or "").strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
        if content.lower().startswith("mermaid"):
            content = content[len("mermaid"):].strip()
    return content

def _safe_int(value: Any, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_option_text(option: Any) -> str:
    if isinstance(option, str):
        return option.strip()
    if isinstance(option, dict):
        # Prefer human-readable label, then common text keys, then value fallback.
        for key in ("label", "text", "option", "content", "value"):
            val = option.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return str(option).strip()


def _option_value_to_index(options_raw: list[Any], options_text: list[str], value: Any) -> int | None:
    if value is None:
        return None

    # Numeric values can be used directly as indices.
    if isinstance(value, int):
        return value if 0 <= value < len(options_text) else None

    value_str = str(value).strip()
    if not value_str:
        return None

    # Letter mapping like A/B/C/D.
    upper = value_str.upper()
    if len(upper) == 1 and "A" <= upper <= "Z":
        idx = ord(upper) - ord("A")
        if 0 <= idx < len(options_text):
            return idx

    # Try match against structured option "value" fields.
    for idx, option in enumerate(options_raw):
        if isinstance(option, dict):
            opt_val = option.get("value")
            if isinstance(opt_val, str) and opt_val.strip().upper() == upper:
                return idx

    # Try match against option text itself.
    for idx, text in enumerate(options_text):
        if text.strip().upper() == upper:
            return idx

    return None


def _normalize_mcq_item(item: dict[str, Any]) -> dict[str, Any]:
    options_raw = item.get("options") if isinstance(item.get("options"), list) else []
    options_text = [_normalize_option_text(opt) for opt in options_raw]
    options_text = [opt for opt in options_text if opt]

    correct_index = _safe_int(item.get("correct_index"), -1)
    if correct_index < 0 or correct_index >= len(options_text):
        cov = item.get("correct_option_values")
        if not isinstance(cov, list):
            cov = [item.get("correct_option_value")] if item.get("correct_option_value") is not None else []
        resolved = None
        for value in cov:
            resolved = _option_value_to_index(options_raw, options_text, value)
            if resolved is not None:
                break
        correct_index = resolved if resolved is not None else (0 if options_text else -1)

    return {
        "question": str(item.get("question", "")).strip(),
        "options": options_text,
        "correct_index": correct_index,
        "marks": _safe_int(item.get("marks"), 1),
        "figure_reference": item.get("figure_reference"),
        "source_sentence": item.get("source_sentence"),
        "difficulty": str(item.get("difficulty", "easy")).strip() or "easy",
    }


def _normalize_question_item(item: dict[str, Any], marks_default: int) -> dict[str, Any]:
    return {
        "question": str(item.get("question", "")).strip(),
        "answer": str(item.get("answer", "")).strip(),
        "figure_reference": item.get("figure_reference"),
        "marks": _safe_int(item.get("marks"), marks_default),
        "difficulty": str(item.get("difficulty", "easy")).strip() or "easy",
    }


def _normalize_question_paper_payload(payload: Any) -> dict[str, Any]:
    normalized = {
        "mcq": [],
        "fill_in_the_blanks": [],
        "short_question": [],
        "long_question": [],
    }

    # New format: flat CSV-style rows.
    if isinstance(payload, list):
        def _row_get(row: dict[str, Any], keys: list[str], default: Any = None) -> Any:
            value = _pick(row, keys)
            return default if value is None else value

        for row in payload:
            if not isinstance(row, dict):
                continue

            qtype_raw = str(
                _row_get(row, ["Question Type", "question_type", "type"], "")
            ).strip().lower()
            qtype = QUESTION_TYPE_ALIASES.get(qtype_raw, qtype_raw)

            sub_qtype_raw = _row_get(row, ["sub question type", "sub_question_type"])
            sub_qtype = QUESTION_TYPE_ALIASES.get(str(sub_qtype_raw).strip().lower(), None) if sub_qtype_raw else None

            is_case_row = qtype == "case_base_question"
            effective_type = sub_qtype if is_case_row and sub_qtype else qtype

            question_text = str(_row_get(row, ["Question", "question"], "")).strip()
            sub_question_text = str(_row_get(row, ["sub question", "sub_question"], "")).strip()
            if is_case_row and sub_question_text:
                question_text = f"{question_text}\n{sub_question_text}" if question_text else sub_question_text

            answer_text = str(_row_get(row, ["Answer", "answer"], "")).strip()
            difficulty = str(
                _row_get(row, ["Difficulty Level", "difficulty_level", "difficulty"], "easy")
            ).strip() or "easy"
            question_image = _row_get(row, ["Question Image", "question_image", "figure_reference"])

            if effective_type == "mcq":
                options = [
                    _row_get(row, ["Option A", "option_a"]),
                    _row_get(row, ["Option B", "option_b"]),
                    _row_get(row, ["Option C", "option_c"]),
                    _row_get(row, ["Option D", "option_d"]),
                ]
                options = [str(opt).strip() for opt in options if opt is not None and str(opt).strip()]

                correct_option = _row_get(
                    row,
                    ["Correct Option", "correct_option", "correct_option_value", "correct_index"],
                )
                mcq_item = _normalize_mcq_item(
                    {
                        "question": question_text,
                        "options": options,
                        "correct_option_values": [correct_option] if correct_option is not None else [],
                        "marks": 1,
                        "figure_reference": question_image,
                        "source_sentence": _row_get(row, ["Explanation", "explanation"]),
                        "difficulty": difficulty,
                    }
                )
                normalized["mcq"].append(mcq_item)
                continue

            if effective_type == "fill_in_the_blank":
                normalized["fill_in_the_blanks"].append(
                    {
                        "question": question_text,
                        "answer": answer_text,
                        "marks": 1,
                        "difficulty": difficulty,
                    }
                )
                continue

            if effective_type == "short_question":
                normalized["short_question"].append(
                    _normalize_question_item(
                        {
                            "question": question_text,
                            "answer": answer_text,
                            "figure_reference": question_image,
                            "marks": 2,
                            "difficulty": difficulty,
                        },
                        marks_default=2,
                    )
                )
                continue

            if effective_type == "long_question":
                normalized["long_question"].append(
                    _normalize_question_item(
                        {
                            "question": question_text,
                            "answer": answer_text,
                            "figure_reference": question_image,
                            "marks": 5,
                            "difficulty": difficulty,
                        },
                        marks_default=5,
                    )
                )
                continue

        return normalized

    data = payload if isinstance(payload, dict) else {}
    mcq_items = data.get("mcq")
    fill_items = data.get("fill_in_the_blanks")
    short_items = data.get("short_question") if data.get("short_question") is not None else data.get("short_questions")
    long_items = data.get("long_question") if data.get("long_question") is not None else data.get("long_questions")

    if isinstance(mcq_items, list):
        for raw in mcq_items:
            if isinstance(raw, dict):
                normalized["mcq"].append(_normalize_mcq_item(raw))

    if isinstance(fill_items, list):
        for raw in fill_items:
            if isinstance(raw, dict):
                normalized["fill_in_the_blanks"].append(
                    {
                        "question": str(raw.get("question", "")).strip(),
                        "answer": str(raw.get("answer", "")).strip(),
                        "marks": _safe_int(raw.get("marks"), 1),
                        "difficulty": str(raw.get("difficulty", "easy")).strip() or "easy",
                    }
                )

    if isinstance(short_items, list):
        for raw in short_items:
            if isinstance(raw, dict):
                normalized["short_question"].append(_normalize_question_item(raw, marks_default=2))

    if isinstance(long_items, list):
        for raw in long_items:
            if isinstance(raw, dict):
                normalized["long_question"].append(_normalize_question_item(raw, marks_default=5))

    return normalized


def _normalize_question_paper_csv_payload(payload: Any) -> List[Dict[str, Any]]:
    """
    Normalize mixed question-paper payload into flat CSV-row JSON format.
    Accepts:
    - new CSV row list (pass-through normalization),
    - legacy grouped dict with mcq/fill/short/long arrays.
    """
    if isinstance(payload, list):
        rows: List[Dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                rows.append(CSVQuestionRow.model_validate(item).model_dump(by_alias=True))
            except ValidationError:
                # Try best-effort row building even if alias/shape is non-standard.
                rows.append(_build_csv_row(item, default_question_type="short_question"))
        return rows

    data = payload if isinstance(payload, dict) else {}
    rows: List[Dict[str, Any]] = []

    legacy_map = [
        ("mcq", ["mcq", "MCQ", "multiple_choice", "multiple choice questions"]),
        (
            "fill_in_the_blank",
            [
                "fill_in_the_blanks",
                "fill_in_the_blank",
                "fill in the blanks",
                "fill in the blank",
                "fillintheblank",
                "fillintheblanks",
                "fillinTheBlank",
            ],
        ),
        ("short_question", ["short_question", "short_questions", "short answer questions"]),
        ("long_question", ["long_question", "long_questions", "long answer questions"]),
        ("true_false", ["true_false", "true false", "truefalse"]),
        ("numerical_problems", ["numerical_problems", "numerical problems"]),
        ("match_the_column", ["match_the_column", "match the column"]),
        ("very_short_answer_question", ["very_short_answer_question", "very short answer questions"]),
    ]

    for default_type, aliases in legacy_map:
        items = _pick(data, aliases)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            row = _build_csv_row(item, default_question_type=default_type)
            rows.append(row)

    case_items = _pick(
        data,
        [
            "case_base_question",
            "case_base_questions",
            "case_based_question",
            "case_based",
            "case-based / competency-based questions",
        ],
    )
    if isinstance(case_items, list):
        rows.extend(_normalize_case_rows(case_items))

    validated_rows: List[Dict[str, Any]] = []
    for row in rows:
        try:
            validated_rows.append(CSVQuestionRow.model_validate(row).model_dump(by_alias=True))
        except ValidationError as exc:
            logger.warning(f"Dropping invalid question_paper CSV row: {exc}")

    return validated_rows


def _apply_question_paper_blueprint_rules(rows: List[Dict[str, Any]], blueprint: PaperBlueprint) -> List[Dict[str, Any]]:
    """
    Enforce blueprint counts on normalized CSV rows.
    Case-based policy:
    - If case_base_question count <= 0 or missing -> remove case-based rows.
    - If case_base_question count > 0 -> keep up to requested count.
      If none are generated, do not hallucinate a case row.
    """
    supported = {"mcq", "fill_in_the_blank", "short_question", "long_question", "case_base_question"}
    requested_counts: Dict[str, int] = {}

    for raw_key, cfg in blueprint.marks.items():
        qtype = QUESTION_TYPE_ALIASES.get(str(raw_key).strip().lower(), str(raw_key).strip().lower())
        if qtype in supported:
            requested_counts[qtype] = max(int(cfg.count), 0)

    used_counts = {k: 0 for k in supported}
    output: List[Dict[str, Any]] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        qtype = _to_question_type(_pick(row, ["Question Type", "question_type", "type"]), "")
        if qtype not in supported:
            continue

        # If qtype isn't requested in blueprint, skip it.
        if qtype not in requested_counts:
            continue

        # Enforce count ceiling per type.
        limit = requested_counts[qtype]
        if used_counts[qtype] >= limit:
            continue

        output.append(row)
        used_counts[qtype] += 1

    case_requested = requested_counts.get("case_base_question", 0)
    case_generated = used_counts.get("case_base_question", 0)
    if case_requested > 0 and case_generated == 0:
        logger.warning(
            "Blueprint requested case_base_question=%s but none could be generated from context.",
            case_requested,
        )

    return output


CSV_COLUMNS = [
    "Topics Name",
    "Subtopic Name",
    "Question Type",
    "Difficulty Level",
    "Question",
    "sub question type",
    "sub question",
    "Question Image",
    "Option A",
    "Option B",
    "Option C",
    "Option D",
    "Correct Option",
    "Answer",
    "Explanation",
]

CSV_GENERATE_TYPES = {
    GenerateType.only_mcq,
    GenerateType.only_fill_blank,
    GenerateType.only_short_question,
    GenerateType.only_long_question,
    GenerateType.only_case_base,
}

QUESTION_TYPE_BY_GENERATE_TYPE = {
    GenerateType.only_mcq: "mcq",
    GenerateType.only_fill_blank: "fill_in_the_blank",
    GenerateType.only_short_question: "short_question",
    GenerateType.only_long_question: "long_question",
    GenerateType.only_case_base: "case_base_question",
}

QUESTION_TYPE_ALIASES = {
    "only_mcq": "mcq",
    "mcq": "mcq",
    "multiple_choice": "mcq",
    "multiple choice questions": "mcq",
    "fill_blank": "fill_in_the_blank",
    "fill_blanks": "fill_in_the_blank",
    "fill blanks": "fill_in_the_blank",
    "fill_in_blank": "fill_in_the_blank",
    "fill_in_the_blank": "fill_in_the_blank",
    "fill_in_the_blanks": "fill_in_the_blank",
    "fill in the blank": "fill_in_the_blank",
    "fill in the blanks": "fill_in_the_blank",
    "fillintheblank": "fill_in_the_blank",
    "fillintheblanks": "fill_in_the_blank",
    "only_fill_blank": "fill_in_the_blank",
    "short": "short_question",
    "short_answer": "short_question",
    "short_question": "short_question",
    "short answer questions": "short_question",
    "only_short_question": "short_question",
    "very short answer questions": "very_short_answer_question",
    "very_short_answer_question": "very_short_answer_question",
    "long": "long_question",
    "long_answer": "long_question",
    "long_question": "long_question",
    "long answer questions": "long_question",
    "only_long_question": "long_question",
    "case": "case_base_question",
    "case_base": "case_base_question",
    "case_based": "case_base_question",
    "case_base_question": "case_base_question",
    "case_base_questions": "case_base_question",
    "case-based / competency-based questions": "case_base_question",
    "case based / competency based questions": "case_base_question",
    "true false": "true_false",
    "true_false": "true_false",
    "truefalse": "true_false",
    "numerical problems": "numerical_problems",
    "numerical_problem": "numerical_problems",
    "numerical_problems": "numerical_problems",
    "match the column": "match_the_column",
    "match_the_column": "match_the_column",
    "only_case_base": "case_base_question",
}

QUESTION_TYPE_LABELS = {
    "mcq": "Multiple Choice Questions",
    "fill_in_the_blank": "Fill in the blanks",
    "short_question": "Short Answer Questions",
    "very_short_answer_question": "Very Short Answer Questions",
    "long_question": "Long Answer Questions",
    "case_base_question": "Case-Based / Competency-Based Questions",
    "true_false": "True False",
    "numerical_problems": "Numerical Problems",
    "match_the_column": "Match the column",
}

EXPORT_CSV_HEADERS = [
    "Board",
    "Grade",
    "Subject",
    "Chapter Name",
    "Topics Name",
    "Subtopic Name",
    "Question Type",
    "Difficulty Level",
    "Question",
    "sub question type",
    "sub question",
    "Question Image",
    "Option A",
    "Option B",
    "Option C",
    "Option D",
    "Correct Option",
    "Answer",
    "Explanation",
    "Reference",
]


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _canon_key(key: Any) -> str:
    return re.sub(r"[\s_]+", "", str(key)).lower()


def _pick(item: Dict[str, Any], keys: List[str]) -> Any:
    if not isinstance(item, dict):
        return None

    for key in keys:
        if key in item and item.get(key) is not None:
            return item.get(key)

    wanted = {_canon_key(k) for k in keys}
    for key, value in item.items():
        if value is None:
            continue
        if _canon_key(key) in wanted:
            return value
    return None


def _empty_csv_row(question_type: str) -> Dict[str, Any]:
    row = {key: None for key in CSV_COLUMNS}
    row["Question Type"] = question_type
    return row


def _to_question_type(raw: Any, default: str) -> str:
    if raw is None:
        return default
    key = str(raw).strip().lower()
    return QUESTION_TYPE_ALIASES.get(key, default)


def _to_question_type_label(raw: Any) -> str | None:
    if raw is None:
        return None
    raw_text = str(raw).strip()
    if not raw_text:
        return None
    canonical = _to_question_type(raw_text, raw_text.lower())
    return QUESTION_TYPE_LABELS.get(canonical, raw_text)


def _enforce_explanation_rule(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keep Explanation only for:
    - Question Type = mcq or fill_in_the_blank
    - Case-based rows where sub question type = mcq or fill_in_the_blank
    """
    qtype = _to_question_type(_pick(row, ["Question Type", "question_type", "type"]), "")
    sub_qtype = _to_question_type(
        _pick(row, ["sub question type", "sub_question_type"]),
        "",
    )

    allowed = qtype in {"mcq", "fill_in_the_blank"}
    if qtype == "case_base_question":
        allowed = sub_qtype in {"mcq", "fill_in_the_blank"}

    if not allowed:
        row["Explanation"] = None

    return row


def _extract_questions_payload(payload: Dict[str, Any]) -> Any:
    """
    Flexible body parsing for CSV export.
    Accepts:
    - explicit `questions`/`question_paper`/`data` containers
    - top-level grouped payload (`mcq`, `fill_in_the_blanks`, ...)
    - top-level CSV rows list-like under common keys (`rows`, `items`)
    """
    direct = _pick(payload, ["questions", "question_paper", "data", "result", "rows", "items"])
    if direct is not None:
        return direct

    known_question_keys = {
        "mcq",
        "Multiple_Choice_Questions",
        "fill_in_the_blanks",
        "Fill_in_the_blanks",
        "Match_the_column",
        "short_question",
        "short_questions",
        "long_question",
        "long_questions",
        "case_base_question",
        "case_based_question",
        "case_based",
        "true_false",
        "true_or_false",
        "numerical_problems",
        "very_short_answer_questions",
        "diagram_based_questions",
        "match_the_column",
    }

    grouped: Dict[str, Any] = {}
    for key, value in payload.items():
        if _canon_key(key) in {_canon_key(x) for x in known_question_keys}:
            grouped[key] = value

    return grouped if grouped else None


def _extract_export_meta_and_rows(payload: Dict[str, Any]) -> tuple[str, str, str, str, List[Dict[str, Any]]]:
    board = _clean_str(_pick(payload, ["Board", "board"]))
    grade = _clean_str(_pick(payload, ["Grade", "grade"]))
    subject = _clean_str(_pick(payload, ["Subject", "subject"]))
    chapter_name = _clean_str(_pick(payload, ["Chapter Name", "chapter_name", "chapterName"]))

    missing = []
    if not board:
        missing.append("Board")
    if not grade:
        missing.append("Grade")
    if not subject:
        missing.append("Subject")
    if not chapter_name:
        missing.append("Chapter Name")

    if missing:
        raise APIError(
            422,
            ErrorCode.INVALID_PARAM,
            f"Missing required fields: {', '.join(missing)}",
            retry=False,
        )

    question_payload = _extract_questions_payload(payload)
    if question_payload is None:
        raise APIError(
            422,
            ErrorCode.INVALID_PARAM,
            "Question JSON not found. Provide it under `questions` (or `question_paper`/`data`) "
            "or as grouped top-level keys like `mcq`, `fill_in_the_blanks`, etc.",
            retry=False,
        )

    rows = _normalize_question_paper_csv_payload(question_payload)
    if not rows:
        if isinstance(question_payload, dict):
            rows = [_build_csv_row(question_payload, default_question_type="short_question")]
        elif isinstance(question_payload, list):
            rows = [
                _build_csv_row(item, default_question_type="short_question")
                for item in question_payload
                if isinstance(item, dict)
            ]

    rows = [_enforce_explanation_rule(dict(row)) for row in rows]
    return board, grade, subject, chapter_name, rows


def _to_export_line(
    row: Dict[str, Any],
    *,
    board: str,
    grade: str,
    subject: str,
    chapter_name: str,
) -> Dict[str, str]:
    question_type_label = _to_question_type_label(_pick(row, ["Question Type", "question_type", "type"]))
    sub_question_type_label = _to_question_type_label(_pick(row, ["sub question type", "sub_question_type"]))

    return {
        "Board": board,
        "Grade": grade,
        "Subject": subject,
        "Chapter Name": chapter_name,
        "Topics Name": _clean_str(_pick(row, ["Topics Name", "topics_name"])) or "",
        "Subtopic Name": _clean_str(_pick(row, ["Subtopic Name", "subtopic_name"])) or "",
        "Question Type": question_type_label or "",
        "Difficulty Level": _clean_str(_pick(row, ["Difficulty Level", "difficulty_level"])) or "",
        "Question": _clean_str(_pick(row, ["Question", "question"])) or "",
        "sub question type": sub_question_type_label or "",
        "sub question": _clean_str(_pick(row, ["sub question", "sub_question"])) or "",
        "Question Image": _clean_str(_pick(row, ["Question Image", "question_image"])) or "",
        "Option A": _clean_str(_pick(row, ["Option A", "option_a"])) or "",
        "Option B": _clean_str(_pick(row, ["Option B", "option_b"])) or "",
        "Option C": _clean_str(_pick(row, ["Option C", "option_c"])) or "",
        "Option D": _clean_str(_pick(row, ["Option D", "option_d"])) or "",
        "Correct Option": _clean_str(_pick(row, ["Correct Option", "correct_option"])) or "",
        "Answer": _clean_str(_pick(row, ["Answer", "answer"])) or "",
        "Explanation": _clean_str(_pick(row, ["Explanation", "explanation"])) or "",
        "Reference": _clean_str(_pick(row, ["Reference", "reference"])) or "RAG agent",
    }


def _extract_options(item: Dict[str, Any]) -> Dict[str, str | None]:
    direct = {
        "A": _clean_str(_pick(item, ["Option A", "option_a"])),
        "B": _clean_str(_pick(item, ["Option B", "option_b"])),
        "C": _clean_str(_pick(item, ["Option C", "option_c"])),
        "D": _clean_str(_pick(item, ["Option D", "option_d"])),
    }
    if any(direct.values()):
        return direct

    options = item.get("options")
    if not isinstance(options, list):
        return direct

    extracted: List[str] = []
    for opt in options:
        text = _normalize_option_text(opt)
        if text:
            extracted.append(text)

    return {
        "A": extracted[0] if len(extracted) > 0 else None,
        "B": extracted[1] if len(extracted) > 1 else None,
        "C": extracted[2] if len(extracted) > 2 else None,
        "D": extracted[3] if len(extracted) > 3 else None,
    }


def _resolve_correct_option_letter(item: Dict[str, Any], options: Dict[str, str | None]) -> str | None:
    raw = _pick(
        item,
        [
            "Correct Option",
            "correct_option",
            "correct_option_value",
            "correct_index",
            "correctOption",
        ],
    )

    cov = item.get("correct_option_values")
    if raw is None and isinstance(cov, list) and cov:
        raw = cov[0]

    if raw is None:
        return None

    if isinstance(raw, int):
        return chr(ord("A") + raw) if 0 <= raw <= 3 else None

    upper = str(raw).strip().upper()
    if upper in {"A", "B", "C", "D"}:
        return upper

    # Match against option values/text.
    for letter, option in options.items():
        if option and option.strip().upper() == upper:
            return letter

    return None


def _build_csv_row(item: Dict[str, Any], default_question_type: str) -> Dict[str, Any]:
    question_type = _to_question_type(
        _pick(item, ["Question Type", "question_type", "type"]),
        default_question_type,
    )
    row = _empty_csv_row(question_type)

    row["Topics Name"] = _clean_str(_pick(item, ["Topics Name", "topic_name", "topic", "Topic Name"]))
    row["Subtopic Name"] = _clean_str(_pick(item, ["Subtopic Name", "subtopic_name", "subtopic", "Subtopic Name"]))
    row["Difficulty Level"] = _clean_str(_pick(item, ["Difficulty Level", "difficulty_level", "difficulty"]))
    row["Question"] = _clean_str(_pick(item, ["Question", "question", "context", "case_context"]))
    row["sub question type"] = _clean_str(_pick(item, ["sub question type", "sub_question_type"]))
    row["sub question"] = _clean_str(_pick(item, ["sub question", "sub_question"]))
    row["Question Image"] = _clean_str(_pick(item, ["Question Image", "question_image", "figure_reference"]))
    row["Answer"] = _clean_str(_pick(item, ["Answer", "answer"]))
    row["Explanation"] = _clean_str(
        _pick(item, ["Explanation", "explanation", "source_sentence", "rationale"])
    )

    is_mcq = question_type == "mcq"
    if is_mcq:
        options = _extract_options(item)
        row["Option A"] = options["A"]
        row["Option B"] = options["B"]
        row["Option C"] = options["C"]
        row["Option D"] = options["D"]
        row["Correct Option"] = _resolve_correct_option_letter(item, options)

        if not row["Answer"] and row["Correct Option"] in {"A", "B", "C", "D"}:
            row["Answer"] = options[row["Correct Option"]]
    else:
        row["Option A"] = None
        row["Option B"] = None
        row["Option C"] = None
        row["Option D"] = None
        row["Correct Option"] = None

    return _enforce_explanation_rule(row)


def _normalize_case_rows(payload: Any) -> List[Dict[str, Any]]:
    items = payload if isinstance(payload, list) else [payload]
    rows: List[Dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        # If already flat row, normalize directly.
        if "sub question" in item or "sub_question" in item or "Question Type" in item:
            row = _build_csv_row(item, default_question_type="case_base_question")
            row["Question Type"] = "case_base_question"
            if row["sub question"] is None:
                row["sub question"] = row["Question"]
            row["sub question type"] = _to_question_type(
                _pick(item, ["sub question type", "sub_question_type", "question_type", "type"]),
                "short_question",
            )

            if row["sub question type"] == "mcq":
                options = _extract_options(item)
                row["Option A"] = options["A"]
                row["Option B"] = options["B"]
                row["Option C"] = options["C"]
                row["Option D"] = options["D"]
                row["Correct Option"] = _resolve_correct_option_letter(item, options)
                if not row["Answer"] and row["Correct Option"] in {"A", "B", "C", "D"}:
                    row["Answer"] = options[row["Correct Option"]]
            else:
                row["Option A"] = None
                row["Option B"] = None
                row["Option C"] = None
                row["Option D"] = None
                row["Correct Option"] = None
            rows.append(_enforce_explanation_rule(row))
            continue

        case_text = _clean_str(_pick(item, ["context", "case_context", "Question", "question"]))
        case_title = _clean_str(_pick(item, ["case_title", "title"]))
        if not case_text and case_title:
            case_text = case_title
        elif case_title and case_text:
            case_text = f"{case_title}: {case_text}"

        case_topic = _clean_str(_pick(item, ["topic", "topic_name", "Topics Name"]))
        case_subtopic = _clean_str(_pick(item, ["subtopic", "subtopic_name", "Subtopic Name"]))
        sub_questions = item.get("sub_questions") if isinstance(item.get("sub_questions"), list) else []

        for sub in sub_questions:
            if not isinstance(sub, dict):
                continue
            row = _build_csv_row(sub, default_question_type="case_base_question")
            row["Question Type"] = "case_base_question"
            row["Question"] = case_text
            row["Topics Name"] = row["Topics Name"] or case_topic
            row["Subtopic Name"] = row["Subtopic Name"] or case_subtopic
            row["sub question"] = _clean_str(_pick(sub, ["sub question", "sub_question", "question"]))
            row["sub question type"] = _to_question_type(
                _pick(sub, ["sub question type", "sub_question_type", "question_type", "type"]),
                "short_question",
            )

            if row["sub question type"] == "mcq":
                options = _extract_options(sub)
                row["Option A"] = options["A"]
                row["Option B"] = options["B"]
                row["Option C"] = options["C"]
                row["Option D"] = options["D"]
                row["Correct Option"] = _resolve_correct_option_letter(sub, options)
                if not row["Answer"] and row["Correct Option"] in {"A", "B", "C", "D"}:
                    row["Answer"] = options[row["Correct Option"]]
            else:
                row["Option A"] = None
                row["Option B"] = None
                row["Option C"] = None
                row["Option D"] = None
                row["Correct Option"] = None
            rows.append(_enforce_explanation_rule(row))

    return rows


def _normalize_csv_question_payload(question_type: GenerateType, payload: Any) -> List[Dict[str, Any]]:
    default_question_type = QUESTION_TYPE_BY_GENERATE_TYPE[question_type]

    if question_type == GenerateType.only_case_base:
        normalized = _normalize_case_rows(payload)
    else:
        items = payload if isinstance(payload, list) else [payload]
        normalized = [
            _build_csv_row(item, default_question_type=default_question_type)
            for item in items
            if isinstance(item, dict)
        ]

    validated_rows = []
    for row in normalized:
        try:
            validated_rows.append(CSVQuestionRow.model_validate(row).model_dump(by_alias=True))
        except ValidationError as exc:
            logger.warning(f"Dropping invalid CSV question row: {exc}")

    return validated_rows


def _validate_session_id(session_id: str) -> str:
    """Validate that session_id is a proper UUID to prevent path traversal."""
    try:
        UUID(session_id, version=4)
    except ValueError:
        raise APIError(400, ErrorCode.INVALID_SESSION, "Invalid session ID format. Must be a valid UUID.")
    return session_id


def _load_chapter_text(session_id: str) -> tuple[str, str]:
    """
    Load chapter text for a session.
    Returns (text, base_path).
    """
    base = f"tmp/sessions/{session_id}"
    chapter_path = f"{base}/chapter.txt"

    if not os.path.exists(chapter_path):
        raise APIError(404, ErrorCode.CHAPTER_NOT_UPLOADED, "Chapter not uploaded. Please upload a PDF first.")

    try:
        with open(chapter_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError as exc:
        logger.error(f"Failed to read chapter file: {exc}")
        raise APIError(500, ErrorCode.FILE_IO_ERROR, "Failed to read chapter file.")

    if not text.strip():
        raise APIError(400, ErrorCode.CHAPTER_EMPTY, "Extracted chapter text is empty. The PDF may not contain readable text.")

    return text, base


def _run_rag_pipeline(session_id: str, content_type, k: int = 20) -> tuple[str, str]:
    """
    Run the common RAG pipeline: validate → vector store → hybrid retrieval → context.
    Returns (context, base_path).
    """
    session_id = _validate_session_id(session_id)
    text, base = _load_chapter_text(session_id)

    content_key = content_type.value if hasattr(content_type, "value") else str(content_type)

    logger.info(f"Pipeline: session={session_id}, type={content_key}, k={k}")

    try:
        store = get_or_create_store(session_id, None, content_type="question_paper")
    except Exception as exc:
        logger.error(f"Vector store error: {exc}")
        raise APIError(500, ErrorCode.VECTOR_STORE_ERROR, "Failed to load vector store. Try re-uploading the chapter.")

    try:
        context = get_context(store, content_key, session_id, k)
    except FileNotFoundError:
        logger.error(f"Chunks file not found for session {session_id}")
        raise APIError(500, ErrorCode.RETRIEVAL_ERROR, "Chunk data not found. Try re-uploading the chapter.")
    except Exception as exc:
        logger.error(f"Retrieval error: {exc}")
        raise APIError(500, ErrorCode.RETRIEVAL_ERROR, f"Failed during context retrieval: {str(exc)[:100]}")

    return context, base


def _save_output(base: str, filename: str, content, as_json: bool = True):
    """Save output to the session's outputs directory."""
    out_dir = f"{base}/outputs"
    os.makedirs(out_dir, exist_ok=True)

    filepath = f"{out_dir}/{filename}"
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            if as_json:
                json.dump(content, f, ensure_ascii=False, indent=2)
            else:
                f.write(content)
        logger.info(f"Saved output: {filepath}")
    except OSError as exc:
        logger.error(f"Failed to save output: {exc}")
        # Don't fail the request — output is already generated


# ---------------------------------------------------------------------------
# Prompt & LLM Config Maps
# ---------------------------------------------------------------------------

GENERATE_TYPE_PROMPT_MAP = {
    GenerateType.only_mcq: MCQ_ONLY_PROMPT,
    GenerateType.only_fill_blank: FILL_BLANK_ONLY_PROMPT,
    GenerateType.only_short_question: SHORT_QUESTION_ONLY_PROMPT,
    GenerateType.only_long_question: LONG_QUESTION_ONLY_PROMPT,
    GenerateType.only_case_base: CASE_BASE_ONLY_PROMPT,
    GenerateType.summary: SUMMARY_PROMPT,
    GenerateType.notes: NOTES_PROMPT,
    GenerateType.worksheet: WORKSHEET_PROMPT,
    GenerateType.lesson_plan: LESSON_PLAN_PROMPT,
}

LLM_CONFIG_MAP = {
    GenerateType.only_mcq: {"temperature": 0.2, "top_p": 0.8, "max_tokens": 10000},
    GenerateType.only_fill_blank: {"temperature": 0.1, "top_p": 0.7, "max_tokens": 10000},
    GenerateType.only_short_question: {"temperature": 0.2, "top_p": 0.8, "max_tokens": 12000},
    GenerateType.only_long_question: {"temperature": 0.3, "top_p": 0.9, "max_tokens": 12000},
    GenerateType.only_case_base: {"temperature": 0.3, "top_p": 0.9, "max_tokens": 12000},
    GenerateType.summary: {"temperature": 0.4, "top_p": 0.9, "max_tokens": 8000},
    GenerateType.notes: {"temperature": 0.3, "top_p": 0.85, "max_tokens": 8000},
    GenerateType.worksheet: {"temperature": 0.3, "top_p": 0.9, "max_tokens": 8000},
    GenerateType.lesson_plan: {"temperature": 0.5, "top_p": 0.95, "max_tokens": 8000},
}

K_CONFIG = {
    GenerateType.summary: 8,
    GenerateType.notes: 8,
    GenerateType.only_mcq: 6,
    GenerateType.only_fill_blank: 6,
    GenerateType.only_short_question: 6,
    GenerateType.only_long_question: 6,
    GenerateType.only_case_base: 6,
    GenerateType.worksheet: 6,
    GenerateType.lesson_plan: 8,
}


# ---------------------------------------------------------------------------
# Endpoints (IMPORTANT: specific routes BEFORE dynamic /{question_type})
# ---------------------------------------------------------------------------

@router.post("/question_paper", response_model=List[CSVQuestionRow])
def generate_question_paper(session_id: str, blueprint: PaperBlueprint):
    """Generate a structured question paper based on the blueprint."""
    context, base = _run_rag_pipeline(session_id, ContentType.question_paper, k=20)

    llm = get_llm(temperature=0.3, top_p=0.9, max_tokens=12000)
    prompt = QUESTION_PAPER_PROMPT.format(
        class_=blueprint.class_,
        subject=blueprint.subject,
        difficulty=blueprint.difficulty,
        marks_json=json.dumps(
            {k: v.model_dump() for k, v in blueprint.marks.items()}, indent=2
        ),
        context=context,
    )

    response = invoke_llm(llm, prompt)

    try:
        paper = json.loads(response.content)
    except json.JSONDecodeError:
        try:
            repaired = repair_json(response.content)
            paper = json.loads(repaired)
            logger.warning("LLM JSON repaired automatically")
        except Exception:
            logger.error(f"Invalid JSON from LLM: {response.content[:500]}")
            raise APIError(500,ErrorCode.INVALID_LLM_RESPONSE,"AI returned an invalid response for the question paper.",retry=True,)

    paper = _normalize_question_paper_csv_payload(paper)
    paper = _apply_question_paper_blueprint_rules(paper, blueprint)
    try:
        # Validate every row and force alias-based output keys exactly as CSV headers.
        paper = [CSVQuestionRow.model_validate(row).model_dump(by_alias=True) for row in paper]
    except ValidationError as exc:
        logger.error(f"Normalized question paper failed schema validation: {exc}")
        raise APIError(
            500,
            ErrorCode.INVALID_LLM_RESPONSE,
            "AI returned question paper in unsupported format. Please try again.",
            retry=True,
        )

    _save_output(base, "question_paper.json", paper)
    return paper


@router.post("/question_paper/csv")
def export_question_paper_csv(payload: Dict[str, Any]):
    """
    Convert question JSON payload into CSV blob and return as downloadable file.
    Does not save file on disk.
    """
    board, grade, subject, chapter_name, rows = _extract_export_meta_and_rows(payload)

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=EXPORT_CSV_HEADERS, extrasaction="ignore")
    writer.writeheader()

    for row in rows:
        line = _to_export_line(
            row,
            board=board,
            grade=grade,
            subject=subject,
            chapter_name=chapter_name,
        )
        writer.writerow(line)

    csv_data = "\ufeff" + out.getvalue()  # UTF-8 BOM for spreadsheet compatibility
    safe_chapter = re.sub(r"[^A-Za-z0-9._-]+", "_", chapter_name).strip("_") or "chapter"
    filename = f"{safe_chapter}_questions.csv"

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/question_paper/xlsx")
def export_question_paper_xlsx(payload: Dict[str, Any]):
    """
    Convert question JSON payload into XLSX blob and return as downloadable file.
    Does not save file on disk.
    """
    board, grade, subject, chapter_name, rows = _extract_export_meta_and_rows(payload)

    try:
        from openpyxl import Workbook  # type: ignore
    except Exception:
        raise APIError(
            500,
            ErrorCode.FILE_IO_ERROR,
            "XLSX export dependency missing. Install `openpyxl` in the active environment.",
            retry=False,
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Questions"
    ws.append(EXPORT_CSV_HEADERS)

    for row in rows:
        line = _to_export_line(
            row,
            board=board,
            grade=grade,
            subject=subject,
            chapter_name=chapter_name,
        )
        ws.append([line.get(header, "") for header in EXPORT_CSV_HEADERS])

    ws.freeze_panes = "A2"

    out = io.BytesIO()
    wb.save(out)
    xlsx_data = out.getvalue()
    safe_chapter = re.sub(r"[^A-Za-z0-9._-]+", "_", chapter_name).strip("_") or "chapter"
    filename = f"{safe_chapter}_questions.xlsx"

    return Response(
        content=xlsx_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/lesson/mindmap", response_class=PlainTextResponse)
def generate_mindmap(session_id: str):
    """Generate a Mermaid mindmap from the chapter text."""
    context, base = _run_rag_pipeline(session_id, ContentType.question_paper, k=10)

    llm = get_llm_for_mindmap()
    prompt = MINDMAP_PROMPT.format(context=context)

    response = invoke_llm(llm, prompt)

    result = _normalize_mindmap_output(response.content)

    if not result.startswith("mindmap"):
        logger.error(f"Invalid Mermaid output: {result[:200]}")
        raise APIError(
            500, ErrorCode.INVALID_LLM_RESPONSE,
            "AI generated an invalid mindmap. Please try again.",
            retry=True,
        )

    _save_output(base, "mindmap.md", result, as_json=False)
    return PlainTextResponse(content=result, media_type="text/plain; charset=utf-8")


@router.post("/{question_type}")
def generate_question_type(question_type: GenerateType, session_id: str):
    """Generate content based on question/content type (MCQ, notes, summary, etc.)."""
    k = K_CONFIG.get(question_type, 6)

    context, base = _run_rag_pipeline(session_id, question_type, k=k)

    config = LLM_CONFIG_MAP[question_type]
    llm = get_llm(
        temperature=config["temperature"],
        top_p=config["top_p"],
        max_tokens=config["max_tokens"],
    )

    prompt = GENERATE_TYPE_PROMPT_MAP[question_type].format(context=context)
    response = invoke_llm(llm, prompt)

    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        try:
            repaired = repair_json(response.content)
            result = json.loads(repaired)
            logger.warning(f"LLM JSON repaired automatically for {question_type.value}")
        except Exception:
            logger.error(f"Invalid JSON from LLM for {question_type.value}: {response.content[:200]}")
            raise APIError(
                500, ErrorCode.INVALID_LLM_RESPONSE,
                f"AI returned an invalid response for {question_type.value}. Please try again.",
                retry=True,
            )

    if question_type in CSV_GENERATE_TYPES:
        result = _normalize_csv_question_payload(question_type, result)

    _save_output(base, f"{question_type.value}.json", result)
    return result
