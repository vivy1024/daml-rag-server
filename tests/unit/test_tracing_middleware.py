# -*- coding: utf-8 -*-
"""
分布式追踪中间件 - 单元测试

覆盖场景:
- trace_id自动生成
- 客户端传入X-Request-ID
- 响应头包含X-Trace-ID
- TraceIdFilter注入日志
- contextvars隔离性

Task 42 - Phase 7 Batch 3 性能与可观测性
"""

import pytest
import logging
import sys
import os
import uuid
import importlib.util

# 直接加载tracing模块文件，避免触发api/__init__.py的链式导入
_tracing_path = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'api', 'middleware', 'tracing.py'
)
_spec = importlib.util.spec_from_file_location("tracing", _tracing_path)
_tracing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tracing)

TracingMiddleware = _tracing.TracingMiddleware
TraceIdFilter = _tracing.TraceIdFilter
trace_id_var = _tracing.trace_id_var
get_trace_id = _tracing.get_trace_id


class TestTraceIdFilter:
    """TraceIdFilter 日志注入测试"""

    def test_filter_injects_trace_id(self):
        """filter应将trace_id注入到LogRecord"""
        f = TraceIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        token = trace_id_var.set("abc-123")
        try:
            result = f.filter(record)
            assert result is True
            assert record.trace_id == "abc-123"
        finally:
            trace_id_var.reset(token)

    def test_filter_default_when_no_context(self):
        """无上下文时trace_id为默认值'-'"""
        f = TraceIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        result = f.filter(record)
        assert result is True
        assert record.trace_id == "-"


class TestGetTraceId:
    """get_trace_id辅助函数测试"""

    def test_returns_current_trace_id(self):
        token = trace_id_var.set("test-trace-id")
        try:
            assert get_trace_id() == "test-trace-id"
        finally:
            trace_id_var.reset(token)

    def test_returns_default_when_unset(self):
        assert get_trace_id() == "-"


class TestTracingMiddleware:
    """TracingMiddleware集成测试（使用Starlette TestClient）"""

    @pytest.fixture
    def app(self):
        """创建测试用Starlette应用"""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        async def homepage(request):
            return JSONResponse({
                "trace_id": get_trace_id(),
            })

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(TracingMiddleware)
        return app

    @pytest.fixture
    def client(self, app):
        from starlette.testclient import TestClient
        return TestClient(app)

    def test_auto_generates_trace_id(self, client):
        """自动生成trace_id并添加到响应头"""
        response = client.get("/")
        assert response.status_code == 200
        trace_id = response.headers.get("X-Trace-ID")
        assert trace_id is not None
        # 验证是有效的UUID4格式
        uuid.UUID(trace_id, version=4)

    def test_uses_client_request_id(self, client):
        """使用客户端传入的X-Request-ID"""
        custom_id = "my-custom-trace-123"
        response = client.get("/", headers={"X-Request-ID": custom_id})
        assert response.headers.get("X-Trace-ID") == custom_id

    def test_trace_id_available_in_handler(self, client):
        """handler内可通过get_trace_id()获取trace_id"""
        response = client.get("/")
        body = response.json()
        trace_id_in_header = response.headers.get("X-Trace-ID")
        assert body["trace_id"] == trace_id_in_header

    def test_different_requests_get_different_ids(self, client):
        """不同请求获得不同的trace_id"""
        r1 = client.get("/")
        r2 = client.get("/")
        assert r1.headers["X-Trace-ID"] != r2.headers["X-Trace-ID"]
