# -*- coding: utf-8 -*-
"""
API Response - 统一API响应格式

符合三端统一标准（前端v2、前端v1、PHP后端）

版本：v2.0.0
更新日期：2025-11-17
重构说明：从备份恢复，适配新的三层检索架构
"""

from typing import Any, Optional, Generic, TypeVar, List, Dict
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """
    统一API响应格式

    符合三端统一标准：
    - code: 状态码（200成功，4xx客户端错误，5xx服务器错误）
    - msg: 消息文本
    - data: 响应数据（泛型）

    Example:
        >>> response = ApiResponse(
        ...     code=200,
        ...     msg="成功",
        ...     data={"result": "训练计划已生成"}
        ... )
    """
    code: int = Field(
        ...,
        description="状态码：200=成功，400=参数错误，401=未授权，500=服务器错误"
    )
    msg: str = Field(
        ...,
        description="消息文本"
    )
    data: Optional[T] = Field(
        None,
        description="响应数据"
    )
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="响应时间戳"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "msg": "成功",
                "data": {
                    "response": "推荐以下训练计划...",
                    "interaction_id": "uuid-xxx"
                },
                "timestamp": "2025-11-17T10:30:00"
            }
        }

    @classmethod
    def success(cls, data: Any = None, msg: str = "成功") -> "ApiResponse":
        """
        成功响应快捷方法

        Args:
            data: 响应数据
            msg: 成功消息（默认"成功"）

        Returns:
            ApiResponse: 成功响应

        Example:
            >>> return ApiResponse.success({"user_id": "123"})
        """
        return cls(code=200, msg=msg, data=data)

    @classmethod
    def error(
        cls,
        code: int = 500,
        msg: str = "服务器错误",
        data: Any = None
    ) -> "ApiResponse":
        """
        错误响应快捷方法

        Args:
            code: 错误码（默认500）
            msg: 错误消息
            data: 错误详情（可选）

        Returns:
            ApiResponse: 错误响应

        Example:
            >>> return ApiResponse.error(400, "参数缺失")
        """
        return cls(code=code, msg=msg, data=data)


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应格式

    用于分页数据的统一返回格式
    """
    items: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    per_page: int = Field(..., description="每页数量")
    pages: int = Field(..., description="总页数")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        per_page: int
    ) -> "PaginatedResponse":
        """创建分页响应"""
        pages = (total + per_page - 1) // per_page
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )


class ApiError(Exception):
    """
    API错误异常

    用于在业务逻辑中抛出错误，会被全局异常处理器捕获

    Attributes:
        code: 错误码
        msg: 错误消息
        data: 错误详情

    Example:
        >>> if not user_id:
        ...     raise ApiError(400, "用户ID不能为空")
    """

    def __init__(
        self,
        code: int = 500,
        msg: str = "服务器错误",
        data: Any = None
    ):
        self.code = code
        self.msg = msg
        self.data = data
        super().__init__(msg)


# 三层检索相关的数据模型
class ThreeLayerRetrievalRequest(BaseModel):
    """三层检索请求"""
    query: str = Field(..., description="查询文本")
    domain: str = Field(default="fitness", description="领域：fitness, nutrition, general")
    user_id: int = Field(..., description="用户ID")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="用户上下文")
    retrieval_mode: str = Field(default="full_three_layer", description="检索模式")
    top_k: int = Field(default=10, description="返回结果数量")
    enable_anti_hallucination: bool = Field(default=True, description="启用反幻觉验证")
    enable_field_standardization: bool = Field(default=True, description="启用字段标准化")

    @field_validator("user_id", mode="before")
    @classmethod
    def coerce_user_id(cls, v):
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return int(v)


class ThreeLayerRetrievalResponse(BaseModel):
    """三层检索响应"""
    query: str = Field(..., description="查询文本")
    answer: str = Field(..., description="生成的答案")
    sources: List[Dict[str, Any]] = Field(..., description="检索来源")
    confidence: float = Field(..., description="置信度")
    metadata: Dict[str, Any] = Field(..., description="元数据")

    # 三层检索特有字段
    retrieval_summary: Optional[Dict[str, Any]] = Field(default=None, description="三层检索摘要")
    anti_hallucination_result: Optional[Dict[str, Any]] = Field(default=None, description="反幻觉验证结果")
    standardization_result: Optional[Dict[str, Any]] = Field(default=None, description="字段标准化结果")


class ChatRequest(BaseModel):
    """聊天请求"""
    user_id: int = Field(..., description="用户ID")
    query: str = Field(..., max_length=2000, description="用户查询")
    domain: str = Field(default="fitness", description="领域")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文信息")
    stream: bool = Field(default=False, description="是否流式返回")
    retrieval_mode: Optional[str] = Field(default="full_three_layer", description="检索模式")
    mode: Optional[str] = Field(default="auto", description="执行模式: auto/dag/agent")
    topic_id: Optional[str] = Field(default=None, description="对话话题ID（用于上下文连续性）")

    @field_validator("user_id", mode="before")
    @classmethod
    def coerce_user_id(cls, v):
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return int(v)


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str = Field(..., description="AI回答")
    interaction_id: str = Field(..., description="交互ID")
    model_used: str = Field(..., description="使用的模型")
    tools_used: List[str] = Field(..., description="使用的工具列表")
    execution_time: float = Field(..., description="执行时间（秒）")
    personalization_score: float = Field(..., description="个性化得分")
    few_shot_examples_count: int = Field(..., description="Few-Shot示例数量")
    cache_hit: bool = Field(..., description="是否命中缓存")

    # 三层检索相关字段
    three_layer_result: Optional[ThreeLayerRetrievalResponse] = Field(
        default=None, description="三层检索结果"
    )


class FeedbackRequest(BaseModel):
    """用户反馈请求"""
    user_id: int = Field(..., description="用户ID")
    interaction_id: str = Field(..., description="交互ID")
    rating: int = Field(..., ge=1, le=5, description="评分（1-5）")
    feedback_type: str = Field(..., description="反馈类型：accuracy, helpfulness, safety")
    comment: Optional[str] = Field(default=None, description="评论")
    issue_category: Optional[str] = Field(default=None, description="问题分类")

    @field_validator("user_id", mode="before")
    @classmethod
    def coerce_user_id(cls, v):
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return int(v)


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态：healthy, unhealthy")
    version: str = Field(..., description="版本号")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    components: Dict[str, Any] = Field(..., description="各组件状态")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="性能指标")
    auth_enabled: bool = Field(default=False, description="认证是否启用（安全加固）")


# 导出所有模型
__all__ = [
    'ApiResponse',
    'PaginatedResponse',
    'ApiError',
    'ThreeLayerRetrievalRequest',
    'ThreeLayerRetrievalResponse',
    'ChatRequest',
    'ChatResponse',
    'FeedbackRequest',
    'HealthResponse'
]