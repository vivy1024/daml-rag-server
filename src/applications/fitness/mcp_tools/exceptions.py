"""
MCP工具异常类型

定义统一的异常类型，用于错误处理和日志记录
"""


class ToolError(Exception):
    """
    工具基础异常
    
    所有MCP工具异常的基类
    """
    def __init__(self, message: str, tool_name: str = None, context: dict = None):
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
    
    当工具输入参数无效时抛出
    
    示例：
        - 缺少必需参数
        - 参数类型错误
        - 参数值超出范围
    """
    pass


class ToolTimeoutError(ToolError):
    """
    执行超时错误
    
    当工具执行时间超过预期时抛出
    
    示例：
        - 数据库查询超时
        - 三层检索超时
        - 外部API调用超时
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
    
    当无法连接到数据库或外部服务时抛出
    
    示例：
        - Neo4j连接失败
        - Qdrant连接失败
        - Redis连接失败
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
    
    当工具内部逻辑执行失败时抛出
    
    示例：
        - 三层检索返回空结果
        - 计算逻辑错误
        - 数据格式错误
    """
    def __init__(self, message: str, tool_name: str = None, stage: str = None, context: dict = None):
        super().__init__(message, tool_name, context)
        self.stage = stage  # 执行阶段（如：layer1, layer2, layer3, calculation）
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        result["stage"] = self.stage
        return result
