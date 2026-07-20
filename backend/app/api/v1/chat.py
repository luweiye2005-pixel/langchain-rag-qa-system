"""
问答聊天 API (SSE 流式响应)
"""
import json
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from loguru import logger

router = APIRouter()

# Global chat service instance (initialized on first use)
chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    global chat_service
    if chat_service is None:
        chat_service = ChatService()
    return chat_service


@router.post("")
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    发送消息并获取流式回答 (SSE)

    SSE 事件类型:
    - token: 增量文本
    - sources: 引用来源 (流结束时)
    - done: 流结束
    - error: 错误消息
    """
    # Validate or create conversation
    conversation = None
    is_new = False
    if request.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    # If no valid conversation found, create a new one
    if conversation is None:
        is_new = True
        conversation = Conversation(
            user_id=current_user.id,
            title="新对话",
        )
        db.add(conversation)
        await db.flush()
        logger.info(f"Created new conversation: {conversation.id}")

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=request.message,
    )
    db.add(user_message)

    # Auto-generate title from first message
    if conversation.message_count == 0 and request.message:
        conversation.title = (
            request.message[:50] + "..." if len(request.message) > 50 else request.message
        )

    conversation.message_count += 1
    await db.flush()
    # Commit immediately so other requests can see the conversation
    await db.commit()

    service = get_chat_service()

    async def generate_sse() -> AsyncGenerator[str, None]:
        """SSE 流生成器"""
        full_response = ""
        sources = []

        try:
            async for event in service.stream_chat(
                question=request.message,
                conversation_id=conversation.id,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    full_response += event.get("content", "")
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                elif event_type == "sources":
                    sources = event.get("documents", [])
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                elif event_type == "done":
                    # Save assistant message
                    assistant_msg = Message(
                        conversation_id=conversation.id,
                        user_id=current_user.id,
                        role="assistant",
                        content=full_response,
                        sources=sources if sources else None,
                        token_count=len(full_response),  # Approximate
                    )
                    db.add(assistant_msg)
                    conversation.message_count += 1
                    await db.commit()

                    # Include conversation_id in done event for new conversations
                    done_event = {"type": "done"}
                    if is_new:
                        done_event["conversation_id"] = conversation.id
                    yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"

                elif event_type == "error":
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )
