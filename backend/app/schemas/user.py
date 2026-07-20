"""
用户相关 Pydantic 模型
"""
from pydantic import BaseModel, Field
from datetime import datetime


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """用户信息更新"""
    email: str | None = Field(None, max_length=100)
