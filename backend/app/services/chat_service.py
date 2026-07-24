"""
RAG 问答核心服务
"""
import asyncio
from typing import AsyncGenerator, Dict, List, Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.rag.llm import get_llm
from app.rag.embeddings import get_embeddings
from app.rag.vector_store import get_vector_store
from app.schemas.chat import ChatHistoryMessage
from loguru import logger

# 余弦距离阈值：score=0表示完全相同，score=1表示完全无关
# Chroma 使用 cosine 距离度量，超过此阈值的文档片段视为不相关
# 注意：此阈值需根据实际 embedding 模型和业务场景调整
RELEVANCE_THRESHOLD = 0.55
# 每次检索返回的最相关文档片段数量
TOP_K_RESULTS = 5


class ChatService:
    """RAG 问答服务"""

    def __init__(self):
        self._llm = None
        self._embeddings = None
        self._vector_store = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = get_embeddings()
        return self._embeddings

    @property
    def vector_store(self):
        if self._vector_store is None:
            self._vector_store = get_vector_store(self.embeddings)
        return self._vector_store

    async def stream_chat(
        self,
        question: str,
        conversation_id: str,
        history: List[ChatHistoryMessage] | None = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式问答，逐 token 返回

        Yields events:
            {"type": "token", "content": "..."}
            {"type": "sources", "documents": [...]}
            {"type": "done"}
            {"type": "error", "message": "..."}
        """
        try:
            # 1. 检索相关文档（同步 Embedding/Chroma，放到线程避免卡住事件循环）
            retrieved_docs = []
            try:
                retrieved_docs = await asyncio.to_thread(
                    self.vector_store.similarity_search_with_score,
                    question,
                    TOP_K_RESULTS,
                )
            except Exception as e:
                logger.warning(f"Vector search failed: {e}, answering without knowledge base")

            sources = []
            context_parts = []

            for i, (doc, score) in enumerate(retrieved_docs):
                if score > RELEVANCE_THRESHOLD:
                    continue

                doc_name = doc.metadata.get("filename", "unknown")
                chunk_text = doc.page_content[:300]
                source_idx = len(sources) + 1

                sources.append({
                    "doc_id": doc.metadata.get("document_id", ""),
                    "doc_name": doc_name,
                    "chunk_id": doc.metadata.get("chunk_index", str(i)),
                    "content_snippet": chunk_text,
                    "score": round(float(score), 4),
                    "citation_index": source_idx,
                })

                context_parts.append(
                    f"[来源 {source_idx}: {doc_name}]\n{doc.page_content}\n"
                )

            context = "\n".join(context_parts) if context_parts else "暂无相关参考资料"

            # 2. 构建 Prompt Messages
            system_prompt = (
                "你是电商商品知识库助手。请**仅根据**以下提供的参考资料回答用户问题。\n"
                "如果参考资料中没有相关信息，请如实告知用户'该问题在知识库中暂未找到相关信息'，"
                "不要编造答案。\n"
                "回答时，引用具体的资料来源编号（如 [1], [2]），让用户知道信息出处。\n"
                "回答要专业、准确、简洁。"
            )

            messages = [SystemMessage(content=system_prompt)]
            for message in history or []:
                if message.role == "assistant":
                    messages.append(AIMessage(content=message.content))
                else:
                    messages.append(HumanMessage(content=message.content))
            messages.append(
                HumanMessage(content=f"参考资料:\n{context}\n\n用户问题: {question}")
            )

            # 3. 流式生成 - 使用 LangChain astream
            full_content = ""
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, str):
                        full_content += content
                        yield {"type": "token", "content": content}

            # 4. 返回引用来源
            if sources:
                yield {"type": "sources", "documents": sources}

            # 5. 完成
            yield {"type": "done"}

        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            yield {"type": "error", "message": "问答处理暂时不可用，请稍后重试"}
