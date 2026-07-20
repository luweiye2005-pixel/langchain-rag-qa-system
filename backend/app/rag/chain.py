"""
LangChain RAG Chain 构建
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough


def build_rag_chain(llm, retriever):
    """
    构建标准 RAG 链 (用于非流式场景)

    Args:
        llm: ChatModel 实例
        retriever: Retriever 实例

    Returns:
        LCEL Chain
    """
    template = """你是电商商品知识库助手。请仅根据以下提供的参考资料回答用户问题。
如果参考资料中没有相关信息，请如实告知用户"该问题在知识库中暂未找到相关信息"，不要编造答案。

参考资料:
{context}

用户问题: {question}

请用专业、准确的语言回答，引用时标注来源编号如 [1], [2]。"""

    prompt = ChatPromptTemplate.from_template(template)

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain
