import fitz, docx

def extract_text(file):
    name = file.filename.lower()

    if name.endswith(".pdf"):
        doc = fitz.open(stream=file.file.read(), filetype="pdf")
        return " ".join(page.get_text() for page in doc)

    if name.endswith(".docx"):
        d = docx.Document(file.file)
        return "\n".join(p.text for p in d.paragraphs)

    if name.endswith(".txt"):
        return file.file.read().decode("utf-8")

    raise ValueError("Unsupported file")
