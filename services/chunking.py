import re
import logging
from enum import Enum
from typing import List, Dict, Tuple, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LaTeX / Formula Detection Patterns
# ---------------------------------------------------------------------------

INLINE_MATH_RE = re.compile(r"\$(?!\$)(.+?)\$", re.DOTALL)
DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
PAREN_MATH_RE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
BRACKET_MATH_RE = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)

LATEX_COMMAND_RE = re.compile(
    r"\\(?:frac|sqrt|vec|hat|bar|dot|ddot|tilde|overline|underline|"
    r"int|iint|iiint|oint|sum|prod|lim|infty|partial|nabla|"
    r"alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|"
    r"xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|"
    r"Alpha|Beta|Gamma|Delta|Epsilon|Theta|Lambda|Sigma|Phi|Psi|Omega|"
    r"sin|cos|tan|cot|sec|csc|log|ln|exp|"
    r"rightarrow|leftarrow|Rightarrow|Leftarrow|leftrightarrow|"
    r"times|div|pm|mp|cdot|leq|geq|neq|approx|equiv|propto|"
    r"text|mathrm|mathbf|mathit|mathcal|"
    r"begin|end)\b"
)

SUPER_SUB_RE = re.compile(r"[A-Za-z0-9\)]\s*[\^_]\s*(?:\{[^}]+\}|[A-Za-z0-9]+)")
SIMPLE_FORMULA_RE = re.compile(r"[A-Za-z_]\w*\s*=\s*[^,\n]{2,}")
CHEMICAL_ARROW_RE = re.compile(
    r"[A-Za-z0-9₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹\s\+\(\)]+\s*(?:→|⟶|->|\\rightarrow|\\to)\s*"
    r"[A-Za-z0-9₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹\s\+\(\)]+"
)

ALL_MATH_DELIMITERS_RE = re.compile(
    r"(\$\$.+?\$\$|\$(?!\$).+?\$|\\\(.+?\\\)|\\\[.+?\\\])",
    re.DOTALL,
)

FIG_PATTERN = re.compile(r"(Fig\.?\s*\d+(\.\d+)?)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Section header detection — line-start only
# ---------------------------------------------------------------------------

SECTION_HEADER_RE = re.compile(
    r"(?:^|\n)"
    r"("
    r"Chapter\s+\d+[^\n]*"
    r"|Section\s+\d+[^\n]*"
    r"|\d+\.\d+(?:\.\d+)?\s+[^\n]*"
    r"|Example\s+\d+[^\n]*"
    r"|Activity\s+\d+[^\n]*"
    r"|Table\s+\d+[^\n]*"
    r"|[A-Z][A-Z\s]{5,}"
    r")",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Equation explanation block detection (Req #3, #9)
# Lines starting with: where, given, therefore, here, note, such that, etc.
# These MUST stay attached to the preceding formula.
# ---------------------------------------------------------------------------

EQUATION_EXPLANATION_RE = re.compile(
    r"^(?:where|given|here|therefore|thus|hence|so\s+that|such\s+that|"
    r"note\s+that|putting|substituting|on\s+solving|we\s+get|we\s+have|"
    r"this\s+gives|from\s+eq|using\s+eq|from\s+equation|"
    r"and|or)\s*[,:—\-]?\s",
    re.IGNORECASE | re.MULTILINE
)

# ---------------------------------------------------------------------------
# OCR → LaTeX conversion patterns (Req #4)
# ---------------------------------------------------------------------------

# Unicode superscripts/subscripts → LaTeX
_UNICODE_SUPER = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ", "0123456789+-=()n")
_UNICODE_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎", "0123456789+-=()")

# Common OCR mis-readings of math symbols
OCR_MATH_FIXES = [
    # Fractions written as a/b or a÷b
    (re.compile(r"(\w+)\s*/\s*(\w+)(?=\s|$|\))"), r"\\frac{\1}{\2}"),
    # Square root written as √(x) or √x
    (re.compile(r"√\(([^)]+)\)"), r"\\sqrt{\1}"),
    (re.compile(r"√(\w+)"), r"\\sqrt{\1}"),
    # Multiplication signs
    (re.compile(r"\s×\s"), r" \\times "),
    (re.compile(r"\s÷\s"), r" \\div "),
    # Arrows
    (re.compile(r"\s*→\s*"), r" \\rightarrow "),
    (re.compile(r"\s*←\s*"), r" \\leftarrow "),
    # Degree symbol
    (re.compile(r"(\d+)°"), r"\1^{\\circ}"),
    # Plus-minus
    (re.compile(r"±"), r"\\pm "),
    # Infinity
    (re.compile(r"∞"), r"\\infty"),
    # Greek letter names often OCR'd as text
    (re.compile(r"\btheta\b", re.I), r"\\theta"),
    (re.compile(r"\balpha\b", re.I), r"\\alpha"),
    (re.compile(r"\bbeta\b", re.I), r"\\beta"),
    (re.compile(r"\bgamma\b", re.I), r"\\gamma"),
    (re.compile(r"\bdelta\b", re.I), r"\\delta"),
    (re.compile(r"\blambda\b", re.I), r"\\lambda"),
    (re.compile(r"\bsigma\b", re.I), r"\\sigma"),
    (re.compile(r"\bpi\b"), r"\\pi"),
    (re.compile(r"\bomega\b", re.I), r"\\omega"),
]


def _convert_unicode_scripts(text: str) -> str:
    """Convert Unicode superscript/subscript chars to LaTeX ^ and _ notation."""
    # Find runs of superscript characters
    text = re.sub(
        r"([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ]+)",
        lambda m: "^{" + m.group(0).translate(_UNICODE_SUPER) + "}",
        text
    )
    # Find runs of subscript characters
    text = re.sub(
        r"([₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎]+)",
        lambda m: "_{" + m.group(0).translate(_UNICODE_SUB) + "}",
        text
    )
    return text


def convert_ocr_to_latex(text: str) -> str:
    """
    Convert OCR-produced math notation into proper LaTeX (Req #4).
    Handles: Unicode scripts, common symbols, fraction notation, roots, etc.
    Only converts OUTSIDE of existing LaTeX delimiters.
    """
    # Protect existing LaTeX first
    text, math_regions = _protect_math_regions(text)

    # Convert Unicode superscripts/subscripts
    text = _convert_unicode_scripts(text)

    # Apply OCR→LaTeX fixes
    for pattern, replacement in OCR_MATH_FIXES:
        text = pattern.sub(replacement, text)

    # Restore existing LaTeX
    text = _restore_math_regions(text, math_regions)

    return text


# ---------------------------------------------------------------------------
# Table → Markdown conversion (Req #5)
# ---------------------------------------------------------------------------

def convert_tables_to_markdown(text: str) -> str:
    """
    Detect pipe-delimited table rows (from pdfplumber) and convert them
    to proper markdown tables.

    pdfplumber outputs tables as: "col1 | col2 | col3"
    We detect consecutive pipe-delimited lines and format them.
    """
    lines = text.split("\n")
    result = []
    table_buffer = []

    def flush_table():
        if len(table_buffer) < 2:
            # Not a real table, just return as-is
            result.extend(table_buffer)
            return

        # Build markdown table
        for i, row in enumerate(table_buffer):
            cells = [c.strip() for c in row.split("|")]
            md_row = "| " + " | ".join(cells) + " |"
            result.append(md_row)
            if i == 0:
                # Add header separator
                result.append("| " + " | ".join(["---"] * len(cells)) + " |")

    for line in lines:
        stripped = line.strip()
        if "|" in stripped and len(stripped.split("|")) >= 2:
            table_buffer.append(stripped)
        else:
            if table_buffer:
                flush_table()
                table_buffer = []
            result.append(line)

    if table_buffer:
        flush_table()

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Math region protection helpers
# ---------------------------------------------------------------------------

def _protect_math_regions(text: str) -> Tuple[str, List[str]]:
    """Replace math-delimited regions with placeholders."""
    regions = []

    def _replace(match):
        regions.append(match.group(0))
        return f"__MATH_PLACEHOLDER_{len(regions) - 1}__"

    protected = ALL_MATH_DELIMITERS_RE.sub(_replace, text)
    return protected, regions


def _restore_math_regions(text: str, regions: list) -> str:
    """Restore math regions from placeholders."""
    for i, region in enumerate(regions):
        text = text.replace(f"__MATH_PLACEHOLDER_{i}__", region)
    return text


# ---------------------------------------------------------------------------
# Formula detection & extraction (Req #10)
# ---------------------------------------------------------------------------

def detect_formulas(text: str) -> List[str]:
    """Extract all formulas/math expressions from text (deduplicated)."""
    formulas = set()

    for pattern in [DISPLAY_MATH_RE, INLINE_MATH_RE, PAREN_MATH_RE, BRACKET_MATH_RE]:
        for match in pattern.finditer(text):
            formulas.add(match.group(0).strip())

    for match in SUPER_SUB_RE.finditer(text):
        formulas.add(match.group(0).strip())

    for match in SIMPLE_FORMULA_RE.finditer(text):
        formula = match.group(0).strip()
        if len(formula) < 200:
            formulas.add(formula)

    for match in CHEMICAL_ARROW_RE.finditer(text):
        formulas.add(match.group(0).strip())

    return list(formulas)


def has_math_content(text: str) -> bool:
    """Quick check if text contains any STEM formulas."""
    return bool(
        INLINE_MATH_RE.search(text)
        or DISPLAY_MATH_RE.search(text)
        or PAREN_MATH_RE.search(text)
        or BRACKET_MATH_RE.search(text)
        or LATEX_COMMAND_RE.search(text)
        or SUPER_SUB_RE.search(text)
        or CHEMICAL_ARROW_RE.search(text)
    )


# ---------------------------------------------------------------------------
# Step 1: OCR paragraph reconstruction
# ---------------------------------------------------------------------------

def reconstruct_paragraphs(text: str) -> str:
    """
    Merge OCR line-broken text into proper paragraphs.
    Preserves headings, list items, and blank-line paragraph breaks.
    """
    text, math_regions = _protect_math_regions(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    paragraphs = re.split(r"\n\s*\n", text)
    rebuilt = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        lines = para.split("\n")

        if len(lines) == 1:
            rebuilt.append(lines[0].strip())
            continue

        merged_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            is_heading = bool(re.match(
                r"^(?:Chapter\s+\d|Section\s+\d|\d+\.\d+\s+[A-Z]|Example\s+\d|Activity\s+\d|Table\s+\d)",
                line, re.IGNORECASE
            ))
            is_allcaps = bool(re.match(r"^[A-Z][A-Z\s]{5,}$", line))
            is_list_item = bool(re.match(r"^[\•\-\*\d]+[\.\)]\s", line))

            if (is_heading or is_allcaps or is_list_item) and merged_lines:
                rebuilt.append(" ".join(merged_lines))
                merged_lines = [line]
            else:
                merged_lines.append(line)

        if merged_lines:
            rebuilt.append(" ".join(merged_lines))

    result = "\n\n".join(rebuilt)
    result = _restore_math_regions(result, math_regions)
    return result


# ---------------------------------------------------------------------------
# Step 2: LaTeX-safe OCR cleaning
# ---------------------------------------------------------------------------

def clean_ocr_text(text: str) -> str:
    """Fix common OCR artifacts without destroying LaTeX formulas."""
    text, math_regions = _protect_math_regions(text)

    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\n +", "\n", text)
    text = re.sub(r" +\n", "\n", text)

    text = _restore_math_regions(text, math_regions)
    return text.strip()


# ---------------------------------------------------------------------------
# Step 3: Section splitting
# ---------------------------------------------------------------------------

def split_into_sections(text: str) -> List[Dict]:
    """
    Split text into semantic sections. Returns list of dicts with
    'header' and 'content' keys for metadata extraction.
    """
    matches = list(SECTION_HEADER_RE.finditer(text))

    if not matches:
        return [{"header": "", "content": text.strip()}] if text.strip() else []

    sections = []

    first_start = matches[0].start()
    if first_start > 0:
        preamble = text[:first_start].strip()
        if preamble:
            sections.append({"header": "", "content": preamble})

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        header = match.group(1).strip()
        if section_text:
            sections.append({"header": header, "content": section_text})

    return sections


def detect_type(text: str) -> str:
    """Identify content type from the first 200 chars."""
    sample = text[:200].lower()
    if re.search(r"example\s+\d", sample):
        return "example"
    if re.search(r"activity\s+\d", sample):
        return "activity"
    if re.search(r"fig\.?\s*\d", sample):
        return "figure"
    if re.search(r"table\s+\d", sample):
        return "table"
    if has_math_content(text):
        return "formula"
    return "concept"


# ---------------------------------------------------------------------------
# Step 4: Equation-block gluing (Req #3, #9)
# ---------------------------------------------------------------------------

def glue_equation_blocks(text: str) -> str:
    """
    Ensure equation explanation lines (where:, given:, therefore:, etc.)
    are NOT separated from their preceding formula by paragraph breaks.

    Before:
        $$E = \\frac{1}{2}mv^2$$
        <paragraph break>
        where m is mass and v is velocity

    After:
        $$E = \\frac{1}{2}mv^2$$
        where m is mass and v is velocity
    """
    paragraphs = text.split("\n\n")
    glued = []

    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]

        # Look ahead: if next paragraph starts with equation explanation,
        # glue it to current paragraph
        while i + 1 < len(paragraphs):
            next_para = paragraphs[i + 1].strip()
            if EQUATION_EXPLANATION_RE.match(next_para):
                para = para + "\n" + next_para
                i += 1
            else:
                break

        glued.append(para)
        i += 1

    return "\n\n".join(glued)


# ---------------------------------------------------------------------------
# Semantic chunking — full pipeline → returns CLEAN STRING
#   (Req #6: no [BLOCK] or [FORMULA] markers in text)
# ---------------------------------------------------------------------------

def semantic_chunking(text: str, chapter: str) -> str:
    """
    Full semantic reconstruction pipeline:
    1. Reconstruct paragraphs (merge OCR line breaks)
    2. Clean OCR text (LaTeX-safe)
    3. Convert OCR math → LaTeX
    4. Convert pipe-tables → markdown tables
    5. Glue equation explanation blocks
    6. Return clean text (NO structural markers)

    Returns:
        str — clean reconstructed text suitable for chapter.txt
    """
    text = reconstruct_paragraphs(text)
    text = clean_ocr_text(text)
    text = convert_ocr_to_latex(text)
    text = convert_tables_to_markdown(text)
    text = glue_equation_blocks(text)

    return text


# ---------------------------------------------------------------------------
# Tag figures (kept for backward compat, but not injected into text)
# ---------------------------------------------------------------------------

def tag_figures(text: str):
    lines = text.split("\n")
    tagged_lines = []
    for line in lines:
        match = FIG_PATTERN.search(line)
        if match:
            fig = match.group(1)
            tagged_lines.append(f"[FIGURE_REFERENCE: {fig}]")
            tagged_lines.append(line)
        else:
            tagged_lines.append(line)
    return "\n".join(tagged_lines)


# ---------------------------------------------------------------------------
# Content / Generate Type Enums + Chunk Config
# ---------------------------------------------------------------------------

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


#  (chunk_size, overlap)  — target: 600-900 chars, 120 overlap
CHUNK_CONFIG = {
    ContentType.question_paper: (800, 120),

    GenerateType.summary: (1200, 150),
    GenerateType.notes: (900, 120),
    GenerateType.worksheet: (700, 100),
    GenerateType.lesson_plan: (1000, 150),
    GenerateType.only_mcq: (800, 120),
    GenerateType.only_fill_blank: (800, 120),
    GenerateType.only_short_question: (800, 120),
    GenerateType.only_long_question: (800, 120),
    GenerateType.only_case_base: (800, 120),
}


# ---------------------------------------------------------------------------
# Paragraph-aware Semantic Chunking (Req #7)
# ---------------------------------------------------------------------------

def _split_preserving_equations(text: str, max_size: int, overlap: int) -> List[str]:
    """
    Split text into chunks while keeping formula + explanation blocks together.

    Strategy:
    1. Split by \n\n into paragraphs
    2. Glue equation-explanation paragraphs to their formula
    3. Accumulate paragraphs until reaching target size
    4. If a single paragraph > max_size, use sentence splitter as fallback
    5. Never split inside a $ or $$ pair
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        return []

    # Minimum chunk size — keep accumulating until we reach this
    min_size = max(300, max_size // 2)

    # Glue: if a paragraph starts with an equation explanation keyword,
    # merge it with the previous paragraph (Req #3, #9)
    glued_paragraphs = []
    for para in paragraphs:
        if glued_paragraphs and EQUATION_EXPLANATION_RE.match(para):
            glued_paragraphs[-1] = glued_paragraphs[-1] + "\n" + para
        else:
            glued_paragraphs.append(para)

    # Build chunks by accumulating paragraphs
    chunks = []
    current = ""

    for para in glued_paragraphs:
        combined = (current + "\n\n" + para).strip() if current else para

        if len(combined) <= max_size:
            # Still under max — keep accumulating
            current = combined
        else:
            # Combined would exceed max_size.
            # Only emit if current chunk is large enough on its own.
            if current and len(current) >= min_size:
                chunks.append(current)
                current = para
            elif current:
                # Current is too small to emit alone.
                # If combined is not absurdly large (< 2x max), keep together.
                if len(combined) <= max_size * 2:
                    current = combined
                else:
                    # Must emit current even though it's small, combined is way too big
                    chunks.append(current)
                    current = para
            else:
                current = para

            # If current single paragraph is too large, use sentence splitter
            if len(current) > max_size:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=max_size,
                    chunk_overlap=overlap,
                    separators=["\n\n", ". ", "? ", "! ", "\n", " "],
                )
                sub_chunks = splitter.split_text(current)
                sub_chunks = _merge_broken_math(sub_chunks)
                chunks.extend(sub_chunks[:-1])  # emit all but last
                current = sub_chunks[-1] if sub_chunks else ""

    if current:
        chunks.append(current)

    # Add overlap: prepend last `overlap` chars of previous chunk
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            if "$" not in prev_tail or prev_tail.count("$") % 2 == 0:
                overlapped.append(prev_tail + " " + chunks[i])
            else:
                overlapped.append(chunks[i])
        chunks = overlapped

    return chunks


def _merge_broken_math(chunks: List[str]) -> List[str]:
    """Merge chunks that break a $ or $$ pair."""
    merged = []
    carry = ""

    for chunk in chunks:
        chunk = carry + chunk
        carry = ""

        # Count unmatched $ signs (ignoring $$)
        text_no_display = re.sub(r"\$\$.*?\$\$", "", chunk, flags=re.DOTALL)
        dollar_count = text_no_display.count("$")

        if dollar_count % 2 != 0:
            # Odd number of $ — formula is split
            carry = chunk + " "
        else:
            merged.append(chunk)

    if carry:
        if merged:
            merged[-1] = merged[-1] + " " + carry
        else:
            merged.append(carry)

    return merged


def _merge_tiny_chunks(chunks: List[str], min_size: int = 200) -> List[str]:
    """Merge chunks below min_size with their neighbor."""
    if not chunks:
        return chunks

    merged = []
    buffer = ""

    for chunk in chunks:
        if len(chunk.strip()) < min_size:
            buffer = (buffer + "\n\n" + chunk).strip() if buffer else chunk.strip()
        else:
            if buffer:
                chunk = buffer + "\n\n" + chunk
                buffer = ""
            merged.append(chunk)

    if buffer:
        if merged:
            merged[-1] = merged[-1] + "\n\n" + buffer
        else:
            merged.append(buffer)

    return merged


# ---------------------------------------------------------------------------
# Main chunk_text — produces clean output (Req #6, #10)
# ---------------------------------------------------------------------------

def chunk_text(text: str, content_type, chapter: str = "") -> List[Dict]:
    """
    Split text into chunks for vector storage.

    Output format (Req #6, #10):
    {
        "content": "...clean text without structural markers...",
        "metadata": {
            "chunk_id": 0,
            "chapter": "...",
            "section": "...",
            "type": "concept|formula|example|activity|figure|table",
            "has_formula": true/false,
            "formula_count": 2
        }
    }

    Formulas are extracted into metadata (formula_count) but NOT
    duplicated — they remain naturally in the content text.
    """
    # Split into semantic sections
    sections = split_into_sections(text)

    size, overlap = CHUNK_CONFIG[content_type]

    chunks = []

    for section_info in sections:
        header = section_info["header"]
        section_text = section_info["content"]

        if not section_text or len(section_text) < 10:
            continue

        block_type = detect_type(section_text)

        # Use paragraph-aware splitting instead of char-based
        section_chunks = _split_preserving_equations(section_text, size, overlap)

        # Post-process
        section_chunks = _merge_tiny_chunks(section_chunks, min_size=100)
        section_chunks = _merge_broken_math(section_chunks)

        for chunk_text_str in section_chunks:
            chunk_text_str = chunk_text_str.strip()
            if not chunk_text_str or len(chunk_text_str) < 50:
                continue

            # Extract formulas for metadata (Req #10)
            formulas = detect_formulas(chunk_text_str)

            chunks.append({
                "content": chunk_text_str,
                "metadata": {
                    "chunk_id": len(chunks),
                    "chapter": chapter,
                    "section": header[:120] if header else section_text[:80],
                    "type": block_type,
                    "has_formula": len(formulas) > 0,
                    "formula_count": len(formulas),
                }
            })

    logger.info(f"Chunking complete: {len(chunks)} chunks (target: 100-200)")
    return chunks
