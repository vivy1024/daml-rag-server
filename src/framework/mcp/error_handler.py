"""
MCP工具统一错误处理器

提供标准化的错误处理机制，包括：
1. 统一的MCPToolError异常类
2. 标准错误码定义
3. MCPErrorHandler统一处理器
4. 错误日志和上下文管理

Requirements: 6.1, 6.2, 6.3, 6.4
Version: 1.0.0
"""

from typing import Dict, Any, Optional
from enum import Enum
import logging
import traceback
from datetime import datetime


class MCPErrorCode(str, Enum):
    """
    MCP工具标准错误码
    
    定义所有MCP工具可能遇到的错误类型
    """
    INVALID_INPUT = "INVALID_INPUT"           # 输入参数无效
    DATA_NOT_FOUND = "DATA_NOT_FOUND"         # 数据未找到
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"     # 依赖服务错误
    TIMEOUT = "TIMEOUT"                       # 执行超时
    INTERNAL_ERROR = "INTERNAL_ERROR"         # 内部错误


class MCPToolError(Exception):
    """
    MCP工具统一错误类
    
    所有MCP工具错误都应该使用此类或其子类
    
    Attributes:
        tool_name: 工具名称
        error_code: 标准错误码
        message: 错误消息
        context: 错误上下文信息
        cause: 原始异常（如果有）
    
    Example:
        raise MCPToolError(
            tool_name="intelligent_exercise_selector",
            error_code=MCPErrorCode.INVALID_INPUT,
            message="缺少必需参数: user_id",
            context={"params": input_data}
        )
    """
    
    def __init__(
        self,
        tool_name: str,
        error_code: MCPErrorCode,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化MCP工具错误
        
        Args:
            tool_name: 工具名称
            error_code: 标准错误码
            message: 错误消息
            context: 错误上下文信息
            cause: 原始异常
        """
        super().__init__(message)
        self.tool_name = tool_name
        self.error_code = error_code
        self.message = message
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.now().isoformat()
        
        # 保留原始异常的堆栈跟踪
        if cause is not None:
            self.__cause__ = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于日志和API响应）
        
        Returns:
            包含所有错误信息的字典
        """
        result = {
            "error_type": "MCPToolError",
            "tool_name": self.tool_name,
            "error_code": self.error_code.value,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp
        }
        
        if self.cause:
            result["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause)
            }
        
        return result
    
    def __str__(self) -> str:
        """返回格式化的错误字符串"""
        parts = [
            f"[{self.error_code.value}]",
            f"Tool: {self.tool_name}",
            f"Message: {self.message}"
        ]
        
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        
        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {self.cause}")
        
        return " | ".join(parts)
    
    def __repr__(self) -> str:
        """返回详细的错误表示（用于调试）"""
        return (
            f"MCPToolError("
            f"tool_name={self.tool_name!r}, "
            f"error_code={self.error_code!r}, "
            f"message={self.message!r}, "
            f"context={self.context!r}, "
            f"cause={self.cause!r})"
        )


class MCPErrorHandler:
    """
    MCP错误处理器
    
    提供统一的错误处理逻辑，包括：
    1. 异常类型识别和转换
    2. 错误日志记录
    3. 错误上下文管理
    4. 错误恢复建议
    
    Usage:
        handler = MCPErrorHandler(logger)
        try:
            result = await tool.execute(params)
        except Exception as e:
            error = handler.handle_error(e, "tool_name", context)
            raise error
    """
    
    # 错误处理策略配置
    ERROR_STRATEGIES = {
        MCPErrorCode.INVALID_INPUT: {
            "action": "return_error",
            "log_level": "WARNING",
            "retry": False,
            "suggestion": "请检查输入参数是否符合要求"
        },
        MCPErrorCode.DATA_NOT_FOUND: {
            "action": "return_empty",
            "log_level": "INFO",
            "retry": False,
            "suggestion": "未找到匹配的数据，请尝试调整查询条件"
        },
        MCPErrorCode.DEPENDENCY_ERROR: {
            "action": "use_fallback",
            "log_level": "ERROR",
            "retry": True,
            "max_retries": 2,
            "suggestion": "依赖服务暂时不可用，请稍后重试"
        },
        MCPErrorCode.TIMEOUT: {
            "action": "retry_with_backoff",
            "log_level": "WARNING",
            "retry": True,
            "max_retries": 2,
            "suggestion": "操作超时，系统将自动重试"
        },
        MCPErrorCode.INTERNAL_ERROR: {
            "action": "return_error",
            "log_level": "ERROR",
            "retry": False,
            "suggestion": "系统内部错误，请联系技术支持"
        }
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化错误处理器
        
        Args:
            logger: 日志记录器（可选）
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def handle_error(
        self,
        error: Exception,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolError:
        """
        统一错误处理
        
        将各种异常转换为MCPToolError，并记录日志
        
        Args:
            error: 原始异常
            tool_name: 工具名称
            context: 错误上下文
        
        Returns:
            MCPToolError实例
        """
        # 如果已经是MCPToolError，直接返回
        if isinstance(error, MCPToolError):
            self._log_error(error)
            return error
        
        # 识别错误类型并转换
        error_code = self._identify_error_code(error)
        message = self._format_error_message(error)
        
        # 创建MCPToolError
        mcp_error = MCPToolError(
            tool_name=tool_name,
            error_code=error_code,
            message=message,
            context=context,
            cause=error
        )
        
        # 记录日志
        self._log_error(mcp_error)
        
        return mcp_error
    
    def _identify_error_code(self, error: Exception) -> MCPErrorCode:
        """
        识别错误类型并返回对应的错误码
        
        Args:
            error: 原始异常
        
        Returns:
            MCPErrorCode
        """
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # 输入验证错误
        if "validation" in error_type.lower() or "invalid" in error_message:
            return MCPErrorCode.INVALID_INPUT
        
        # 数据未找到
        if "not found" in error_message or "empty" in error_message:
            return MCPErrorCode.DATA_NOT_FOUND
        
        # 超时错误
        if "timeout" in error_type.lower() or "timeout" in error_message:
            return MCPErrorCode.TIMEOUT
        
        # 连接错误（依赖服务）
        if "connection" in error_type.lower() or "connection" in error_message:
            return MCPErrorCode.DEPENDENCY_ERROR
        
        # 默认为内部错误
        return MCPErrorCode.INTERNAL_ERROR
    
    def _format_error_message(self, error: Exception) -> str:
        """
        格式化错误消息
        
        Args:
            error: 原始异常
        
        Returns:
            格式化后的错误消息
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # 如果错误消息为空，使用错误类型
        if not error_message:
            return f"{error_type} occurred"
        
        return f"{error_type}: {error_message}"
    
    def _log_error(self, error: MCPToolError) -> None:
        """
        记录错误日志
        
        根据错误码选择合适的日志级别
        
        Args:
            error: MCPToolError实例
        """
        strategy = self.ERROR_STRATEGIES.get(error.error_code, {})
        log_level = strategy.get("log_level", "ERROR")
        
        # 构建日志消息
        log_message = (
            f"❌ MCP工具错误 | "
            f"工具: {error.tool_name} | "
            f"错误码: {error.error_code.value} | "
            f"消息: {error.message}"
        )
        
        if error.context:
            log_message += f" | 上下文: {error.context}"
        
        # 记录日志
        if log_level == "ERROR":
            self.logger.error(log_message, exc_info=error.cause)
        elif log_level == "WARNING":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def get_error_strategy(self, error_code: MCPErrorCode) -> Dict[str, Any]:
        """
        获取错误处理策略
        
        Args:
            error_code: 错误码
        
        Returns:
            错误处理策略配置
        """
        return self.ERROR_STRATEGIES.get(error_code, {})
    
    def should_retry(self, error_code: MCPErrorCode) -> bool:
        """
        判断是否应该重试
        
        Args:
            error_code: 错误码
        
        Returns:
            是否应该重试
        """
        strategy = self.get_error_strategy(error_code)
        return strategy.get("retry", False)
    
    def get_max_retries(self, error_code: MCPErrorCode) -> int:
        """
        获取最大重试次数
        
        Args:
            error_code: 错误码
        
        Returns:
            最大重试次数
        """
        strategy = self.get_error_strategy(error_code)
        return strategy.get("max_retries", 0)
    
    def get_suggestion(self, error_code: MCPErrorCode) -> str:
        """
        获取错误恢复建议
        
        Args:
            error_code: 错误码
        
        Returns:
            恢复建议
        """
        strategy = self.get_error_strategy(error_code)
        return strategy.get("suggestion", "请联系技术支持")


# 便捷函数

def create_mcp_error(
    tool_name: str,
    error_code: MCPErrorCode,
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> MCPToolError:
    """
    创建MCPToolError的便捷函数
    
    Args:
        tool_name: 工具名称
        error_code: 错误码
        message: 错误消息
        context: 错误上下文
    
    Returns:
        MCPToolError实例
    """
    return MCPToolError(
        tool_name=tool_name,
        error_code=error_code,
        message=message,
        context=context
    )


def wrap_mcp_error(
    error: Exception,
    tool_name: str,
    context: Optional[Dict[str, Any]] = None
) -> MCPToolError:
    """
    包装异常为MCPToolError的便捷函数
    
    Args:
        error: 原始异常
        tool_name: 工具名称
        context: 错误上下文
    
    Returns:
        MCPToolError实例
    """
    handler = MCPErrorHandler()
    return handler.handle_error(error, tool_name, context)
