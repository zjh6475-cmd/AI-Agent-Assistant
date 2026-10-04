from dataclasses import FrozenInstanceError

import pytest

from graph.agent_context import AgentContext


def test_agent_context_user_id_is_immutable():
    """
    Agent 运行期间，
    用户身份上下文不能被意外修改。
    """

    context = AgentContext(
        user_id=7,
    )

    assert context.user_id == 7

    with pytest.raises(FrozenInstanceError):
        context.user_id = 999