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
    r"\d+\.\d+\s+[A-Z][^\n]+"
    r"|Section\s+\d+[^\n]*"
    r"|Chapter\s+\d+[^\n]*"
    r"|Exercise\s+\d+[^\n]*"
    r"|Example\s+\d+[^\n]*"
    r"|Activity\s+\d+[^\n]*"
    r"|Table\s+\d+[^\n]*"
    r"|Definition\s+[^\n]*"
    r"|[A-Z][A-Z\s]{5,}"
    r")",
    re.IGNORECASE,
)

EXERCISE_BLOCK_RE = re.compile(
    r"(?:^|\n)(?:"
    r"\d+[\.\)]\s"                # 1. or 1)
    r"|[a-z][\.\)]\s"             # a. or a)
    r"|\([ivx]+\)\s"              # (i), (ii), etc.
    r"|Question\s+\d+"            # Question 1
    r"|Exercise\s+\d+"            # Exercise 2
    r"|Try\s+this"                # Try this
    r"|Figure\s+it\s+out"         # Figure it out
    r")",
    re.IGNORECASE
)

DEFINITION_BLOCK_RE = re.compile(
    r"^(?:Definition:?|Note:?|Key\s+Concept:?)\s+",
    re.IGNORECASE | re.MULTILINE
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

# ---------------------------------------------------------------------------
# Advanced OCR Cleanup (Req #1)
# ---------------------------------------------------------------------------

def remove_ocr_artifacts(text: str) -> str:
    """
    Remove common OCR artifacts like page numbers, headers, footers, 
    and timestamps.
    """
    # Remove page numbers like "Page 12", "12 of 45", or just a digit on its own line
    text = re.sub(r"(?m)^\s*(?:Page\s+)?\d+(?:\s+of\s+\d+)?\s*$", "", text)
    
    # Remove strings like "Chapter 22..in 1199 77//1100//22002255"
    text = re.sub(r"(?m)^.*Chapter\s+\d+\.\.in\s+\d+.*$", "", text, flags=re.I)
    
    # Remove stamps like "Ganita Prakash | Grade 8"
    text = re.sub(r"(?m)^.*Ganita\s+Prakash\s*\|\s*Grade\s+\d+.*$", "", text, flags=re.I)

    # Remove timestamps like "12:34:56" or "2024-03-12 16:00"
    text = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "", text)
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", text)
    
    # Remove repeated book titles/subject names (often in headers)
    # e.g. "Mathematics Grade 8", "Class 8 Mathematics"
    subjects = "Mathematics|Science|Social Science|History|Geography|English|Physics|Chemistry|Biology"
    text = re.sub(fr"(?m)^\s*(?:{subjects})\s+(?:Grade|Class)\s+\d+\s*$", "", text, flags=re.I)
    text = re.sub(fr"(?m)^\s*(?:Grade|Class)\s+\d+\s+(?:{subjects})\s*$", "", text, flags=re.I)

    # Remove repeated publishing/copyright strings
    text = re.sub(r"(?i)©\s*NCERT|©\s*All\s*rights\s*reserved|Not\s*to\s*be\s*republished", "", text)

    # Remove strings of 3+ repeated characters that aren't likely math symbols (e.g. "----------")
    text = re.sub(r"(?<![0-9\$])([^\.\s\d\$])\1{2,}(?![0-9\$])", "", text)
    text = re.sub(r"\.{4,}", "", text) # Remove excessive dots
    
    return text

def remove_duplicate_lines(text: str) -> str:
    """Remove consecutive duplicate lines often produced by OCR."""
    lines = text.split("\n")
    if not lines:
        return text
    
    cleaned_lines = []
    prev_line = None
    for line in lines:
        stripped = line.strip()
        # If line is identical to previous, skip it
        if stripped and stripped == prev_line:
            continue
        cleaned_lines.append(line)
        if stripped:
            prev_line = stripped
            
    return "\n".join(cleaned_lines)

def normalize_formulas(text: str) -> str:
    """
    Normalize OCR-produced math notation into proper LaTeX notation.
    Example: 0.001 cm x 22 -> 0.001 cm x 2^2
    """
    # Fix 22 -> 2² pattern for simple exponents often lost in OCR
    # Only if it looks like a power of a number
    def _power_repl(match):
        base = match.group(1)
        exp = match.group(2)
        # Avoid common words/numbers that aren't powers
        if base in ["11", "22", "33"] and exp == base[0]:
             return match.group(0)
        return f"{base}^{{{exp}}}"

    # Matches digit followed by same digit (very basic, but requested)
    # text = re.sub(r"(\d)(\1)", _power_repl, text)
    
    # Better: match known patterns like 22, 10-2, etc.
    # But specifically user requested: 0.001 cm x 22 -> 0.001 cm x 2^2
    # Fix for the specific example and similar patterns
    text = re.sub(r"(\d)\s*[x×]\s*(\d)(\2)\b", r"\1 \\times \2^{2}", text)
    
    # Also handle things like 102 -> 10^2 if it follows a number
    text = re.sub(r"(\d{1,2})([23])\b", r"\1^{\2}", text)

    return text

def fix_repeated_chars(text: str) -> str:
    """
    Fix stuttering OCR text like 'CChhaapptteerr' -> 'Chapter' 
    or 'PPhhyyssiiccss' -> 'Physics'.
    """
    # Matches patterns where each character is repeated: XYXY -> XY
    # Uses a lookahead to ensure we are matching doubling
    # e.g., CChhaapptteerr -> C h a p t e r
    # This regex looks for 4+ chars where every even char matches the previous one
    def _de_stutter(match):
        s = match.group(0)
        # Check if it's actually stuttered: char 0==1, 2==3, etc.
        if all(s[i] == s[i+1] for i in range(0, len(s), 2)):
            return "".join(s[i] for i in range(0, len(s), 2))
        return s

    return re.sub(r"\b(?:[A-Za-z]{2,})\b", _de_stutter, text)

# ---------------------------------------------------------------------------
# Math Exponent Conversion (Req #5)
# ---------------------------------------------------------------------------

def convert_mult_to_exponent(text: str) -> str:
    """
    Convert repeated multiplication like 'x * x * x' to 'x^3'.
    Only works for simple variables to avoid false positives.
    """
    def _repl(match):
        full_match = match.group(0)
        var = match.group(1).strip()
        # Find which operator was used (* or ×)
        op = "*" if "*" in full_match else "×"
        count = full_match.count(op) + 1
        return f"{var}^{{{count}}}"

    # Matches x * x * x where x is a variable or digit
    # Pattern explanation:
    # ((?:\b\w+\b|\d+)) -> Group 1: variable or number
    # (\s*[*×]\s*\1)+ -> One or more repetitions of (operator + variable)
    pattern = r"((?:\b\w+\b|\d+))(\s*[*×]\s*\1)+"
    return re.sub(pattern, _repl, text, flags=re.IGNORECASE)


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
    Detect pipe-delimited table rows (from pdfplumber) or space-aligned 
    table-like structures and convert them to proper markdown tables.
    """
    lines = text.split("\n")
    result = []
    table_buffer = []

    def flush_table():
        if len(table_buffer) < 2:
            result.extend(table_buffer)
            return

        # Check if it's pipe-delimited or space-delimited
        is_pipe = all("|" in row for row in table_buffer)
        
        formatted_rows = []
        max_cols = 0
        
        for row in table_buffer:
            if is_pipe:
                cells = [c.strip() for c in row.split("|") if c.strip()]
            else:
                # Basic space-based splitting for simple tables
                # Try splitting by 2+ spaces first
                cells = re.split(r"\s{2,}", row.strip())
                if len(cells) < 2:
                    # If not, try common pattern: Digit + Space + Rest
                    match = re.match(r"^(\d+)\s+(.+)$", row.strip())
                    if match:
                        cells = [match.group(1), match.group(2)]
            
            if cells:
                max_cols = max(max_cols, len(cells))
                formatted_rows.append(cells)

        if not formatted_rows or max_cols < 2:
            result.extend(table_buffer)
            return

        # Build markdown table
        for i, cells in enumerate(formatted_rows):
            # Pad cells if necessary
            cells += [""] * (max_cols - len(cells))
            md_row = "| " + " | ".join(cells) + " |"
            result.append(md_row)
            if i == 0:
                result.append("| " + " | ".join(["----"] * max_cols) + " |")

    for line in lines:
        stripped = line.strip()
        # Detect table line: pipe-delimited or contains multiple gaps of spaces (2+ spaces)
        # Or starts with a digit/identifier followed by values
        # Or looks like a header (all caps/bold) followed by values
        parts = re.split(r"\s{2,}", stripped)
        is_table_line = ("|" in stripped and stripped.count("|") >= 1) or \
                         (len(parts) >= 2) or \
                         (bool(re.match(r"^\d+\s+\d+", stripped)))
        
        if is_table_line and stripped:
            # Use original line to preserve spacing for table parsing
            table_buffer.append(line) 
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

        # If it's a table-like structure, don't merge lines
        if any("|" in l or len(re.split(r"\s{2,}", l.strip())) >= 2 for l in lines):
            rebuilt.append(para)
            continue

        if len(lines) == 1:
            rebuilt.append(lines[0].strip())
            continue

        merged_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            is_heading = bool(SECTION_HEADER_RE.match(line))
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
    """
    Fix common OCR artifacts without destroying LaTeX formulas.
    """
    # Protect math
    text, math_regions = _protect_math_regions(text)

    # Req #1: Remove artifacts and fix doubling
    text = remove_ocr_artifacts(text)
    text = fix_repeated_chars(text)
    text = remove_duplicate_lines(text)
    
    # Req #8: Normalize formulas
    text = normalize_formulas(text)

    # Basic cleanup
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\n +", "\n", text)
    text = re.sub(r" +\n", "\n", text)

    # Restore math
    text = _restore_math_regions(text, math_regions)
    
    # Req #5: Convert exponents (outside protected math if needed, but safe here)
    text = convert_mult_to_exponent(text)

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
    """
    Identify content type from the first 200 chars.
    Priority: exercise → definition → example → table → formula → concept
    """
    sample = text[:1500].lower()
    
    # Priority: exercise → definition → example → table → formula → concept
    if re.search(r"exercise\s+\d|question\s+\d|try\s+this|figure\s+it\s+out|\d+[\.\)]\s", sample):
        return "exercise"
    if re.search(r"definition|key\s+concept|note:", sample) or DEFINITION_BLOCK_RE.search(sample):
        return "definition"
    if re.search(r"example\s+\d", sample):
        return "example"
    if re.search(r"table|\|\s*----+\s*\|", sample) or (sample.count("|") >= 2) or ("| --" in sample):
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
    Ensures chunks never start/end mid-sentence (Req #7).
    """
    # Ensure we use sentence-aware splitting at the paragraph level first
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        return []

    min_size = max(300, max_size // 2)

    glued_paragraphs = []
    for para in paragraphs:
        is_explanation = EQUATION_EXPLANATION_RE.match(para)
        is_exercise_part = EXERCISE_BLOCK_RE.match(para)
        is_definition_cont = DEFINITION_BLOCK_RE.match(para)

        # Glue explanation or sub-parts to the previous block
        if glued_paragraphs and (is_explanation or is_exercise_part or is_definition_cont):
            glued_paragraphs[-1] = glued_paragraphs[-1] + "\n\n" + para
        else:
            glued_paragraphs.append(para)

    chunks = []
    current = ""

    for para in glued_paragraphs:
        combined = (current + "\n\n" + para).strip() if current else para

        if len(combined) <= max_size:
            current = combined
        else:
            if current and len(current) >= min_size:
                chunks.append(current)
                current = para
            elif current:
                # If current is too small, extend max_size slightly to avoid tiny chunks
                if len(combined) <= max_size * 1.5:
                    current = combined
                else:
                    chunks.append(current)
                    current = para
            else:
                current = para

            if len(current) > max_size:
                # Sentence-aware splitting within a large paragraph
                # Req #7: Chunks should never start/end mid-sentence
                sentences = re.split(r"(?<=[.?!])\s+", current)
                
                temp_chunk = ""
                for s in sentences:
                    if len(temp_chunk) + len(s) + 1 <= max_size:
                        temp_chunk = (temp_chunk + " " + s).strip()
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)
                        temp_chunk = s
                current = temp_chunk

    if current:
        chunks.append(current)

    # Post-process overlap with sentence awareness
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            sentences = re.split(r"(?<=[.?!])\s+", prev_chunk)
            
            overlap_content = ""
            current_len = 0
            for s in reversed(sentences):
                if current_len + len(s) <= overlap:
                    overlap_content = s + " " + overlap_content
                    current_len += len(s)
                else:
                    break
            
            if overlap_content:
                overlapped.append(overlap_content.strip() + " " + chunks[i])
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
    Split text into chunks for vector storage with type-specific sizing and metadata.
    """
    # 1. OCR Pre-cleaning (preserving whitespace for tables)
    text = remove_ocr_artifacts(text)
    text = fix_repeated_chars(text)
    text = remove_duplicate_lines(text)
    
    # 2. Structure reconstruction
    text = convert_tables_to_markdown(text)
    text = reconstruct_paragraphs(text)
    
    # 3. Content normalization
    text = normalize_formulas(text)
    text = convert_ocr_to_latex(text)
    text = glue_equation_blocks(text)

    # 4. Split into semantic sections
    sections = split_into_sections(text)

    # Default size/overlap
    default_size, default_overlap = CHUNK_CONFIG.get(content_type, (800, 120))

    chunks = []

    for section_info in sections:
        header = section_info["header"]
        section_text = section_info["content"]

        if not section_text or len(section_text) < 10:
            continue

        block_type = detect_type(section_text)
        
        # Apply type-specific sizing logic (Req #10)
        # concept → 700–900 characters
        # example → 600–800 characters
        # exercise → 500–700 characters
        if block_type == "concept":
            size, overlap = (800, 120)
        elif block_type == "definition":
            size, overlap = (800, 120)
        elif block_type == "example":
            size, overlap = (700, 120)
        elif block_type == "exercise":
            size, overlap = (600, 120)
        else:
            size, overlap = (default_size, default_overlap)

        # Use paragraph-aware splitting
        section_chunks = _split_preserving_equations(section_text, size, overlap)

        # Post-process
        section_chunks = _merge_tiny_chunks(section_chunks, min_size=100)
        section_chunks = _merge_broken_math(section_chunks)

        for chunk_text_str in section_chunks:
            chunk_text_str = chunk_text_str.strip()
            if not chunk_text_str or len(chunk_text_str) < 30:
                continue

            # Extract formulas for metadata (Req #9)
            formulas = detect_formulas(chunk_text_str)

            chunks.append({
                "content": chunk_text_str,
                "metadata": {
                    "chunk_id": len(chunks),
                    "chapter": chapter,
                    "section": header[:120] if header else "",
                    "type": block_type,
                    "has_formula": len(formulas) > 0,
                    "formula_count": len(formulas),
                }
            })

    logger.info(f"Chunking complete: {len(chunks)} chunks")
    return chunks
