# -*- coding: utf-8 -*-
"""
Distributed Tracing Middleware - 分布式追踪中间件

功能:
- 每个请求生成唯一 trace_id（UUID4）
- 通过 contextvars 在整个请求生命周期内传播
- 所有日志自动携带 trace_id
- 响应头添加 X-Trace-ID
- 支持客户端传入 X-Request-ID 作为 trace_id

版本: v1.0.0
日期: 2026-02-19
作者: 薛小川
"""

import uuid
import time
import logging
import contextvars
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# 协程安全的 trace_id 上下文变量
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default="-"
)


def get_trace_id() -> str:
    """获取当前请求的 trace_id（供业务代码使用）"""
    return trace_id_var.get("-")


class TraceIdFilter(logging.Filter):
    """
    日志过滤器：自动注入 trace_id 到日志记录

    使用方式:
        在日志格式中添加 %(trace_id)s
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get("-")
        return True


class TracingMiddleware(BaseHTTPMiddleware):
    """
    分布式追踪中间件

    请求进入 → 生成/提取 trace_id → 存入 contextvar → 处理请求 → 响应头添加 X-Trace-ID
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 优先使用客户端传入的 X-Request-ID
        trace_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 存入 contextvar（后续所有日志自动携带）
        token = trace_id_var.set(trace_id)

        start_time = time.time()
        try:
            response = await call_next(request)
            # 响应头添加 trace_id
            response.headers["X-Trace-ID"] = trace_id
            return response
        except Exception as e:
            logger.error(
                f"[trace={trace_id}] Request failed: {e}",
                exc_info=True,
            )
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"[trace={trace_id}] {request.method} {request.url.path} "
                    f"completed in {duration_ms:.1f}ms"
                )
            # 重置 contextvar
            trace_id_var.reset(token)
