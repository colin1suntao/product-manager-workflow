"""RAG 引擎与文档存储测试"""

import tempfile
from pathlib import Path

import pytest

from pm_workstation.knowledge_base.rag_engine import RAGEngine
from pm_workstation.knowledge_base.document_store import DocumentStore
from pm_workstation.knowledge_base.rag_models import Document


class TestRAGEngine:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.rag = RAGEngine(storage_dir=f"{self.tmpdir}/rag")

    def test_empty_engine(self):
        assert self.rag.chunk_count == 0
        assert self.rag.search("anything") == []
        ctx = self.rag.retrieve_context("anything")
        assert ctx.context == ""

    def test_add_document(self):
        chunk_ids = self.rag.add_document("doc-1", "检索增强生成（RAG）是一种 AI 技术。")
        assert len(chunk_ids) == 1
        assert self.rag.chunk_count == 1

    def test_search(self):
        self.rag.add_document("doc-1", "RAG 技术结合检索与生成，让 AI 更准确。")
        self.rag.add_document("doc-2", "向量检索通过余弦相似度找到最相关的内容。")

        results = self.rag.search("RAG 检索", top_k=3)
        assert len(results) == 2
        assert results[0].score > 0.01

    def test_remove_document(self):
        self.rag.add_document("doc-1", "内容 A")
        self.rag.add_document("doc-2", "内容 B")
        assert self.rag.chunk_count == 2

        removed = self.rag.remove_document("doc-1")
        assert removed == 1
        assert self.rag.chunk_count == 1

    def test_clear(self):
        self.rag.add_document("doc-1", "内容 A")
        self.rag.add_document("doc-2", "内容 B")
        self.rag.clear()
        assert self.rag.chunk_count == 0
        assert self.rag.search("anything") == []

    def test_retrieve_context(self):
        self.rag.add_document("doc-1", "这是关于产品需求文档的说明。")
        ctx = self.rag.retrieve_context("产品需求", top_k=3)
        assert ctx.context
        assert len(ctx.sources) > 0
        assert ctx.sources[0].doc_id == "doc-1"

    def test_persistence(self):
        self.rag.add_document("doc-1", "持久化测试内容")
        chunk_count = self.rag.chunk_count

        rag2 = RAGEngine(storage_dir=f"{self.tmpdir}/rag")
        assert rag2.chunk_count == chunk_count, "索引加载失败"
        results = rag2.search("持久化测试", top_k=1)
        assert len(results) == 1

    def test_chinese_search(self):
        self.rag.add_document("doc-prd", "产品需求文档（PRD）是产品经理的核心文档，包含功能需求、用户故事、验收标准。")
        self.rag.add_document("doc-proto", "原型设计是产品设计阶段的关键产出，包含页面布局、交互流程。")

        results = self.rag.search("产品需求文档怎么写", top_k=1)
        assert results[0].doc_id == "doc-prd"

        results = self.rag.search("原型设计工具", top_k=1)
        assert results[0].doc_id == "doc-proto"

    def test_split_text(self):
        from pm_workstation.knowledge_base.rag_engine import _split_text

        chunks = _split_text("第一段内容。\n\n第二段内容。\n\n第三段内容。", chunk_size=100)
        assert len(chunks) >= 1

        long_chunks = _split_text("A" * 200 + "\n\n" + "B" * 200, chunk_size=100)
        assert len(long_chunks) >= 2


class TestDocumentStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = DocumentStore(storage_dir=f"{self.tmpdir}/docs")

    def test_save_and_get(self):
        doc = Document(title="测试文档", content="测试内容")
        self.store.save(doc)

        loaded = self.store.get(doc.id)
        assert loaded is not None
        assert loaded.title == "测试文档"
        assert loaded.content == "测试内容"

    def test_list_all(self):
        doc1 = Document(title="文档 1", content="内容 1")
        doc2 = Document(title="文档 2", content="内容 2")
        self.store.save(doc1)
        self.store.save(doc2)

        docs = self.store.list_all()
        assert len(docs) == 2

    def test_delete(self):
        doc = Document(title="待删除", content="内容")
        self.store.save(doc)
        assert self.store.delete(doc.id) is True
        assert self.store.count() == 0
        assert self.store.delete("nonexistent") is False

    def test_update(self):
        doc = Document(title="原始标题", content="原始内容")
        self.store.save(doc)

        updated = self.store.update(doc.id, title="新标题")
        assert updated is not None
        assert updated.title == "新标题"
        assert updated.content == "原始内容"

    def test_persistence(self):
        doc = Document(title="持久化文档", content="持久化内容")
        self.store.save(doc)
        doc_id = doc.id

        store2 = DocumentStore(storage_dir=f"{self.tmpdir}/docs")
        loaded = store2.get(doc_id)
        assert loaded is not None
        assert loaded.title == "持久化文档"