"""RAG 引擎 - 基于向量检索的增强生成

使用 TF-IDF 字符 n-gram 向量化（无需下载模型，离线可用，对中文友好），
支持余弦相似度检索、文档分块、索引持久化。
"""

import json
import logging
import re
import threading
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pm_workstation.knowledge_base.rag_models import (
    DocumentChunk,
    RAGContext,
    SearchResult,
)

logger = logging.getLogger(__name__)

_VECTORIZER_FILE = "vectorizer.joblib"
_VECTORS_FILE = "vectors.joblib"
_CHUNKS_FILE = "chunks.json"


def _split_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """将文本按段落/边界切分为指定大小的块

    优先按段落（空行）切分，段落过长时按句子边界回退，最后按固定长度切分。

    Args:
        text: 原始文本
        chunk_size: 块大小（字符数）
        overlap: 相邻块重叠字符数

    Returns:
        文本块列表
    """
    text = text.strip()
    if not text:
        return []

    # 按空行切分为段落
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) <= chunk_size:
            if len(current) + len(para) + 1 <= chunk_size:
                current = f"{current}\n{para}" if current else para
            else:
                if current:
                    chunks.append(current)
                current = para
        else:
            # 段落过长，按句子边界切分
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_paragraph(para, chunk_size, overlap))

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


def _split_long_paragraph(para: str, chunk_size: int, overlap: int) -> list[str]:
    """切分过长段落

    Args:
        para: 过长段落
        chunk_size: 块大小
        overlap: 重叠字符数

    Returns:
        切分后的块列表
    """
    sentences = re.split(r"(?<=[。！？.!?])\s*", para)
    sentences = [s for s in sentences if s.strip()]

    chunks: list[str] = []
    if len(sentences) == 1:
        # 无句子边界，按固定长度切分
        step = max(1, chunk_size - overlap)
        for i in range(0, len(para), step):
            chunks.append(para[i : i + chunk_size])
        return chunks

    current = ""
    for s in sentences:
        if len(current) + len(s) <= chunk_size:
            current += s
        else:
            if current:
                chunks.append(current)
                current = s
    if current:
        chunks.append(current)
    return chunks


class RAGEngine:
    """基于 TF-IDF 向量检索的 RAG 引擎

    线程安全：文档读写与检索分别加锁，避免并发冲突。
    """

    def __init__(self, storage_dir: str = "./data/rag"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._chunks: list[DocumentChunk] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._vectors: np.ndarray | None = None

        self._index_lock = threading.Lock()
        self._search_lock = threading.Lock()

        self._load()

    # ---------- 索引管理 ----------

    @property
    def chunk_count(self) -> int:
        """当前索引的块的数目"""
        return len(self._chunks)

    def _rebuild_index(self) -> None:
        """重建向量索引"""
        if not self._chunks:
            self._vectorizer = None
            self._vectors = None
            return

        texts = [chunk.content for chunk in self._chunks]

        self._vectorizer = TfidfVectorizer(
            max_features=20000,
            analyzer="char_wb",
            ngram_range=(2, 4),
            min_df=1,
            sublinear_tf=True,
        )
        self._vectors = self._vectorizer.fit_transform(texts).toarray()

    # ---------- 文档操作 ----------

    def add_document(self, doc_id: str, content: str, metadata: dict | None = None) -> list[str]:
        """添加文档并建立向量索引

        Args:
            doc_id: 文档 ID
            content: 文档内容
            metadata: 附加元数据

        Returns:
            生成的块 ID 列表
        """
        chunks = _split_text(content)
        new_chunks: list[DocumentChunk] = []
        for idx, text in enumerate(chunks):
            new_chunks.append(
                DocumentChunk(
                    doc_id=doc_id,
                    content=text,
                    chunk_index=idx,
                    metadata=metadata or {},
                )
            )

        with self._index_lock:
            self._chunks.extend(new_chunks)
            self._rebuild_index()
            self._save()

        return [c.chunk_id for c in new_chunks]

    def remove_document(self, doc_id: str) -> int:
        """移除文档及其所有块

        Args:
            doc_id: 文档 ID

        Returns:
            移除的块数量
        """
        with self._index_lock:
            before = len(self._chunks)
            self._chunks = [c for c in self._chunks if c.doc_id != doc_id]
            removed = before - len(self._chunks)
            if removed:
                self._rebuild_index()
                self._save()

        return removed

    def clear(self) -> None:
        """清空索引"""
        with self._index_lock:
            self._chunks = []
            self._vectorizer = None
            self._vectors = None
            self._save()

    # ---------- 检索 ----------

    def search(self, query: str, top_k: int = 5, min_score: float = 0.0) -> list[SearchResult]:
        """向量相似度检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            min_score: 最低相似度阈值

        Returns:
            按相似度降序的检索结果
        """
        query = (query or "").strip()
        if not query:
            return []

        with self._search_lock:
            if self._vectorizer is None or self._vectors is None or len(self._vectors) == 0:
                return []

            query_vec = self._vectorizer.transform([query]).toarray()
            similarities = cosine_similarity(query_vec, self._vectors)[0]

            # 取相似度前 top_k 的索引
            top_indices = np.argsort(similarities)[::-1][:top_k]

            results: list[SearchResult] = []
            for idx in top_indices:
                score = float(similarities[idx])
                if score < min_score:
                    continue
                chunk = self._chunks[idx]
                results.append(
                    SearchResult(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        content=chunk.content,
                        score=score,
                        metadata=chunk.metadata,
                    )
                )

            return results

    def retrieve_context(self, query: str, top_k: int = 5, max_chars: int = 4000) -> RAGContext:
        """检索并格式化上下文（供 LLM 注入）

        Args:
            query: 查询文本
            top_k: 返回结果数量
            max_chars: 上下文最大字符数

        Returns:
            RAGContext，包含格式化上下文与来源列表
        """
        results = self.search(query, top_k=top_k)
        if not results:
            return RAGContext(context="", sources=[])

        parts: list[str] = []
        total = 0
        for r in results:
            snippet = f"[文献 {r.doc_id}]\n{r.content}"
            if total + len(snippet) > max_chars:
                break
            parts.append(snippet)
            total += len(snippet)

        return RAGContext(context="\n\n".join(parts), sources=results)

    # ---------- 持久化 ----------

    def _save(self) -> None:
        """保存索引到磁盘"""
        try:
            joblib.dump(self._vectorizer, self.storage_dir / _VECTORIZER_FILE)
            joblib.dump(self._vectors, self.storage_dir / _VECTORS_FILE)
            with open(self.storage_dir / _CHUNKS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    [c.model_dump() for c in self._chunks],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError as e:
            logger.error(f"Failed to save RAG index: {e}")

    def _load(self) -> None:
        """从磁盘加载索引"""
        try:
            vectorizer_file = self.storage_dir / _VECTORIZER_FILE
            vectors_file = self.storage_dir / _VECTORS_FILE
            chunks_file = self.storage_dir / _CHUNKS_FILE

            if chunks_file.exists():
                with open(chunks_file, encoding="utf-8") as f:
                    data = json.load(f)
                self._chunks = [DocumentChunk(**d) for d in data]

            if vectorizer_file.exists() and vectors_file.exists():
                self._vectorizer = joblib.load(vectorizer_file)
                self._vectors = joblib.load(vectors_file)
            else:
                self._rebuild_index()
        except Exception as e:
            logger.error(f"Failed to load RAG index: {e}")
            self._chunks = []
            self._vectorizer = None
            self._vectors = None


_global_rag_engine: RAGEngine | None = None
_global_rag_lock = threading.Lock()


def get_rag_engine() -> RAGEngine:
    """获取全局 RAG 引擎单例"""
    global _global_rag_engine
    if _global_rag_engine is None:
        with _global_rag_lock:
            if _global_rag_engine is None:
                _global_rag_engine = RAGEngine()
    return _global_rag_engine


def reset_rag_engine() -> None:
    """重置 RAG 引擎（用于测试）"""
    global _global_rag_engine
    _global_rag_engine = RAGEngine()
