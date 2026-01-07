# -*- coding: utf-8 -*-
"""
结构化日志系统 - Structured Logging System

提供JSON格式的结构化日志，支持：
1. trace_id追踪
2. 统一日志格式
3. 日志级别管理
4. 上下文信息记录
5. 性能指标记录

版本: v1.0.0
日期: 2025-12-16
作者: 薛小川
"""

import logging
import json
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar
from functools import wraps

# 上下文变量：存储trace_id
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        初始化结构化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 如果没有处理器，添加默认处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
    
    def _build_log_entry(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        构建日志条目
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外信息
            
        Returns:
            Dict[str, Any]: 日志条目
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "trace_id": trace_id_var.get(),
            "logger_name": self.logger.name
        }
        
        if extra:
            entry.update(extra)
        
        return entry
    
    def debug(self, message: str, **kwargs):
        """记录DEBUG级别日志"""
        entry = self._build_log_entry("DEBUG", message, kwargs)
        self.logger.debug(json.dumps(entry, ensure_ascii=False))
    
    def info(self, message: str, **kwargs):
        """记录INFO级别日志"""
        entry = self._build_log_entry("INFO", message, kwargs)
        self.logger.info(json.dumps(entry, ensure_ascii=False))
    
    def warning(self, message: str, **kwargs):
        """记录WARNING级别日志"""
        entry = self._build_log_entry("WARNING", message, kwargs)
        self.logger.warning(json.dumps(entry, ensure_ascii=False))
    
    def error(self, message: str, **kwargs):
        """记录ERROR级别日志"""
        entry = self._build_log_entry("ERROR", message, kwargs)
        self.logger.error(json.dumps(entry, ensure_ascii=False))
    
    def critical(self, message: str, **kwargs):
        """记录CRITICAL级别日志"""
        entry = self._build_log_entry("CRITICAL", message, kwargs)
        self.logger.critical(json.dumps(entry, ensure_ascii=False))


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的日志
        """
        # 如果消息已经是JSON格式，直接返回
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            pass
        
        # 否则构建JSON格式
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "trace_id": trace_id_var.get(),
            "logger_name": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """
    设置trace_id
    
    Args:
        trace_id: trace_id，如果为None则自动生成
        
    Returns:
        str: 设置的trace_id
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    
    trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> Optional[str]:
    """
    获取当前trace_id
    
    Returns:
        Optional[str]: 当前trace_id
    """
    return trace_id_var.get()


def clear_trace_id():
    """清除trace_id"""
    trace_id_var.set(None)


def with_trace_id(func):
    """
    装饰器：为函数调用自动生成trace_id
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        trace_id = set_trace_id()
        try:
            return await func(*args, **kwargs)
        finally:
            clear_trace_id()
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        trace_id = set_trace_id()
        try:
            return func(*args, **kwargs)
        finally:
            clear_trace_id()
    
    # 判断是否为异步函数
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def log_performance(logger: StructuredLogger, operation: str):
    """
    装饰器：记录函数执行性能
    
    Args:
        logger: 结构化日志记录器
        operation: 操作名称
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"{operation} completed",
                    operation=operation,
                    duration_seconds=duration,
                    success=True
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{operation} failed",
                    operation=operation,
                    duration_seconds=duration,
                    success=False,
                    error=str(e)
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"{operation} completed",
                    operation=operation,
                    duration_seconds=duration,
                    success=True
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{operation} failed",
                    operation=operation,
                    duration_seconds=duration,
                    success=False,
                    error=str(e)
                )
                raise
        
        # 判断是否为异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 全局日志记录器实例
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
    """
    获取结构化日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        
    Returns:
        StructuredLogger: 结构化日志记录器
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, level)
    return _loggers[name]


# 导出
__all__ = [
    "StructuredLogger",
    "StructuredFormatter",
    "set_trace_id",
    "get_trace_id",
    "clear_trace_id",
    "with_trace_id",
    "log_performance",
    "get_logger"
]
