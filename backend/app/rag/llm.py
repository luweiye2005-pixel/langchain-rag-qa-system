"""
LLM 集成 (DeepSeek / 本地 Ollama)
"""
import os
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from app.config import settings


def get_llm(**kwargs):
    """获取 LLM 实例，优先使用 DeepSeek API，回退到本地 Ollama"""
    if settings.DEEPSEEK_API_KEY:
        return _get_deepseek_llm(**kwargs)
    else:
        return _get_ollama_llm(**kwargs)


def _get_deepseek_llm(**kwargs) -> ChatOpenAI:
    """获取 DeepSeek LLM 实例"""
    default_kwargs = {
        "model": settings.DEEPSEEK_MODEL,
        "api_key": settings.DEEPSEEK_API_KEY,
        "base_url": settings.DEEPSEEK_BASE_URL,
        "temperature": 0.1,
        "max_tokens": 2048,
        "streaming": True,
    }
    default_kwargs.update(kwargs)
    return ChatOpenAI(**default_kwargs)


def _get_ollama_llm(**kwargs) -> ChatOllama:
    """获取本地 Ollama LLM 实例"""
    default_kwargs = {
        "model": settings.OLLAMA_LLM_MODEL,
        "base_url": settings.OLLAMA_BASE_URL,
        "temperature": 0.1,
        "num_predict": 2048,
    }
    default_kwargs.update(kwargs)
    return ChatOllama(**default_kwargs)
