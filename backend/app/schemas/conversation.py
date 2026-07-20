"""
会话相关 Pydantic 模型
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List


class ConversationCreate(BaseModel):
    """创建会话"""
    title: str = Field(default="新对话", max_length=200)


class ConversationUpdate(BaseModel):
    """更新会话"""
    title: str | None = Field(None, max_length=200)
    is_archived: bool | None = None
    is_pinned: bool | None = None


class ConversationResponse(BaseModel):
    """会话响应"""
    id: str
    user_id: str
    title: str
    is_archived: bool
    is_pinned: bool | None = False
    message_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """会话列表响应"""
    conversations: List[ConversationResponse]
    total: int
