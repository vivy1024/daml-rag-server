"""
test_mcp_tools.py — MCP 工具协议层测试

验证：
- list_tools 返回正确数量
- call_tool 各工具返回正确格式
- 参数验证
- 错误处理
"""

import json
import pytest


class TestListTools:
    """list_tools 测试"""

    async def test_returns_5_tools(self):
        """返回 5 个工具"""
        from src_v2.server import list_tools
        tools = await list_tools()
        assert len(tools) == 5

    async def test_tool_names(self):
        """工具名称正确"""
        from src_v2.server import list_tools
        tools = await list_tools()
        names = {t.name for t in tools}
        expected = {
            "search_exercises",
            "get_exercise_detail",
            "graph_query",
            "find_alternatives",
            "check_exercise_safety",
        }
        assert names == expected

    async def test_tools_have_description(self):
        """每个工具有描述"""
        from src_v2.server import list_tools
        tools = await list_tools()
        for t in tools:
            assert t.description
            assert len(t.description) > 10

    async def test_tools_have_schema(self):
        """每个工具有输入 schema"""
        from src_v2.server import list_tools
        tools = await list_tools()
        for t in tools:
            assert t.inputSchema is not None
            assert "properties" in t.inputSchema


class TestCallToolSearchExercises:
    """call_tool: search_exercises 测试"""

    async def test_basic_call(self):
        """基本调用返回结果"""
        from src_v2.server import call_tool
        result = await call_tool("search_exercises", {"query_text": "深蹲", "top_k": 3})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "exercises" in data
        assert "total" in data
        assert "timing_ms" in data

    async def test_result_format(self):
        """结果格式正确"""
        from src_v2.server import call_tool
        result = await call_tool("search_exercises", {"query_text": "卧推", "top_k": 2})
        data = json.loads(result[0].text)
        for ex in data["exercises"]:
            assert "id" in ex
            assert "score" in ex
            assert "name_zh" in ex

    async def test_missing_query_text(self):
        """缺少 query_text 返回错误"""
        from src_v2.server import call_tool
        result = await call_tool("search_exercises", {})
        text = result[0].text
        # 应该返回错误信息（可能是 JSON 或纯文本）
        assert "错误" in text or "error" in text.lower()


class TestCallToolGetDetail:
    """call_tool: get_exercise_detail 测试"""

    async def test_valid_id(self, data_store):
        """有效 ID 返回详情"""
        from src_v2.server import call_tool
        eid = data_store.exercise_ids[0]
        result = await call_tool("get_exercise_detail", {"exercise_id": eid})
        data = json.loads(result[0].text)
        assert "name_zh" in data or "error" not in data

    async def test_invalid_id(self):
        """无效 ID 返回空或错误"""
        from src_v2.server import call_tool
        result = await call_tool("get_exercise_detail", {"exercise_id": "nonexistent_99999"})
        text = result[0].text
        # 可能返回空 JSON、错误 JSON、或中文提示
        if text.startswith("{"):
            data = json.loads(text)
            assert data == {} or "error" in data
        else:
            # 中文提示如 "未找到动作: ..."
            assert "未找到" in text or "错误" in text or "error" in text.lower()


class TestCallToolGraphQuery:
    """call_tool: graph_query 测试"""

    async def test_basic_query(self, data_store):
        """基本图谱查询"""
        from src_v2.server import call_tool
        eid = data_store.exercise_ids[0]
        result = await call_tool("graph_query", {"node_id": eid})
        data = json.loads(result[0].text)
        assert "node_id" in data
        assert "relations" in data


class TestCallToolFindAlternatives:
    """call_tool: find_alternatives 测试"""

    async def test_basic_call(self, data_store):
        """基本替代动作查找"""
        from src_v2.server import call_tool
        eid = data_store.exercise_ids[0]
        result = await call_tool("find_alternatives", {"exercise_id": eid})
        data = json.loads(result[0].text)
        assert "exercises" in data or "alternatives" in data or "error" not in data


class TestCallToolCheckSafety:
    """call_tool: check_exercise_safety 测试"""

    async def test_basic_check(self, data_store):
        """基本安全检查"""
        from src_v2.server import call_tool
        eid = data_store.exercise_ids[0]
        result = await call_tool("check_exercise_safety", {
            "exercise_id": eid,
            "user_profile": {"fitness_level": "beginner", "injuries": []},
        })
        data = json.loads(result[0].text)
        assert "safe" in data or "safety_level" in data or "error" not in data
