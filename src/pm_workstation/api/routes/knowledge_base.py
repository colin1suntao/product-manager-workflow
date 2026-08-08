"""知识库 API - 产品文档模板和原型组件模板管理 + RAG 向量检索"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.knowledge_base.document_store import DocumentStore, get_document_store
from pm_workstation.knowledge_base.models import TEMPLATE_TYPE_LABELS, Template, TemplateType
from pm_workstation.knowledge_base.rag_engine import RAGEngine, get_rag_engine
from pm_workstation.knowledge_base.rag_models import Document
from pm_workstation.knowledge_base.store import TemplateStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-base", tags=["知识库"])

_store = TemplateStore()


def get_store() -> TemplateStore:
    return _store


class UploadDocumentRequest(BaseModel):
    """上传文档请求"""
    title: str = Field(..., min_length=1, max_length=500, description="文档标题")
    content: str = Field(..., min_length=1, description="文档内容")
    source: str = Field(default="", max_length=500, description="来源")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    metadata: dict = Field(default_factory=dict, description="附加元数据")


class SearchRequest(BaseModel):
    """向量搜索请求"""
    query: str = Field(..., min_length=1, description="查询文本")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="最低相似度阈值")


class RAGRetrieveRequest(BaseModel):
    """RAG 检索请求"""
    query: str = Field(..., min_length=1, description="查询文本")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    max_chars: int = Field(default=4000, ge=100, le=20000, description="上下文最大字符数")


@router.get("/templates", summary="获取模板列表")
async def list_templates(
    type: str | None = None,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    type_filter = None
    if type:
        try:
            type_filter = TemplateType(type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支持的模板类型: {type}")

    templates = await store.list_all(type_filter)
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "type": t.type.value,
                "type_label": TEMPLATE_TYPE_LABELS.get(t.type, t.type.value),
                "tags": t.tags,
                "content_preview": t.content[:200] + "..." if len(t.content) > 200 else t.content,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
            for t in templates
        ],
        "total": len(templates),
    }


@router.get("/templates/{template_id}", summary="获取模板详情")
async def get_template(
    template_id: str,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    template = await store.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "type": template.type.value,
        "type_label": TEMPLATE_TYPE_LABELS.get(template.type, template.type.value),
        "content": template.content,
        "tags": template.tags,
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat(),
    }


@router.post("/templates", summary="创建模板")
async def create_template(
    body: dict,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="模板名称不能为空")

    type_str = body.get("type", "").strip()
    try:
        template_type = TemplateType(type_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的模板类型: {type_str}")

    template = Template(
        name=name,
        description=body.get("description", ""),
        type=template_type,
        content=body.get("content", ""),
        tags=body.get("tags", []),
    )

    result = await store.create(template)
    return {
        "id": result.id,
        "name": result.name,
        "type": result.type.value,
        "message": f"模板 '{result.name}' 创建成功",
    }


@router.put("/templates/{template_id}", summary="更新模板")
async def update_template(
    template_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    existing = await store.get(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="模板不存在")

    updates = {}
    for field in ("name", "description", "content", "tags"):
        if field in body:
            updates[field] = body[field]

    result = await store.update(template_id, updates)
    return {
        "id": result.id,
        "name": result.name,
        "message": "模板已更新",
    }


@router.delete("/templates/{template_id}", summary="删除模板")
async def delete_template(
    template_id: str,
    user_id: str = Depends(get_current_user),
    store: TemplateStore = Depends(get_store),
) -> dict:
    deleted = await store.delete(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"message": "模板已删除"}


@router.get("/types", summary="获取模板类型列表")
async def get_template_types(
    user_id: str = Depends(get_current_user),
) -> dict:
    return {
        "types": [
            {"value": t.value, "label": TEMPLATE_TYPE_LABELS[t]}
            for t in TemplateType
        ]
    }


# ======================== RAG 文档管理 ========================


@router.post("/documents", summary="上传文档")
async def upload_document(
    body: UploadDocumentRequest,
    user_id: str = Depends(get_current_user),
    doc_store: DocumentStore = Depends(get_document_store),
    rag: RAGEngine = Depends(get_rag_engine),
) -> dict:
    """上传文档，自动分块并建立向量索引"""
    doc = Document(
        title=body.title,
        content=body.content,
        source=body.source,
        tags=body.tags,
        metadata=body.metadata,
    )
    doc_store.save(doc)
    chunk_ids = rag.add_document(doc.id, body.content, {"source": body.source})
    doc.chunk_count = len(chunk_ids)
    doc_store.save(doc)

    return {
        "id": doc.id,
        "title": doc.title,
        "chunks": len(chunk_ids),
        "message": f"文档 '{doc.title}' 上传成功，已切分为 {len(chunk_ids)} 个块",
    }


@router.get("/documents", summary="文档列表")
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    doc_store: DocumentStore = Depends(get_document_store),
    rag: RAGEngine = Depends(get_rag_engine),
) -> dict:
    """获取已上传的文档列表"""
    offset = (page - 1) * page_size
    docs = doc_store.list_all(limit=page_size, offset=offset)
    total = doc_store.count()

    return {
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "source": d.source,
                "tags": d.tags,
                "chunk_count": d.chunk_count,
                "content_preview": d.content[:200] + "..." if len(d.content) > 200 else d.content,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
            }
            for d in docs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_chunks": rag.chunk_count,
    }


@router.get("/documents/{doc_id}", summary="获取文档详情")
async def get_document(
    doc_id: str,
    user_id: str = Depends(get_current_user),
    doc_store: DocumentStore = Depends(get_document_store),
) -> dict:
    doc = doc_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    return {
        "id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "source": doc.source,
        "tags": doc.tags,
        "metadata": doc.metadata,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }


@router.delete("/documents/{doc_id}", summary="删除文档")
async def delete_document(
    doc_id: str,
    user_id: str = Depends(get_current_user),
    doc_store: DocumentStore = Depends(get_document_store),
    rag: RAGEngine = Depends(get_rag_engine),
) -> dict:
    doc = doc_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    doc_store.delete(doc_id)
    removed = rag.remove_document(doc_id)
    return {"message": f"文档已删除，移除 {removed} 个向量块"}


# ======================== 向量检索 & RAG ========================


@router.post("/search", summary="向量搜索")
async def search_documents(
    body: SearchRequest,
    user_id: str = Depends(get_current_user),
    rag: RAGEngine = Depends(get_rag_engine),
) -> dict:
    """使用 TF-IDF 字符 n-gram 向量相似度搜索文档"""
    results = rag.search(body.query, top_k=body.top_k, min_score=body.min_score)

    return {
        "results": [
            {
                "chunk_id": r.chunk_id,
                "doc_id": r.doc_id,
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
        ],
        "total": len(results),
    }


@router.post("/rag/retrieve", summary="RAG 检索上下文")
async def rag_retrieve(
    body: RAGRetrieveRequest,
    user_id: str = Depends(get_current_user),
    rag: RAGEngine = Depends(get_rag_engine),
) -> dict:
    """RAG 检索：搜索相关文档片段并格式化为 LLM 上下文"""
    ctx = rag.retrieve_context(body.query, top_k=body.top_k, max_chars=body.max_chars)

    return {
        "context": ctx.context,
        "sources": [
            {
                "chunk_id": s.chunk_id,
                "doc_id": s.doc_id,
                "score": s.score,
                "content": s.content[:300] + "..." if len(s.content) > 300 else s.content,
            }
            for s in ctx.sources
        ],
        "source_count": len(ctx.sources),
    }
