"""
通义千问 LLM 集成
"""
from langchain_community.chat_models.tongyi import ChatTongyi
from app.config import settings


def get_llm(**kwargs) -> ChatTongyi:
    """获取通义千问 LLM 实例。"""
    if not settings.OPENAI_API_KEY:
        raise ValueError(
            "缺少 OPENAI_API_KEY，请将阿里云百炼的通义千问 API Key 配置到该环境变量。"
        )

    default_kwargs = {
        "model": settings.TONGYI_MODEL,
        "dashscope_api_key": settings.OPENAI_API_KEY,
        "temperature": 0.1,
        "max_tokens": 2048,
        "streaming": True,
    }
    default_kwargs.update(kwargs)
    return ChatTongyi(**default_kwargs)
