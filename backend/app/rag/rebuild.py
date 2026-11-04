"""Rebuild the persistent index from technical summaries.

Usage (from the backend directory, with secrets in the environment)::

    python -m app.rag.rebuild
"""
import json
import os
import sys


def main():
    from app import create_app
    from app.rag.ingest import rebuild_from_db
    from app.rag.service import sync_corpus_from_db

    app = create_app(os.getenv("FLASK_CONFIG") or "default")
    with app.app_context():
        memory = sync_corpus_from_db()
        stats = rebuild_from_db()
        stats["memory_docs"] = memory
        json.dump(stats, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0 if stats["documents"] == stats["tech_summary_rows"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
