import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ChunkingStrategy(StrEnum):
    PARAGRAPH = "paragraph"
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"


class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    doc_id: str
    content: str
    chunk_index: int = 0
    metadata: dict = Field(default_factory=dict)


class Document(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str
    content: str = ""
    source: str = ""
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    content: str
    score: float = 0.0
    metadata: dict = Field(default_factory=dict)


class RAGContext(BaseModel):
    context: str = ""
    sources: list[SearchResult] = Field(default_factory=list)
