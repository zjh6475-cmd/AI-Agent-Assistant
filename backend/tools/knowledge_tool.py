from langchain_core.tools import tool

from services.vector_service import search_chunks


MAX_K = 5


def create_knowledge_tool(user_id: int):
    @tool("search_knowledge_base")
    def search_knowledge_base(
        query: str,
        k: int = 3
    ) -> dict:
        """
    只用于检索当前用户已经上传的文档内容。

    只有当用户明确询问文档正文、
    技术细节、总结或文档重点时才调用。

    用户问候、询问身份、普通聊天时不要调用。
        """
        k = max(1, min(k, MAX_K))

        return search_chunks(
            query=query,
            user_id=user_id,
            k=k
        )

    return search_knowledge_base