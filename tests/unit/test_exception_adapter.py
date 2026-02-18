# -*- coding: utf-8 -*-
"""
异常层级统一 - LegacyExceptionAdapter 单元测试

验证旧异常到 DAMLRAGError 子类的映射正确性。
Task 37 - Phase 7 Batch 2 系统一致性
"""

import pytest
import warnings
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from framework.exceptions import (
    DAMLRAGError,
    ToolExecutionError,
    ValidationError,
    TimeoutError,
    ConnectionError,
    LegacyExceptionAdapter,
)


class TestLegacyExceptionAdapter:
    """LegacyExceptionAdapter 映射测试"""

    def test_tool_error_maps_to_tool_execution_error(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from applications.fitness.mcp_tools.exceptions import ToolError
            legacy = ToolError("test error", tool_name="test_tool")

        result = LegacyExceptionAdapter.adapt(legacy)
        assert isinstance(result, ToolExecutionError)
        assert result.message == "test error"
        assert result.context.get("tool_name") == "test_tool"
        assert result.cause is legacy

    def test_tool_validation_error_maps_to_validation_error(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from applications.fitness.mcp_tools.exceptions import ToolValidationError
            legacy = ToolValidationError("invalid param", tool_name="selector")

        result = LegacyExceptionAdapter.adapt(legacy)
        assert isinstance(result, ValidationError)

    def test_tool_timeout_error_maps_to_timeout_error(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from applications.fitness.mcp_tools.exceptions import ToolTimeoutError
            legacy = ToolTimeoutError("timed out", tool_name="calc", timeout_ms=5000)

        result = LegacyExceptionAdapter.adapt(legacy)
        assert isinstance(result, TimeoutError)

    def test_tool_connection_error_maps_to_connection_error(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from applications.fitness.mcp_tools.exceptions import ToolConnectionError
            legacy = ToolConnectionError("neo4j down", tool_name="search", service="neo4j")

        result = LegacyExceptionAdapter.adapt(legacy)
        assert isinstance(result, ConnectionError)

    def test_is_legacy_detects_old_exceptions(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from applications.fitness.mcp_tools.exceptions import ToolError
            legacy = ToolError("test")

        assert LegacyExceptionAdapter.is_legacy(legacy) is True

    def test_is_legacy_rejects_new_exceptions(self):
        new_err = DAMLRAGError("test")
        assert LegacyExceptionAdapter.is_legacy(new_err) is False

    def test_unknown_exception_maps_to_base(self):
        err = RuntimeError("unknown")
        result = LegacyExceptionAdapter.adapt(err)
        assert isinstance(result, DAMLRAGError)

    def test_context_preserved(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from applications.fitness.mcp_tools.exceptions import ToolError
            legacy = ToolError("err", tool_name="t", context={"key": "val"})

        result = LegacyExceptionAdapter.adapt(legacy)
        assert result.context.get("key") == "val"
        assert result.context.get("tool_name") == "t"


class TestDeprecationWarnings:
    """验证旧异常触发 DeprecationWarning"""

    def test_tool_error_warns(self):
        from applications.fitness.mcp_tools.exceptions import ToolError
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ToolError("test")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "v10.0" in str(w[0].message)

    def test_mcp_tool_error_warns(self):
        from framework.mcp.error_handler import MCPToolError, MCPErrorCode
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            MCPToolError("tool", MCPErrorCode.INTERNAL_ERROR, "test")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
