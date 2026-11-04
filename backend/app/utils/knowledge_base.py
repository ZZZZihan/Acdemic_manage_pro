"""In-memory corpus.

The database is the source of truth. This object is a derived cache and is
not written back to the repository.
"""
import logging

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(self):
        self.documents = {}

    def replace_all(self, documents):
        self.documents = documents or {}
        return len(self.documents)

    def add_document(self, doc_id, title, content, metadata=None):
        self.documents[str(doc_id)] = {
            "title": title or "",
            "content": content or "",
            "metadata": metadata or {},
        }
        return True

    def remove_document(self, doc_id):
        return self.documents.pop(str(doc_id), None) is not None

    def get_document(self, doc_id):
        return self.documents.get(str(doc_id))

    def get_all_documents(self):
        return self.documents

    def search_documents(self, query):
        needle = (query or "").strip().lower()
        if len(needle) < 2:
            return []
        matches = []
        for doc_id, doc in self.documents.items():
            title = doc.get("title") or ""
            content = doc.get("content") or ""
            if needle in title.lower() or needle in content.lower():
                copied = dict(doc)
                copied["id"] = doc_id
                matches.append(copied)
        return matches


knowledge_base = KnowledgeBase()
logger.debug("knowledge corpus starts empty until it is synced from the database")
