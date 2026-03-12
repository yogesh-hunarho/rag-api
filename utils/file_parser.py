import pdfplumber
import docx
import re

# ---------------------------------------------------------------------------
# Formula Detection (matches the patterns in services/chunking.py)
# ---------------------------------------------------------------------------

# Delimited math
INLINE_MATH_RE = re.compile(r"\$(?!\$)(.+?)\$", re.DOTALL)
DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
PAREN_MATH_RE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
BRACKET_MATH_RE = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)

# LaTeX commands even without $ delimiters (OCR often drops them)
LATEX_COMMAND_RE = re.compile(
    r"\\(?:frac|sqrt|vec|hat|bar|dot|int|sum|prod|lim|partial|nabla|"
    r"alpha|beta|gamma|delta|theta|lambda|sigma|phi|omega|"
    r"sin|cos|tan|log|ln|exp|"
    r"rightarrow|leftarrow|times|div|pm|cdot|leq|geq|neq|approx|equiv|"
    r"text|mathrm|begin|end)\b"
)

# Simple assignment formulas: F = ma, v = u + at
SIMPLE_FORMULA_RE = re.compile(r"[A-Za-z_]\w*\s*=\s*[^,\n]{2,}")

# Chemical equations with arrows
CHEMICAL_ARROW_RE = re.compile(
    r"[A-Za-z0-9₀₁₂₃₄₅₆₇₈₉\s\+\(\)]+\s*(?:→|⟶|->|\\rightarrow|\\to)\s*[A-Za-z0-9₀₁₂₃₄₅₆₇₈₉\s\+\(\)]+"
)


def tag_formulas(text: str) -> str:
    """
    Detect formulas in extracted text and append a [FORMULAS] section
    so that downstream chunking / retrieval can identify them.
    """
    formulas = set()

    for pattern in [DISPLAY_MATH_RE, INLINE_MATH_RE, PAREN_MATH_RE, BRACKET_MATH_RE]:
        for m in pattern.finditer(text):
            formulas.add(m.group(0).strip())

    for m in SIMPLE_FORMULA_RE.finditer(text):
        f = m.group(0).strip()
        if len(f) < 200:
            formulas.add(f)

    for m in CHEMICAL_ARROW_RE.finditer(text):
        formulas.add(m.group(0).strip())

    for m in LATEX_COMMAND_RE.finditer(text):
        start = max(0, m.start() - 15)
        end = min(len(text), m.end() + 30)
        snippet = text[start:end].strip()
        snippet = re.split(r"[.!?]\s", snippet)[0]
        if len(snippet) > 3:
            formulas.add(snippet)

    if formulas:
        text += "\n\n[FORMULAS]\n" + "\n".join(sorted(formulas))

    return text


# ---------------------------------------------------------------------------
# Text Extraction
# ---------------------------------------------------------------------------

def extract_text(file) -> str:
    name = file.filename.lower()

    # PDF parsing
    if name.endswith(".pdf"):
        text_parts = []

        with pdfplumber.open(file.file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text_parts.append(page_text)

                # extract tables if present
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        row_text = " | ".join([cell or "" for cell in row])
                        text_parts.append(row_text)

        text = "\n".join(text_parts)
        return tag_formulas(text)

    # DOCX parsing
    if name.endswith(".docx"):
        d = docx.Document(file.file)
        return "\n".join(p.text for p in d.paragraphs)

    # TXT parsing
    if name.endswith(".txt"):
        return file.file.read().decode("utf-8")

    raise ValueError("Unsupported file")