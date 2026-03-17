import docx

try:
    import pymupdf4llm
except ImportError:  # pragma: no cover
    pymupdf4llm = None

try:
    import pymupdf
except ImportError:  # pragma: no cover
    pymupdf = None


def extract_text(file) -> str:
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
            return pymupdf4llm.to_markdown(doc)
        finally:
            doc.close()

    if name.endswith(".docx"):
        d = docx.Document(file.file)
        return "\n".join(p.text for p in d.paragraphs)

    if name.endswith(".txt"):
        return file.file.read().decode("utf-8", errors="ignore")

    raise ValueError("Unsupported file")
