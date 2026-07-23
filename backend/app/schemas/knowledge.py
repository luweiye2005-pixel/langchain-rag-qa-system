"""
知识库管理相关 Pydantic 模型
"""
from pydantic import BaseModel, Field


class DocumentContentResponse(BaseModel):
    """文档内容响应"""
    document_id: str
    filename: str
    file_type: str
    content: str
    size: int


class UpdateContentRequest(BaseModel):
    """更新文档内容请求"""
    content: str = Field(..., min_length=1, description="新的文档内容")
