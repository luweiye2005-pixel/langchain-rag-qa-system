"""
应用配置管理
使用 pydantic-settings 从环境变量加载配置
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """应用配置"""

    # ===== Database =====
    DATABASE_URL: str = "postgresql+asyncpg://raguser:ragpass@localhost:5432/ragdb"

    # ===== LLM (通义千问) =====
    TONGYI_API_KEY: str = "sk-your-tongyi-api-key"
    TONGYI_MODEL: str = "qwen-max"

    # ===== Embedding (Ollama) =====
    EMBEDDING_MODEL: str = "bge-m3"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ===== JWT =====
    JWT_SECRET: str = "change-me-to-a-random-secret-at-least-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

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
