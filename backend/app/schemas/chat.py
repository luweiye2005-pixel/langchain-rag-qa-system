"""
聊天相关 Pydantic 模型
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List


class ChatRequest(BaseModel):
    """发送消息请求"""
    conversation_id: str | None = Field(None, description="会话 ID（新会话则为空）")
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")


class SourceDocument(BaseModel):
    """引用的知识库文档"""
    doc_id: str
    doc_name: str
    chunk_id: str
    content_snippet: str
    score: float


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    conversation_id: str
    role: str
    content: str
    sources: List[SourceDocument] | None = None
    token_count: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
