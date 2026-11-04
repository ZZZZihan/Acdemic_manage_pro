"""Pull text out of uploaded notes. Scanned PDFs are recorded, not dropped."""
from pathlib import Path


def extract_file(path):
    """Return ``(text, status)``.

    Status is ``ok``, ``unsupported_scan``, ``unsupported_type``, or
    ``extract_failed``. Callers persist the non-ok statuses.
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    try:
        if suffix in {".txt", ".md", ".markdown"}:
            return file_path.read_text(encoding="utf-8", errors="replace"), "ok"
        if suffix == ".pdf":
            return _pdf(file_path)
        if suffix == ".docx":
            return _docx(file_path)
    except Exception:
        return "", "extract_failed"
    return "", "unsupported_type"


def _pdf(path):
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n".join(pages).strip()
    if not text:
        return "", "unsupported_scan"
    return text, "ok"


def _docx(path):
    from docx import Document

    document = Document(str(path))
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    text = "\n".join(parts).strip()
    if not text:
        return "", "unsupported_scan"
    return text, "ok"
