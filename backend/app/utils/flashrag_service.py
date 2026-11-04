"""Backward-compatible import path.

The previous module loaded an embedding model at import time. Retrieval now
lives in ``app.rag.service`` and stays unloaded until a vector query runs.
"""
from app.rag.service import RagUnavailable, retrieve, sync_corpus_from_db

__all__ = ["RagUnavailable", "retrieve", "sync_corpus_from_db"]
