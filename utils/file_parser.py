import docx
import os
import shutil
import logging
import re

try:
    import pymupdf4llm
except ImportError:  # pragma: no cover
    pymupdf4llm = None

try:
    import pymupdf
except ImportError:  # pragma: no cover
    pymupdf = None

logger = logging.getLogger(__name__)
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_DIGIT_RE = re.compile(r"\d")
_SYMBOLS_ONLY_RE = re.compile(r"^[^\w\u0900-\u097F]+$")


def _normalize_language(language: str) -> str:
    value = (language or "auto").strip().lower()
    mapping = {
        "auto": "auto",
        "eng": "eng",
        "english": "eng",
        "hin": "hin",
        "hindi": "hin+eng",
        "hin+eng": "hin+eng",
        # In practice for mixed Hindi textbook pages, hin+eng is usually better than script model.
        "devanagari": "hin+eng",
        "script/devanagari": "hin+eng",
        "script\\devanagari": "hin+eng",
    }
    return mapping.get(value, language.strip() if language else "auto")


def _configure_tesseract_environment() -> None:
    """
    Best-effort setup for OCR runtime on Windows if PATH / TESSDATA_PREFIX are missing.
    """
    candidates = []

    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd:
        candidates.append(env_cmd)

    candidates.extend(
        [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
    )

    tesseract_path = None
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            tesseract_path = candidate
            break

    if not tesseract_path:
        which_path = shutil.which("tesseract")
        if which_path:
            tesseract_path = which_path

    if not tesseract_path:
        return

    bin_dir = os.path.dirname(tesseract_path)
    current_path = os.getenv("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    if bin_dir not in path_parts:
        os.environ["PATH"] = bin_dir + os.pathsep + current_path if current_path else bin_dir

    if not os.getenv("TESSDATA_PREFIX"):
        tessdata_dir = os.path.join(bin_dir, "tessdata")
        if os.path.isdir(tessdata_dir):
            os.environ["TESSDATA_PREFIX"] = tessdata_dir


def _resolve_tessdata_path() -> str | None:
    env_tessdata = os.getenv("TESSDATA_PREFIX")
    if env_tessdata and os.path.isdir(env_tessdata):
        return env_tessdata

    tesseract_cmd = os.getenv("TESSERACT_CMD")
    candidates = []
    if tesseract_cmd:
        candidates.append(os.path.join(os.path.dirname(tesseract_cmd), "tessdata"))

    tesseract_in_path = shutil.which("tesseract")
    if tesseract_in_path:
        candidates.append(os.path.join(os.path.dirname(tesseract_in_path), "tessdata"))

    candidates.extend(
        [
            r"C:\Program Files\Tesseract-OCR\tessdata",
            r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
        ]
    )

    for candidate in candidates:
        if candidate and os.path.isdir(candidate):
            return candidate
    return None


def _extract_pdf_with_forced_ocr(doc, language: str, tessdata: str) -> str:
    logger.info("PDF extraction mode=forced_ocr language=%s tessdata=%s", language, tessdata)
    pages = []
    for page in doc:
        textpage = page.get_textpage_ocr(
            language=language,
            dpi=300,
            full=True,
            tessdata=tessdata,
        )
        page_text = page.get_text("text", textpage=textpage)
        if page_text:
            pages.append(page_text.replace("\x0c", "").strip())
    return "\n\n".join(p for p in pages if p)


def _clean_ocr_output(text: str) -> str:
    filtered_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            filtered_lines.append("")
            continue

        if line.lower().startswith("http://") or line.lower().startswith("https://"):
            filtered_lines.append(line)
            continue

        if _SYMBOLS_ONLY_RE.fullmatch(line):
            continue

        dev = len(_DEVANAGARI_RE.findall(line))
        lat = len(_LATIN_RE.findall(line))
        digits = len(_DIGIT_RE.findall(line))

        # Drop tiny noisy fragments like isolated OCR artifacts.
        if len(line) <= 2 and (lat or digits):
            continue

        # Drop short lines that are mostly Latin / numeric noise in Hindi OCR output.
        if dev == 0 and (lat + digits) >= 4 and len(line) <= 20:
            continue

        filtered_lines.append(line)

    # Merge fragmented OCR lines into paragraphs.
    merged_lines = []
    paragraph_parts: list[str] = []
    for line in filtered_lines:
        if not line:
            if paragraph_parts:
                merged_lines.append(" ".join(paragraph_parts))
                paragraph_parts = []
            continue

        if line.lower().startswith("http://") or line.lower().startswith("https://"):
            if paragraph_parts:
                merged_lines.append(" ".join(paragraph_parts))
                paragraph_parts = []
            merged_lines.append(line)
            continue

        paragraph_parts.append(line)

    if paragraph_parts:
        merged_lines.append(" ".join(paragraph_parts))

    text = "\n\n".join(merged_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(file, language: str = "auto") -> str:
    """
    Extract content from an uploaded file.

    PDFs are converted to Markdown via PyMuPDF4LLM.
    """
    name = (file.filename or "").lower()

    if name.endswith(".pdf"):
        if pymupdf4llm is None:
            raise RuntimeError("Missing dependency: pymupdf4llm. Install it to enable PDF ingestion.")
        if pymupdf is None:
            raise RuntimeError("Missing dependency: pymupdf. Install it to enable PDF ingestion.")

        try:
            file.file.seek(0)
        except Exception:
            pass

        pdf_bytes = file.file.read()
        if not pdf_bytes:
            return ""

        # Avoid passing the UploadFile handle (often a NamedTemporaryFile on Windows that
        # cannot be reopened by path while still open). Use an in-memory stream instead.
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        try:
            ocr_language = _normalize_language(language)
            if ocr_language != "auto":
                _configure_tesseract_environment()
                tessdata = _resolve_tessdata_path()
                if not tessdata:
                    raise RuntimeError(
                        "OCR failed. Tesseract tessdata folder not found. "
                        "Set TESSDATA_PREFIX (for example: C:\\Program Files\\Tesseract-OCR\\tessdata)."
                    )
                try:
                    return _clean_ocr_output(_extract_pdf_with_forced_ocr(doc, ocr_language, tessdata))
                except Exception as exc:
                    raise RuntimeError(
                        "OCR failed. Install Tesseract executable, ensure it is in PATH, "
                        "set TESSDATA_PREFIX to tessdata, and install Hindi data (hin). "
                        f"Original error: {exc}"
                    ) from exc
            logger.info("PDF extraction mode=pymupdf4llm language=auto")
            return pymupdf4llm.to_markdown(doc)
        finally:
            doc.close()

    if name.endswith(".docx"):
        try:
            file.file.seek(0)
        except Exception:
            pass
        d = docx.Document(file.file)
        return "\n".join(p.text for p in d.paragraphs)

    if name.endswith(".txt"):
        try:
            file.file.seek(0)
        except Exception:
            pass
        return file.file.read().decode("utf-8", errors="ignore")

    raise ValueError("Unsupported file")
