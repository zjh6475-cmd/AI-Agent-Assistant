import graph.project_graph as project_graph
from graph.prompts import SYSTEM_PROMPT
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


class FakeModel:
    """
    替代真实 llm_with_tools。

    它不请求模型 API，
    只记录 call_model 实际传给它的消息。
    """

    def __init__(self):
        self.received_messages = None

    def invoke(self, messages):
        self.received_messages = messages

        return AIMessage(
            content=(
                "抱歉，当前文档检索服务暂时不可用，"
                "暂时无法完成这次查询，请稍后重试。"
            )
        )


def test_call_model_receives_tool_error_and_error_rules(
    monkeypatch,
):
    """
    工具失败后再次进入 call_model 时：

    1. 第一条必须是带错误处理规则的 SystemMessage；
    2. 历史中必须保留失败 ToolMessage；
    3. FakeModel 能返回面向用户的友好回答。
    """

    fake_model = FakeModel()

    monkeypatch.setattr(
        project_graph,
        "llm_with_tools",
        fake_model,
    )

    user_message = HumanMessage(
        content="帮我总结上传的文档"
    )

    tool_request_message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_knowledge_base",
                "args": {
                    "query": "总结上传的文档",
                },
                "id": "call-error-1",
            }
        ],
    )

    tool_error_message = ToolMessage(
        content=(
            "Error: ConnectionError("
            "'向量数据库暂时不可用'"
            ")"
        ),
        name="search_knowledge_base",
        tool_call_id="call-error-1",
        status="error",
    )

    state = {
        "messages": [
            user_message,
            tool_request_message,
            tool_error_message,
        ],
    }

    result = project_graph.call_model(state)

    sent_messages = fake_model.received_messages

    # 第一条一定是系统提示词
    assert isinstance(
        sent_messages[0],
        SystemMessage,
    )

    # 验证我们刚加入的工具失败规则确实在提示词中
    system_prompt = sent_messages[0].content

    assert "工具失败处理规则" in system_prompt
    assert "不要编造工具本应返回的数据" in system_prompt
    assert "不要把原始异常" in system_prompt
    assert "稍后重试" in system_prompt

    # ToolMessage 必须原样传给模型，
    # 模型才能知道本轮工具执行失败。
    assert sent_messages[-1] is tool_error_message
    assert sent_messages[-1].status == "error"
    assert sent_messages[-1].tool_call_id == (
        "call-error-1"
    )

    # call_model 应返回 FakeModel 的最终回答
    answer_message = result["messages"][0]

    assert "暂时不可用" in answer_message.content
    assert "请稍后重试" in answer_message.content

    # 模型节点仍应记录正常执行步骤
    assert result["steps"][0]["name"] == "call_model"
    assert result["steps"][0]["status"] == "success"
    
def test_system_prompt_keeps_historical_tool_failures_truthful():
    assert "不得据此否定、改写或纠正历史中已经出现的工具失败" in SYSTEM_PROMPT    