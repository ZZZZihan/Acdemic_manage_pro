"""SQLite chunk store with a pgvector-shaped upsert/delete/search surface.

SQLite is the default because the lab app already runs on one file, the
index has to survive a process restart, and a few thousand chunks do not
need a second database service. ``search`` is brute-force cosine over the
stored float32 blobs. A Postgres deployment can keep the same method names
and replace the blob column with ``vector``; callers do not change.
"""
import sqlite3
import struct
import threading
from datetime import datetime, timezone
from pathlib import Path


def _pack(vector):
    return struct.pack(f"<{len(vector)}f", *[float(value) for value in vector])


def _unpack(blob, dim):
    if not blob or not dim:
        return []
    return list(struct.unpack(f"<{dim}f", blob))


class SqliteVectorStore:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                title TEXT,
                source TEXT,
                source_url TEXT,
                updated_at TEXT,
                access_scope TEXT,
                owner_id INTEGER,
                status TEXT
            );
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                section TEXT,
                text TEXT,
                span_start INTEGER,
                span_end INTEGER,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                dim INTEGER,
                vector BLOB
            );
            CREATE TABLE IF NOT EXISTS ingest_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                source TEXT,
                status TEXT,
                detail TEXT,
                created_at TEXT
            );
            """
        )
        self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()

    def upsert_document(self, document, chunks, vectors):
        """Replace every chunk of ``document['doc_id']`` and write embeddings."""
        doc_id = str(document["doc_id"])
        with self._lock:
            self._conn.execute("DELETE FROM embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = ?)", (doc_id,))
            self._conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            self._conn.execute(
                """
                INSERT INTO documents (doc_id, title, source, source_url, updated_at, access_scope, owner_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    title=excluded.title,
                    source=excluded.source,
                    source_url=excluded.source_url,
                    updated_at=excluded.updated_at,
                    access_scope=excluded.access_scope,
                    owner_id=excluded.owner_id,
                    status=excluded.status
                """,
                (
                    doc_id,
                    document.get("title") or "",
                    document.get("source") or "tech_summary",
                    document.get("source_url") or "",
                    document.get("updated_at") or "",
                    document.get("access_scope") or "lab",
                    document.get("owner_id"),
                    document.get("status") or "ok",
                ),
            )
            for index, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}:{chunk['span_start']}:{chunk['span_end']}:{index}"
                self._conn.execute(
                    """
                    INSERT INTO chunks (chunk_id, doc_id, section, text, span_start, span_end, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        doc_id,
                        chunk.get("section") or "",
                        chunk.get("text") or "",
                        int(chunk.get("span_start") or 0),
                        int(chunk.get("span_end") or 0),
                        chunk.get("source") or document.get("source") or "tech_summary",
                    ),
                )
                vector = vectors[index] if index < len(vectors) else []
                self._conn.execute(
                    "INSERT INTO embeddings (chunk_id, dim, vector) VALUES (?, ?, ?)",
                    (chunk_id, len(vector), _pack(vector) if vector else None),
                )
            self._conn.commit()

    def delete_document(self, doc_id):
        doc_id = str(doc_id)
        with self._lock:
            self._conn.execute(
                "DELETE FROM embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = ?)",
                (doc_id,),
            )
            self._conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            self._conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            self._conn.commit()

    def clear(self):
        with self._lock:
            self._conn.executescript(
                "DELETE FROM embeddings; DELETE FROM chunks; DELETE FROM documents;"
            )
            self._conn.commit()

    def log_ingest(self, doc_id, source, status, detail=""):
        with self._lock:
            self._conn.execute(
                "INSERT INTO ingest_log (doc_id, source, status, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(doc_id) if doc_id is not None else "", source or "", status or "", (detail or "")[:300], _now()),
            )
            self._conn.commit()

    def document_count(self):
        row = self._conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()
        return int(row["n"])

    def get_document(self, doc_id):
        row = self._conn.execute("SELECT * FROM documents WHERE doc_id = ?", (str(doc_id),)).fetchone()
        return dict(row) if row else None

    def failure_count(self, status=None):
        if status:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM ingest_log WHERE status = ?",
                (status,),
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM ingest_log").fetchone()
        return int(row["n"])

    def iter_chunks(self):
        rows = self._conn.execute(
            """
            SELECT c.chunk_id, c.doc_id, c.section, c.text, c.span_start, c.span_end, c.source,
                   d.title, d.source_url, d.updated_at, d.access_scope, d.owner_id,
                   e.dim, e.vector
            FROM chunks c
            JOIN documents d ON d.doc_id = c.doc_id
            LEFT JOIN embeddings e ON e.chunk_id = c.chunk_id
            """
        ).fetchall()
        for row in rows:
            yield {
                "chunk_id": row["chunk_id"],
                "doc_id": row["doc_id"],
                "section": row["section"] or "",
                "text": row["text"] or "",
                "span": [row["span_start"], row["span_end"]],
                "source": row["source"] or "tech_summary",
                "title": row["title"] or "",
                "source_url": row["source_url"] or "",
                "updated_at": row["updated_at"] or "",
                "access_scope": row["access_scope"] or "lab",
                "owner_id": row["owner_id"],
                "vector": _unpack(row["vector"], row["dim"] or 0),
            }


def _now():
    return datetime.now(timezone.utc).isoformat()
