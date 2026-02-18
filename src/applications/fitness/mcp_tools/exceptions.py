"""
MCP工具异常类型

⚠️ DEPRECATED - 将在v10.0删除
请使用 framework.exceptions 中的 DAMLRAGError 子类替代：
  ToolError → ToolExecutionError
  ToolValidationError → ValidationError
  ToolTimeoutError → TimeoutError
  ToolConnectionError → ConnectionError
  ToolExecutionError → ToolExecutionError

定义统一的异常类型，用于错误处理和日志记录
"""

import warnings


class ToolError(Exception):
    """
    工具基础异常

    ⚠️ DEPRECATED - 将在v10.0删除，使用 framework.exceptions.ToolExecutionError
    """
    def __init__(self, message: str, tool_name: str = None, context: dict = None):
        warnings.warn(
            "ToolError已废弃，将在v10.0删除。请使用 framework.exceptions.ToolExecutionError",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.context = context or {}

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "tool_name": self.tool_name,
            "context": self.context
        }


class ToolValidationError(ToolError):
    """
    输入验证错误

    ⚠️ DEPRECATED - 将在v10.0删除，使用 framework.exceptions.ValidationError
    """
    pass


class ToolTimeoutError(ToolError):
    """
    执行超时错误

    ⚠️ DEPRECATED - 将在v10.0删除，使用 framework.exceptions.TimeoutError
    """
    def __init__(self, message: str, tool_name: str = None, timeout_ms: float = None, context: dict = None):
        super().__init__(message, tool_name, context)
        self.timeout_ms = timeout_ms

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["timeout_ms"] = self.timeout_ms
        return result


class ToolConnectionError(ToolError):
    """
    数据库连接错误

    ⚠️ DEPRECATED - 将在v10.0删除，使用 framework.exceptions.ConnectionError
    """
    def __init__(self, message: str, tool_name: str = None, service: str = None, context: dict = None):
        super().__init__(message, tool_name, context)
        self.service = service

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["service"] = self.service
        return result


class ToolExecutionError(ToolError):
    """
    执行错误

    ⚠️ DEPRECATED - 将在v10.0删除，使用 framework.exceptions.ToolExecutionError
    """
    def __init__(self, message: str, tool_name: str = None, stage: str = None, context: dict = None):
        super().__init__(message, tool_name, context)
        self.stage = stage

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["stage"] = self.stage
        return result
