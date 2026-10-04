
from tools.sql_tool import run_sql_tool
#路由判断测试通过；
#普通问题不会误调用知识库；
#未知用户无法查询到文档；
#用户数据隔离正常。

import pytest
def test_unknown_user_has_no_documents():
    result = run_sql_tool(
        action="document_count",
        user_id=999999
    )

    rows = result["rows"]

    assert len(rows) == 1
    assert rows[0]["count"] == 0


def test_unknown_user_has_no_recent_documents():
    result = run_sql_tool(
        action="recent_documents",
        user_id=999999
    )

    assert result["rows"] == []
    
def test_invalid_action_is_rejected(): 
    with pytest.raises(ValueError):
        run_sql_tool(
            action="drop_table",
            user_id=2
        )    
#用户输入非法 action
 #不执行 SQL
 #抛出 ValueError
   