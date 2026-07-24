"""
应用配置管理
使用 pydantic-settings 从环境变量加载配置
"""
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """应用配置"""

    # ===== Database =====
    DATABASE_URL: str = ""

    # ===== LLM (通义千问) =====
    # 填入阿里云百炼 API Key；名称与统一部署环境变量保持一致。
    OPENAI_API_KEY: str = Field(default="")
    TONGYI_MODEL: str = "qwen-max"

    # ===== Voice (DashScope ASR / CosyVoice TTS) =====
    TTS_MODEL: str = "cosyvoice-v3-flash"
    TTS_VOICE: str = "longxiaochun_v3"

    # Ollama：仅在 EMBEDDING_PROVIDER=ollama 时使用
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ===== Embedding =====
    # dashscope（默认，通义文本向量）或 ollama（本地）
    EMBEDDING_PROVIDER: str = "dashscope"
    # 百炼常用：text-embedding-v3 / text-embedding-v2；Ollama 常用：bge-m3
    EMBEDDING_MODEL: str = "text-embedding-v3"

    # ===== Celery =====
    # 本地默认关闭：无 Redis/Worker 时 Celery.delay 会阻塞并拖垮 API。
    # Docker 部署且运行 celery worker 时设 USE_CELERY=true。
    USE_CELERY: bool = False

    # ===== JWT =====
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    INITIAL_ADMIN_USERNAME: str = ""
    INITIAL_ADMIN_EMAIL: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""

    # ===== Redis =====
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_BROKER_URL: str = "redis://localhost:6379/1"

    # ===== Chroma =====
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"

    # ===== Upload =====
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ===== Features =====
    ENABLE_HYBRID_SEARCH: bool = False
    ENABLE_RERANKING: bool = False

    # ===== Rate Limit =====
    RATE_LIMIT_CHAT_PER_MINUTE: int = 20
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5

    # ===== CORS =====
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # ===== Logging =====
    LOG_LEVEL: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
