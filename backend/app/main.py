"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.config import settings
from app.core.database import Base, async_engine
from app.core.redis import init_redis, close_redis
from app.api.v1.router import api_router
from app.services.auth_service import seed_admin_user
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    logger.info("Starting RAG Knowledge Base Q&A System...")

    # Validate critical configuration
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be set in environment or .env file")
    if len(settings.JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")

    # Create database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")

    # Initialize Redis
    await init_redis()
    logger.info("Redis connected")

    # Create default admin user
    await seed_admin_user()
    logger.info("Admin account initialized successfully")

    yield

    # Shutdown
    await close_redis()
    await async_engine.dispose()
    logger.info("System shutdown complete")


app = FastAPI(
    title="RAG Enterprise Knowledge Base Q&A System",
    description="LangChain + Tongyi Qwen RAG knowledge base Q&A platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Register API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "RAG Enterprise Knowledge Base Q&A System",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
