"""
Embedding 模型管理

默认使用阿里云百炼（通义）文本向量 API，与 LLM 共用 OPENAI_API_KEY。
也可通过 EMBEDDING_PROVIDER=ollama 回退到本地 Ollama。
"""
from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import DashScopeEmbeddings, OllamaEmbeddings
from app.config import settings


def get_embeddings() -> Embeddings:
    """获取 Embeddings 实例（默认 DashScope / 千问）。"""
    provider = (settings.EMBEDDING_PROVIDER or "dashscope").strip().lower()

    if provider == "ollama":
        return OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

    if provider not in {"dashscope", "tongyi", "qwen"}:
        raise ValueError(
            f"不支持的 EMBEDDING_PROVIDER={settings.EMBEDDING_PROVIDER!r}，"
            "请使用 dashscope 或 ollama。"
        )

    if not settings.OPENAI_API_KEY:
        raise ValueError(
            "缺少 OPENAI_API_KEY，无法调用千问 Embedding；"
            "请配置阿里云百炼 API Key，或设置 EMBEDDING_PROVIDER=ollama。"
        )

    return DashScopeEmbeddings(
        model=settings.EMBEDDING_MODEL,
        dashscope_api_key=settings.OPENAI_API_KEY,
    )
