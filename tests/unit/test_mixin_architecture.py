# -*- coding: utf-8 -*-
"""
BaseMCPTool Mixin架构 - 单元测试

验证Mixin拆分后的功能完整性：
- VersionedToolMixin: 版本管理
- CachedToolMixin: 缓存读写
- MonitoredToolMixin: 性能监控包装
- ThreeLayerQueryMixin: 三层检索
- BaseMCPTool: Mixin组合 + 抽象接口

Task 44 - Phase 7 Batch 4
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock
from pydantic import BaseModel
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from applications.fitness.mcp_tools.mixins.versioned import (
    VersionInfo, ChangelogEntry, VersionedToolMixin,
)
from applications.fitness.mcp_tools.mixins.cached import CachedToolMixin
from applications.fitness.mcp_tools.mixins.monitored import MonitoredToolMixin
from applications.fitness.mcp_tools.mixins.three_layer_query import (
    ThreeLayerQueryMixin, ThreeLayerQueryResult,
)
from applications.fitness.mcp_tools.base_tool import (
    BaseMCPTool, ToolMetadata, MCPToolVersionRegistry, get_version_registry,
)


def run_async(coro):
    return asyncio.run(coro)


# ─── 测试用具体工具 ──────────────────────────────────────

class DummyInput(BaseModel):
    query: str

class DummyOutput(BaseModel):
    result: str

class DummyTool(BaseMCPTool):
    """用于测试的具体工具实现"""

    _version = VersionInfo(2, 1, 0)
    _changelog = [
        ChangelogEntry("2.1.0", "2026-02-19", ["Mixin架构"]),
    ]

    def get_name(self) -> str:
        return "dummy_tool"

    def get_description(self) -> str:
        return "测试工具"

    def get_category(self) -> str:
        return "utility"

    def get_input_schema(self):
        return DummyInput

    def get_output_schema(self):
        return DummyOutput

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "data": {"result": "ok"}}


def _make_dummy_tool(**kwargs):
    defaults = dict(
        neo4j_client=MagicMock(),
        qdrant_client=MagicMock(),
        three_layer_engine=MagicMock(),
    )
    defaults.update(kwargs)
    return DummyTool(**defaults)


# ═══════════════════════════════════════════════════════════
# VersionedToolMixin 测试
# ═══════════════════════════════════════════════════════════

class TestVersionInfo:
    def test_str(self):
        v = VersionInfo(1, 2, 3)
        assert str(v) == "1.2.3"

    def test_eq(self):
        assert VersionInfo(1, 0, 0) == VersionInfo(1, 0, 0)
        assert VersionInfo(1, 0, 0) != VersionInfo(2, 0, 0)

    def test_lt(self):
        assert VersionInfo(1, 0, 0) < VersionInfo(2, 0, 0)
        assert VersionInfo(1, 1, 0) < VersionInfo(1, 2, 0)

    def test_compatible(self):
        v1 = VersionInfo(1, 0, 0)
        v2 = VersionInfo(1, 5, 3)
        v3 = VersionInfo(2, 0, 0)
        assert v1.is_compatible_with(v2) is True
        assert v1.is_compatible_with(v3) is False

    def test_from_string(self):
        v = VersionInfo.from_string("3.2.1")
        assert v == VersionInfo(3, 2, 1)

    def test_from_string_invalid(self):
        with pytest.raises(ValueError):
            VersionInfo.from_string("1.2")


class TestVersionedToolMixin:
    def test_get_version(self):
        tool = _make_dummy_tool()
        assert tool.get_version() == "2.1.0"

    def test_get_changelog(self):
        tool = _make_dummy_tool()
        cl = tool.get_changelog()
        assert len(cl) >= 1
        assert cl[0]["version"] == "2.1.0"

    def test_is_compatible(self):
        tool = _make_dummy_tool()
        assert tool.is_compatible_with_version("2.0.0") is True
        assert tool.is_compatible_with_version("3.0.0") is False


# ═══════════════════════════════════════════════════════════
# CachedToolMixin 测试
# ═══════════════════════════════════════════════════════════

class TestCachedToolMixin:
    def test_no_cache_manager_returns_none(self):
        tool = _make_dummy_tool(cache_manager=None)
        assert tool.get_cached("key") is None

    def test_no_cache_manager_set_returns_false(self):
        tool = _make_dummy_tool(cache_manager=None)
        assert tool.set_cached("key", "val") is False

    def test_get_cached_delegates(self):
        cm = MagicMock()
        cm.get.return_value = "cached_value"
        tool = _make_dummy_tool(cache_manager=cm)
        assert tool.get_cached("k1") == "cached_value"
        cm.get.assert_called_once_with("k1")

    def test_set_cached_with_ttl(self):
        cm = MagicMock()
        tool = _make_dummy_tool(cache_manager=cm)
        assert tool.set_cached("k1", "v1", ttl=60) is True
        cm.set.assert_called_once_with("k1", "v1", ttl=60)

    def test_invalidate_cached(self):
        cm = MagicMock()
        tool = _make_dummy_tool(cache_manager=cm)
        assert tool.invalidate_cached("k1") is True
        cm.delete.assert_called_once_with("k1")

    def test_cache_error_graceful(self):
        cm = MagicMock()
        cm.get.side_effect = Exception("Redis down")
        tool = _make_dummy_tool(cache_manager=cm)
        assert tool.get_cached("k1") is None  # 不抛异常


# ═══════════════════════════════════════════════════════════
# MonitoredToolMixin 测试
# ═══════════════════════════════════════════════════════════

class TestMonitoredToolMixin:
    def test_success_adds_metadata(self):
        tool = _make_dummy_tool()
        result = run_async(tool.execute_with_monitoring({"query": "test"}))
        assert result["success"] is True
        assert "metadata" in result
        assert result["metadata"]["tool_name"] == "dummy_tool"
        assert result["metadata"]["tool_version"] == "2.1.0"
        assert result["metadata"]["execution_time_ms"] >= 0

    def test_failure_returns_error_format(self):
        tool = _make_dummy_tool()
        # 传入无效输入触发验证错误
        result = run_async(tool.execute_with_monitoring({}))
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == "TOOL_EXECUTION_ERROR"


# ═══════════════════════════════════════════════════════════
# ThreeLayerQueryMixin 测试
# ═══════════════════════════════════════════════════════════

class TestThreeLayerQueryMixin:
    def test_no_engine_returns_failure(self):
        tool = _make_dummy_tool(three_layer_engine=None)
        result = run_async(tool.execute_three_layer_query("test query"))
        assert result.success is False
        assert "未初始化" in result.reasoning

    def test_engine_called_correctly(self):
        engine = MagicMock()
        # 模拟三层检索结果
        mock_result = MagicMock()
        mock_result.final_results = [{"name": "深蹲"}]
        mock_result.total_confidence = 0.85
        mock_result.reasoning = "ok"
        for layer in ("layer_1_result", "layer_2_result", "layer_3_result"):
            lr = MagicMock()
            lr.success = True
            lr.results = [{"name": "深蹲"}]
            lr.confidence = 0.9
            lr.execution_time_ms = 10.0
            setattr(mock_result, layer, lr)
        engine.execute_three_layer_query = AsyncMock(return_value=mock_result)

        tool = _make_dummy_tool(three_layer_engine=engine)
        result = run_async(tool.execute_three_layer_query("深蹲替代动作"))
        assert result.success is True
        assert len(result.results) == 1
        assert result.confidence == 0.85

    def test_engine_exception_triggers_fallback(self):
        engine = MagicMock()
        engine.execute_three_layer_query = AsyncMock(
            side_effect=Exception("Neo4j down")
        )
        tool = _make_dummy_tool(three_layer_engine=engine)
        result = run_async(tool.execute_three_layer_query("test"))
        assert result.success is False
        assert "Neo4j down" in result.reasoning


# ═══════════════════════════════════════════════════════════
# BaseMCPTool 组合测试
# ═══════════════════════════════════════════════════════════

class TestBaseMCPToolComposition:
    def test_has_all_mixin_methods(self):
        tool = _make_dummy_tool()
        # VersionedToolMixin
        assert hasattr(tool, "get_version")
        assert hasattr(tool, "get_changelog")
        # CachedToolMixin
        assert hasattr(tool, "get_cached")
        assert hasattr(tool, "set_cached")
        # MonitoredToolMixin
        assert hasattr(tool, "execute_with_monitoring")
        # ThreeLayerQueryMixin
        assert hasattr(tool, "execute_three_layer_query")

    def test_metadata_includes_version(self):
        tool = _make_dummy_tool()
        meta = tool.get_metadata()
        assert isinstance(meta, ToolMetadata)
        assert meta.version == "2.1.0"
        assert meta.name == "dummy_tool"
        assert meta.category == "utility"

    def test_mro_order(self):
        """验证MRO顺序：Mixins在ABC之前"""
        mro = [c.__name__ for c in DummyTool.__mro__]
        assert mro.index("VersionedToolMixin") < mro.index("ABC")
        assert mro.index("CachedToolMixin") < mro.index("ABC")
        assert mro.index("MonitoredToolMixin") < mro.index("ABC")
        assert mro.index("ThreeLayerQueryMixin") < mro.index("ABC")


# ═══════════════════════════════════════════════════════════
# MCPToolVersionRegistry 测试
# ═══════════════════════════════════════════════════════════

class TestMCPToolVersionRegistry:
    def test_register_and_query(self):
        registry = MCPToolVersionRegistry()
        registry._tools = {}  # 隔离测试
        tool = _make_dummy_tool()
        registry.register(tool)
        assert registry.get_tool_version("dummy_tool") == "2.1.0"

    def test_get_all_versions(self):
        registry = MCPToolVersionRegistry()
        registry._tools = {}
        tool = _make_dummy_tool()
        registry.register(tool)
        versions = registry.get_all_versions()
        assert "dummy_tool" in versions

    def test_check_compatibility(self):
        registry = MCPToolVersionRegistry()
        registry._tools = {}
        tool = _make_dummy_tool()
        registry.register(tool)
        ok, msg = registry.check_compatibility("dummy_tool", "2.0.0")
        assert ok is True
        ok, msg = registry.check_compatibility("dummy_tool", "3.0.0")
        assert ok is False

    def test_unknown_tool(self):
        registry = MCPToolVersionRegistry()
        registry._tools = {}
        assert registry.get_tool_version("nonexistent") is None
