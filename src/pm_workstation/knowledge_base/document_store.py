"""文档存储 — 持久化文档 CRUD"""

import json
import logging
import threading
from pathlib import Path

from pm_workstation.knowledge_base.rag_models import Document

logger = logging.getLogger(__name__)


class DocumentStore:
    """基于文件系统的文档持久化存储

    每篇文档保存为独立 JSON 文件，按 ID 哈希分目录避免单目录文件过多。
    """

    def __init__(self, storage_dir: str = "./data/rag/documents"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._docs: dict[str, Document] = {}
        self._lock = threading.Lock()
        self._load_all()

    def _doc_path(self, doc_id: str) -> Path:
        prefix = doc_id[:2]
        (self.storage_dir / prefix).mkdir(parents=True, exist_ok=True)
        return self.storage_dir / prefix / f"{doc_id}.json"

    def _load_all(self) -> None:
        for subdir in self.storage_dir.iterdir():
            if not subdir.is_dir() or len(subdir.name) != 2:
                continue
            for path in subdir.glob("*.json"):
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    doc = Document(**data)
                    self._docs[doc.id] = doc
                except Exception as e:
                    logger.warning(f"Failed to load document {path}: {e}")

    def _save_doc(self, doc: Document) -> None:
        path = self._doc_path(doc.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc.model_dump(), f, ensure_ascii=False, indent=2, default=str)

    def _delete_doc_file(self, doc_id: str) -> None:
        path = self._doc_path(doc_id)
        if path.exists():
            path.unlink()

    def save(self, doc: Document) -> Document:
        with self._lock:
            self._docs[doc.id] = doc
            self._save_doc(doc)
        return doc

    def get(self, doc_id: str) -> Document | None:
        return self._docs.get(doc_id)

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Document]:
        docs = sorted(self._docs.values(), key=lambda d: d.created_at, reverse=True)
        return docs[offset: offset + limit]

    def count(self) -> int:
        return len(self._docs)

    def delete(self, doc_id: str) -> bool:
        with self._lock:
            doc = self._docs.pop(doc_id, None)
            if doc:
                self._delete_doc_file(doc_id)
                return True
        return False

    def update(self, doc_id: str, **updates) -> Document | None:
        with self._lock:
            doc = self._docs.get(doc_id)
            if not doc:
                return None
            for key, value in updates.items():
                if hasattr(doc, key) and value is not None:
                    setattr(doc, key, value)
            from datetime import datetime
            doc.updated_at = datetime.now()
            self._save_doc(doc)
        return doc


_global_doc_store: DocumentStore | None = None
_doc_store_lock = threading.Lock()


def get_document_store() -> DocumentStore:
    global _global_doc_store
    if _global_doc_store is None:
        with _doc_store_lock:
            if _global_doc_store is None:
                _global_doc_store = DocumentStore()
    return _global_doc_store


def reset_document_store() -> None:
    global _global_doc_store
    _global_doc_store = DocumentStore()
