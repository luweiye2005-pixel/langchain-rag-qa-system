"""
通义千问 LLM 集成
"""
from langchain_community.chat_models.tongyi import ChatTongyi
from app.config import settings


def get_llm(**kwargs) -> ChatTongyi:
    """获取通义千问 LLM 实例"""
    default_kwargs = {
        "model": settings.TONGYI_MODEL,
        "dashscope_api_key": settings.TONGYI_API_KEY,
        "temperature": 0.1,
        "max_tokens": 2048,
        "streaming": True,
    }
    default_kwargs.update(kwargs)
    return ChatTongyi(**default_kwargs)
