"""Structure-aware chunking for Chinese technical notes.

Headings become a section path. Body text is packed on sentence boundaries
with a character overlap so a citation span still sits inside one chunk.
"""
import re

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
_SENTENCE = re.compile(r"[^。！？!?]*[。！？!?]|[^。！？!?]+$")


def chunk_document(text, title="", size=480, overlap=60):
    """Return chunks with section path and spans into ``text``."""
    source = text or ""
    if not source.strip():
        return []
    sections = _sections(source)
    chunks = []
    for section, start, end in sections:
        body = source[start:end]
        for piece_start, piece_end in _pack(body, size, overlap):
            absolute_start = start + piece_start
            absolute_end = start + piece_end
            snippet = source[absolute_start:absolute_end].strip()
            if not snippet:
                continue
            chunks.append({
                "section": section or (title or ""),
                "text": snippet,
                "span_start": absolute_start,
                "span_end": absolute_end,
            })
    return chunks


def _sections(source):
    matches = list(_HEADING.finditer(source))
    if not matches:
        return [("", 0, len(source))]
    sections = []
    if matches[0].start() > 0:
        sections.append(("", 0, matches[0].start()))
    stack = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, heading))
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        path = " / ".join(item[1] for item in stack)
        sections.append((path, body_start, body_end))
    return [(path, start, end) for path, start, end in sections if end > start]


def _pack(body, size, overlap):
    if len(body) <= size:
        return [(0, len(body))]
    parts = []
    for match in _SENTENCE.finditer(body):
        piece = match.group(0)
        if piece:
            parts.append((match.start(), match.end()))
    if not parts:
        return _windows(body, size, overlap)
    spans = []
    current_start = None
    current_end = None
    for start, end in parts:
        if end - start > size:
            if current_start is not None:
                spans.append((current_start, current_end))
                current_start = None
                current_end = None
            spans.extend((start + left, start + right) for left, right in _windows(body[start:end], size, overlap))
            continue
        if current_start is None:
            current_start = start
            current_end = end
            continue
        if end - current_start <= size:
            current_end = end
            continue
        spans.append((current_start, current_end))
        rewind = max(current_start, current_end - overlap)
        current_start = rewind
        current_end = end
        if current_end - current_start > size:
            current_start = start
            current_end = end
    if current_start is not None:
        spans.append((current_start, current_end))
    return spans or [(0, min(len(body), size))]


def _windows(text, size, overlap):
    step = max(size - overlap, 1)
    spans = []
    for start in range(0, len(text), step):
        spans.append((start, min(len(text), start + size)))
        if start + size >= len(text):
            break
    return spans
