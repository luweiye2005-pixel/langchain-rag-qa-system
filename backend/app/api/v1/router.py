"""
API v1 路由聚合
"""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.chat import router as chat_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.voice import router as voice_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(users_router, prefix="/users", tags=["用户"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["会话"])
api_router.include_router(chat_router, prefix="/chat", tags=["问答"])
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(voice_router, prefix="/voice", tags=["语音"])
