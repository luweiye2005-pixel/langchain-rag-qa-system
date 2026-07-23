"""
应用配置管理
使用 pydantic-settings 从环境变量加载配置
"""
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """应用配置"""

    # ===== Database =====
    DATABASE_URL: str = ""

    # ===== LLM (DeepSeek 优先，本地 Ollama 回退) =====
    DEEPSEEK_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"),
    )
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # 通义千问（备用，可选配置）
    TONGYI_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("TONGYI_API_KEY", "OPENAI_API_KEY"),
    )
    TONGYI_MODEL: str = "qwen-max"

    # Ollama 本地模型（无 API 时的回退方案）
    OLLAMA_LLM_MODEL: str = "qwen3:4b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ===== Embedding (Ollama) =====
    EMBEDDING_MODEL: str = "bge-m3"

    # ===== JWT =====
    JWT_SECRET: str = ""
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
