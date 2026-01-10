# -*- coding: utf-8 -*-
"""
Agent执行器 - 双策略架构核心组件

实现LLM自主决策的Agent模式执行器，与DAG模式形成双策略架构。

核心功能：
1. LLM自主决策工具调用
2. 最大迭代次数限制（防止无限循环）
3. 工具调用白名单
4. Layer3安全规则强制执行
5. 敏感操作日志记录
6. 可配置人工确认机制

Requirements: 8.1-8.4, 8.7

版本: v1.1.0
日期: 2026-01-11
作者: 薛小川
"""

import asyncio
import logging
import time
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union, TYPE_CHECKING
from enum import Enum
from datetime import datetime
from pathlib import Path

if TYPE_CHECKING:
    from src.framework.adapters.domain_adapter import Layer3Rule

logger = logging.getLogger(__name__)

# 安全审计日志记录器（独立于普通日志）
security_logger = logging.getLogger("agent_security_audit")


# =============================================================================
# 枚举定义
# =============================================================================

class ExecutionStrategy(Enum):
    """执行策略枚举"""
    DAG = "dag"      # DAG模式：预定义模板，程序控制
    AGENT = "agent"  # Agent模式：LLM自主决策


class AgentAction(Enum):
    """Agent动作类型"""
    CALL_TOOL = "call_tool"    # 调用工具
    FINISH = "finish"          # 完成任务
    THINK = "think"            # 继续思考（不调用工具）


class SensitiveOperationType(Enum):
    """敏感操作类型"""
    DATA_MODIFICATION = "data_modification"      # 数据修改
    USER_PROFILE_UPDATE = "user_profile_update"  # 用户档案更新
    TRAINING_PLAN_CREATE = "training_plan_create"  # 训练计划创建
    NUTRITION_PLAN_CREATE = "nutrition_plan_create"  # 营养计划创建
    SAFETY_OVERRIDE = "safety_override"          # 安全规则覆盖
    HIGH_RISK_EXERCISE = "high_risk_exercise"    # 高风险动作推荐


# 敏感工具映射表
SENSITIVE_TOOLS: Dict[str, SensitiveOperationType] = {
    "update_user_profile": SensitiveOperationType.USER_PROFILE_UPDATE,
    "professional_program_designer": SensitiveOperationType.TRAINING_PLAN_CREATE,
    "periodized_program_designer": SensitiveOperationType.TRAINING_PLAN_CREATE,
    "training_split_designer": SensitiveOperationType.TRAINING_PLAN_CREATE,
    "meal_plan_designer": SensitiveOperationType.NUTRITION_PLAN_CREATE,
    "record_training_feedback": SensitiveOperationType.DATA_MODIFICATION,
}


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class AgentDecision:
    """
    Agent决策结果
    
    表示LLM在每次迭代中做出的决策
    
    Attributes:
        action: 动作类型（调用工具/完成/思考）
        tool_name: 要调用的工具名称（仅CALL_TOOL时有效）
        tool_params: 工具参数（仅CALL_TOOL时有效）
        response: 最终响应（仅FINISH时有效）
        reasoning: 决策推理过程
    """
    action: AgentAction
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    response: Optional[str] = None
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "action": self.action.value,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "response": self.response,
            "reasoning": self.reasoning
        }


@dataclass
class ToolCallRecord:
    """
    工具调用记录
    
    记录单次工具调用的详细信息
    """
    tool_name: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    iteration: int = 0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "params": self.params,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "iteration": self.iteration,
            "timestamp": self.timestamp
        }


@dataclass
class SafetyCheckResult:
    """
    安全检查结果
    
    Layer3规则检查的结果
    """
    passed: bool
    reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    blocked_by_rule: Optional[str] = None
    requires_confirmation: bool = False  # 是否需要人工确认
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "passed": self.passed,
            "reason": self.reason,
            "warnings": self.warnings,
            "blocked_by_rule": self.blocked_by_rule,
            "requires_confirmation": self.requires_confirmation
        }


@dataclass
class HumanConfirmationRequest:
    """
    人工确认请求
    
    当敏感操作需要人工确认时生成此请求
    
    Requirements: 8.7
    """
    request_id: str
    tool_name: str
    tool_params: Dict[str, Any]
    operation_type: SensitiveOperationType
    reason: str
    user_id: str
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"  # pending | approved | rejected | timeout
    response_timestamp: Optional[float] = None
    responder: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "operation_type": self.operation_type.value,
            "reason": self.reason,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "response_timestamp": self.response_timestamp,
            "responder": self.responder
        }


@dataclass
class SecurityAuditLog:
    """
    安全审计日志
    
    记录所有敏感操作的审计日志
    
    Requirements: 8.7
    """
    log_id: str
    timestamp: float
    event_type: str  # tool_call | safety_block | human_confirm | rule_trigger
    user_id: str
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    safety_result: Optional[Dict[str, Any]] = None
    rule_triggered: Optional[str] = None
    action_taken: str = ""  # executed | blocked | pending_confirmation
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "safety_result": self.safety_result,
            "rule_triggered": self.rule_triggered,
            "action_taken": self.action_taken,
            "details": self.details
        }
    
    def to_log_string(self) -> str:
        """转换为日志字符串"""
        return (
            f"[{datetime.fromtimestamp(self.timestamp).isoformat()}] "
            f"[{self.event_type}] "
            f"user={self.user_id} "
            f"tool={self.tool_name or 'N/A'} "
            f"action={self.action_taken} "
            f"rule={self.rule_triggered or 'N/A'}"
        )


@dataclass
class AgentExecutionResult:
    """
    Agent执行结果
    
    Agent模式执行的最终结果
    
    Attributes:
        success: 是否成功完成
        response: 最终响应文本
        iterations: 执行的迭代次数
        tool_calls: 工具调用记录列表
        total_time_ms: 总执行时间（毫秒）
        safety_warnings: 安全警告列表
        metadata: 额外元数据
        audit_logs: 安全审计日志列表
        pending_confirmations: 待确认的人工确认请求
    """
    success: bool
    response: str
    iterations: int
    tool_calls: List[ToolCallRecord]
    total_time_ms: float
    safety_warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    audit_logs: List[SecurityAuditLog] = field(default_factory=list)
    pending_confirmations: List[HumanConfirmationRequest] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "response": self.response,
            "iterations": self.iterations,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "total_time_ms": self.total_time_ms,
            "safety_warnings": self.safety_warnings,
            "metadata": self.metadata,
            "audit_logs": [log.to_dict() for log in self.audit_logs],
            "pending_confirmations": [pc.to_dict() for pc in self.pending_confirmations]
        }


# =============================================================================
# LLM客户端抽象接口
# =============================================================================

class LLMClientInterface(ABC):
    """
    LLM客户端抽象接口
    
    定义Agent执行器所需的LLM客户端接口
    """
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            tools: 可用工具列表（OpenAI function calling格式）
            **kwargs: 其他参数
        
        Returns:
            LLM响应
        """
        pass
    
    @abstractmethod
    async def parse_tool_call(
        self,
        response: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        解析工具调用
        
        Args:
            response: LLM响应
        
        Returns:
            工具调用信息或None
        """
        pass


# =============================================================================
# 工具接口抽象
# =============================================================================

class ToolInterface(ABC):
    """
    工具抽象接口
    
    定义Agent执行器所需的工具接口
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """返回工具名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """返回工具描述"""
        pass
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        pass
    
    def get_openai_schema(self) -> Dict[str, Any]:
        """
        返回OpenAI function calling格式的Schema
        
        子类可覆盖此方法提供更详细的Schema
        """
        return {
            "type": "function",
            "function": {
                "name": self.get_name(),
                "description": self.get_description(),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }


# =============================================================================
# AgentExecutor 核心类
# =============================================================================

class AgentExecutor:
    """
    Agent模式执行器
    
    实现LLM自主决策的工具调用，与DAG模式形成双策略架构。
    
    核心特性：
    1. LLM自主决策工具调用 - Requirements 8.1
    2. 最大迭代次数限制（防止无限循环）- Requirements 8.2
    3. 工具调用白名单 - Requirements 8.3
    4. Layer3安全规则强制执行
    5. 敏感操作日志记录
    
    使用示例:
    ```python
    from src.framework.orchestration.agent_executor import AgentExecutor
    
    # 创建执行器
    executor = AgentExecutor(
        tools=my_tools,
        layer3_rules=my_rules,
        llm_client=my_llm_client,
        max_iterations=10,
        tool_whitelist=["tool1", "tool2"]
    )
    
    # 执行Agent模式
    result = await executor.execute(
        query="帮我制定一个训练计划",
        user_profile={"age": 25, "goal": "增肌"}
    )
    ```
    """
    
    DEFAULT_MAX_ITERATIONS = 10
    DEFAULT_TIMEOUT_SECONDS = 60.0
    DEFAULT_CONFIRMATION_TIMEOUT = 300.0  # 人工确认超时时间（秒）
    
    def __init__(
        self,
        tools: List[Union[ToolInterface, Any]],
        layer3_rules: List['Layer3Rule'],
        llm_client: LLMClientInterface,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        tool_whitelist: Optional[List[str]] = None,
        enable_human_confirmation: bool = False,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        enable_safety_check: bool = True,
        confirmation_callback: Optional[Callable] = None,
        confirmation_timeout: float = DEFAULT_CONFIRMATION_TIMEOUT,
        sensitive_tools: Optional[Dict[str, SensitiveOperationType]] = None,
        audit_log_path: Optional[str] = None
    ):
        """
        初始化Agent执行器
        
        Args:
            tools: 可用工具列表
            layer3_rules: Layer3安全规则列表
            llm_client: LLM客户端
            max_iterations: 最大迭代次数（默认10次）- Requirements 8.2
            tool_whitelist: 工具白名单（None表示允许所有工具）- Requirements 8.3
            enable_human_confirmation: 是否启用人工确认（敏感操作）- Requirements 8.7
            timeout_seconds: 执行超时时间（秒）
            enable_safety_check: 是否启用安全检查 - Requirements 8.4
            confirmation_callback: 人工确认回调函数
            confirmation_timeout: 人工确认超时时间（秒）
            sensitive_tools: 敏感工具映射表（覆盖默认）
            audit_log_path: 审计日志文件路径
        
        Requirements: 8.1-8.4, 8.7
        """
        # 构建工具字典
        self.tools: Dict[str, Union[ToolInterface, Any]] = {}
        for tool in tools:
            tool_name = tool.get_name() if hasattr(tool, 'get_name') else str(tool)
            self.tools[tool_name] = tool
        
        self.layer3_rules = layer3_rules
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.tool_whitelist = set(tool_whitelist) if tool_whitelist else None
        self.enable_human_confirmation = enable_human_confirmation
        self.timeout_seconds = timeout_seconds
        self.enable_safety_check = enable_safety_check
        self.confirmation_callback = confirmation_callback
        self.confirmation_timeout = confirmation_timeout
        self.sensitive_tools = sensitive_tools or SENSITIVE_TOOLS
        
        # 审计日志配置
        self.audit_log_path = audit_log_path
        self._setup_security_logger()
        
        # 待确认请求存储
        self._pending_confirmations: Dict[str, HumanConfirmationRequest] = {}
        
        # 统计信息
        self._execution_count = 0
        self._total_iterations = 0
        self._total_tool_calls = 0
        self._blocked_by_safety = 0
        self._human_confirmations_requested = 0
        self._human_confirmations_approved = 0
        self._human_confirmations_rejected = 0
        
        logger.info(
            f"✅ AgentExecutor初始化完成: "
            f"{len(self.tools)}个工具, "
            f"最大迭代{max_iterations}次, "
            f"白名单: {tool_whitelist or '全部'}, "
            f"人工确认: {'启用' if enable_human_confirmation else '禁用'}"
        )
    
    def _setup_security_logger(self) -> None:
        """
        设置安全审计日志记录器
        
        Requirements: 8.7
        """
        if self.audit_log_path:
            # 确保目录存在
            log_dir = Path(self.audit_log_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建文件处理器
            file_handler = logging.FileHandler(
                self.audit_log_path,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            
            # 添加到安全日志记录器
            security_logger.addHandler(file_handler)
            security_logger.setLevel(logging.INFO)
            
            logger.info(f"安全审计日志路径: {self.audit_log_path}")

    
    # =========================================================================
    # 核心执行方法
    # =========================================================================
    
    async def execute(
        self,
        query: str,
        user_profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        force_tools: Optional[List[str]] = None
    ) -> AgentExecutionResult:
        """
        执行Agent模式
        
        流程：
        1. LLM分析用户意图
        2. LLM选择工具
        3. 安全检查（Layer3规则）
        4. 敏感操作检查（人工确认）
        5. 执行工具
        6. LLM判断是否需要继续
        7. 重复2-6直到完成或达到最大迭代
        
        Args:
            query: 用户查询
            user_profile: 用户档案
            context: 额外上下文（可选）
            force_tools: 强制使用的工具列表（可选）
        
        Returns:
            AgentExecutionResult: 执行结果
        
        Requirements: 8.1-8.4, 8.7
        """
        self._execution_count += 1
        start_time = time.time()
        user_id = user_profile.get("user_id", "unknown")
        
        logger.info(f"🤖 开始Agent执行 #{self._execution_count}")
        logger.info(f"   查询: {query[:100]}...")
        
        # 记录执行开始的审计日志
        audit_logs: List[SecurityAuditLog] = []
        self._log_security_event(
            audit_logs=audit_logs,
            event_type="execution_start",
            user_id=user_id,
            details={"query": query[:200], "execution_id": self._execution_count}
        )
        
        # 初始化执行上下文
        execution_context = {
            "query": query,
            "user_profile": user_profile,
            "context": context or {},
            "tool_results": [],
            "iteration": 0,
            "messages": []
        }
        
        tool_calls: List[ToolCallRecord] = []
        safety_warnings: List[str] = []
        pending_confirmations: List[HumanConfirmationRequest] = []
        
        try:
            # 执行迭代循环
            for i in range(self.max_iterations):
                execution_context["iteration"] = i + 1
                self._total_iterations += 1
                
                logger.info(f"   📍 迭代 {i + 1}/{self.max_iterations}")
                
                # 检查超时
                elapsed = time.time() - start_time
                if elapsed > self.timeout_seconds:
                    logger.warning(f"   ⏰ 执行超时 ({elapsed:.1f}s > {self.timeout_seconds}s)")
                    self._log_security_event(
                        audit_logs=audit_logs,
                        event_type="execution_timeout",
                        user_id=user_id,
                        action_taken="timeout",
                        details={"elapsed_seconds": elapsed}
                    )
                    return AgentExecutionResult(
                        success=False,
                        response=f"执行超时，已完成{i}次迭代",
                        iterations=i,
                        tool_calls=tool_calls,
                        total_time_ms=(time.time() - start_time) * 1000,
                        safety_warnings=safety_warnings,
                        metadata={"timeout": True},
                        audit_logs=audit_logs,
                        pending_confirmations=pending_confirmations
                    )
                
                # LLM决策
                decision = await self._llm_decide(execution_context)
                logger.info(f"   🧠 LLM决策: {decision.action.value}")
                
                # 处理完成动作
                if decision.action == AgentAction.FINISH:
                    logger.info(f"   ✅ Agent完成，共{i + 1}次迭代")
                    self._log_security_event(
                        audit_logs=audit_logs,
                        event_type="execution_complete",
                        user_id=user_id,
                        action_taken="completed",
                        details={"iterations": i + 1, "tool_calls_count": len(tool_calls)}
                    )
                    return AgentExecutionResult(
                        success=True,
                        response=decision.response or "",
                        iterations=i + 1,
                        tool_calls=tool_calls,
                        total_time_ms=(time.time() - start_time) * 1000,
                        safety_warnings=safety_warnings,
                        metadata={"finish_reason": "completed"},
                        audit_logs=audit_logs,
                        pending_confirmations=pending_confirmations
                    )
                
                # 处理思考动作（不调用工具）
                if decision.action == AgentAction.THINK:
                    logger.info(f"   💭 Agent思考中: {decision.reasoning[:50]}...")
                    execution_context["messages"].append({
                        "role": "assistant",
                        "content": decision.reasoning
                    })
                    continue
                
                # 处理工具调用动作
                if decision.action == AgentAction.CALL_TOOL:
                    tool_result = await self._handle_tool_call(
                        decision=decision,
                        user_profile=user_profile,
                        execution_context=execution_context,
                        tool_calls=tool_calls,
                        safety_warnings=safety_warnings,
                        pending_confirmations=pending_confirmations,
                        audit_logs=audit_logs,
                        iteration=i + 1
                    )
                    
                    # 将工具结果添加到上下文
                    execution_context["tool_results"].append(tool_result)
            
            # 达到最大迭代次数
            logger.warning(f"   ⚠️ 达到最大迭代次数 ({self.max_iterations})")
            self._log_security_event(
                audit_logs=audit_logs,
                event_type="max_iterations_reached",
                user_id=user_id,
                action_taken="max_iterations",
                details={"max_iterations": self.max_iterations}
            )
            return AgentExecutionResult(
                success=False,
                response=f"达到最大迭代次数({self.max_iterations})，任务未完成",
                iterations=self.max_iterations,
                tool_calls=tool_calls,
                total_time_ms=(time.time() - start_time) * 1000,
                safety_warnings=safety_warnings,
                metadata={"finish_reason": "max_iterations"},
                audit_logs=audit_logs,
                pending_confirmations=pending_confirmations
            )
            
        except Exception as e:
            logger.error(f"   ❌ Agent执行异常: {e}", exc_info=True)
            self._log_security_event(
                audit_logs=audit_logs,
                event_type="execution_error",
                user_id=user_id,
                action_taken="error",
                details={"error": str(e)}
            )
            return AgentExecutionResult(
                success=False,
                response=f"执行异常: {str(e)}",
                iterations=execution_context.get("iteration", 0),
                tool_calls=tool_calls,
                total_time_ms=(time.time() - start_time) * 1000,
                safety_warnings=safety_warnings,
                metadata={"error": str(e)},
                audit_logs=audit_logs,
                pending_confirmations=pending_confirmations
            )

    
    async def _handle_tool_call(
        self,
        decision: AgentDecision,
        user_profile: Dict[str, Any],
        execution_context: Dict[str, Any],
        tool_calls: List[ToolCallRecord],
        safety_warnings: List[str],
        pending_confirmations: List[HumanConfirmationRequest],
        audit_logs: List[SecurityAuditLog],
        iteration: int
    ) -> Dict[str, Any]:
        """
        处理工具调用
        
        Args:
            decision: Agent决策
            user_profile: 用户档案
            execution_context: 执行上下文
            tool_calls: 工具调用记录列表（会被修改）
            safety_warnings: 安全警告列表（会被修改）
            pending_confirmations: 待确认请求列表（会被修改）
            audit_logs: 审计日志列表（会被修改）
            iteration: 当前迭代次数
        
        Returns:
            工具执行结果
        
        Requirements: 8.4, 8.7
        """
        tool_name = decision.tool_name
        tool_params = decision.tool_params or {}
        user_id = user_profile.get("user_id", "unknown")
        
        logger.info(f"   🔧 调用工具: {tool_name}")
        
        # 白名单检查 - Requirements 8.3
        if not self._check_whitelist(tool_name):
            logger.warning(f"   ⛔ 工具 {tool_name} 不在白名单中")
            self._log_security_event(
                audit_logs=audit_logs,
                event_type="whitelist_block",
                user_id=user_id,
                tool_name=tool_name,
                tool_params=tool_params,
                action_taken="blocked",
                details={"reason": "not_in_whitelist"}
            )
            error_result = {
                "tool": tool_name,
                "error": f"工具 {tool_name} 不在白名单中",
                "success": False
            }
            tool_calls.append(ToolCallRecord(
                tool_name=tool_name,
                params=tool_params,
                error=error_result["error"],
                iteration=iteration
            ))
            return error_result
        
        # 安全检查（Layer3规则）- Requirements 8.4
        if self.enable_safety_check:
            safety_result = self._safety_check(
                tool_name=tool_name,
                params=tool_params,
                user_profile=user_profile
            )
            
            if not safety_result.passed:
                logger.warning(f"   ⛔ 安全检查未通过: {safety_result.reason}")
                self._blocked_by_safety += 1
                self._log_security_event(
                    audit_logs=audit_logs,
                    event_type="safety_block",
                    user_id=user_id,
                    tool_name=tool_name,
                    tool_params=tool_params,
                    safety_result=safety_result.to_dict(),
                    rule_triggered=safety_result.blocked_by_rule,
                    action_taken="blocked",
                    details={"reason": safety_result.reason}
                )
                safety_warnings.extend(safety_result.warnings)
                error_result = {
                    "tool": tool_name,
                    "error": f"安全检查未通过: {safety_result.reason}",
                    "blocked_by_rule": safety_result.blocked_by_rule,
                    "success": False
                }
                tool_calls.append(ToolCallRecord(
                    tool_name=tool_name,
                    params=tool_params,
                    error=error_result["error"],
                    iteration=iteration
                ))
                return error_result
            
            # 添加警告（即使通过）
            if safety_result.warnings:
                safety_warnings.extend(safety_result.warnings)
        
        # 敏感操作检查和人工确认 - Requirements 8.7
        if self.enable_human_confirmation:
            confirmation_result = await self._check_sensitive_operation(
                tool_name=tool_name,
                params=tool_params,
                user_profile=user_profile,
                pending_confirmations=pending_confirmations,
                audit_logs=audit_logs
            )
            
            if not confirmation_result["approved"]:
                if confirmation_result["status"] == "pending":
                    # 需要人工确认，暂停执行
                    logger.info(f"   ⏸️ 等待人工确认: {tool_name}")
                    return {
                        "tool": tool_name,
                        "status": "pending_confirmation",
                        "confirmation_request_id": confirmation_result.get("request_id"),
                        "success": False
                    }
                else:
                    # 人工确认被拒绝
                    logger.warning(f"   ⛔ 人工确认被拒绝: {tool_name}")
                    error_result = {
                        "tool": tool_name,
                        "error": "敏感操作被拒绝",
                        "success": False
                    }
                    tool_calls.append(ToolCallRecord(
                        tool_name=tool_name,
                        params=tool_params,
                        error=error_result["error"],
                        iteration=iteration
                    ))
                    return error_result
        
        # 记录工具调用审计日志
        self._log_security_event(
            audit_logs=audit_logs,
            event_type="tool_call",
            user_id=user_id,
            tool_name=tool_name,
            tool_params=tool_params,
            action_taken="executing",
            details={"iteration": iteration}
        )
        
        # 执行工具
        tool_start = time.time()
        result = await self._execute_tool(
            tool_name=tool_name,
            params=tool_params,
            user_profile=user_profile
        )
        tool_time_ms = (time.time() - tool_start) * 1000
        
        # 记录工具调用
        self._total_tool_calls += 1
        tool_record = ToolCallRecord(
            tool_name=tool_name,
            params=tool_params,
            result=result if result.get("success") else None,
            error=result.get("error") if not result.get("success") else None,
            execution_time_ms=tool_time_ms,
            iteration=iteration
        )
        tool_calls.append(tool_record)
        
        # 记录执行完成的审计日志
        self._log_security_event(
            audit_logs=audit_logs,
            event_type="tool_complete",
            user_id=user_id,
            tool_name=tool_name,
            action_taken="executed" if result.get("success") else "failed",
            details={
                "execution_time_ms": tool_time_ms,
                "success": result.get("success", False)
            }
        )
        
        logger.info(f"   ✅ 工具执行完成: {tool_time_ms:.1f}ms")
        
        return result

    
    # =========================================================================
    # LLM决策方法
    # =========================================================================
    
    async def _llm_decide(self, context: Dict[str, Any]) -> AgentDecision:
        """
        LLM决策：选择下一步动作
        
        Args:
            context: 执行上下文
        
        Returns:
            AgentDecision: 决策结果
        
        Requirements: 8.1
        """
        # 构建提示词
        messages = self._build_decision_messages(context)
        
        # 构建工具列表
        tools = self._build_tools_schema()
        
        try:
            # 调用LLM
            response = await self.llm_client.chat(
                messages=messages,
                tools=tools if tools else None
            )
            
            # 解析决策
            return self._parse_decision(response, context)
            
        except Exception as e:
            logger.error(f"LLM决策失败: {e}")
            # 返回完成决策，避免无限循环
            return AgentDecision(
                action=AgentAction.FINISH,
                response=f"LLM决策失败: {str(e)}",
                reasoning=f"异常: {str(e)}"
            )
    
    def _build_decision_messages(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        构建LLM决策的消息列表
        
        Args:
            context: 执行上下文
        
        Returns:
            消息列表
        """
        messages = []
        
        # 系统提示
        system_prompt = self._build_system_prompt(context)
        messages.append({"role": "system", "content": system_prompt})
        
        # 用户查询
        messages.append({"role": "user", "content": context["query"]})
        
        # 添加之前的工具调用结果
        for tool_result in context.get("tool_results", []):
            if tool_result.get("success"):
                messages.append({
                    "role": "assistant",
                    "content": f"工具 {tool_result.get('tool', 'unknown')} 执行成功"
                })
                messages.append({
                    "role": "function",
                    "name": tool_result.get("tool", "unknown"),
                    "content": json.dumps(tool_result.get("data", {}), ensure_ascii=False)
                })
            else:
                messages.append({
                    "role": "assistant",
                    "content": f"工具 {tool_result.get('tool', 'unknown')} 执行失败: {tool_result.get('error', '未知错误')}"
                })
        
        return messages
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建系统提示词
        
        Args:
            context: 执行上下文
        
        Returns:
            系统提示词
        """
        user_profile = context.get("user_profile", {})
        iteration = context.get("iteration", 1)
        
        # 构建可用工具列表
        available_tools = list(self.tools.keys())
        if self.tool_whitelist:
            available_tools = [t for t in available_tools if t in self.tool_whitelist]
        
        prompt = f"""你是一个智能健身助手，可以使用以下工具来帮助用户：

可用工具：
{chr(10).join(f"- {name}: {self.tools[name].get_description() if hasattr(self.tools[name], 'get_description') else '无描述'}" for name in available_tools)}

用户档案：
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

当前迭代：{iteration}/{self.max_iterations}

指导原则：
1. 分析用户需求，选择合适的工具
2. 如果需要多个工具，按依赖顺序调用
3. 如果已收集足够信息，生成最终回答
4. 注意用户的健康状况和禁忌症
5. 如果不确定，可以先思考再决定

请根据用户的问题和已有的工具结果，决定下一步动作。"""
        
        return prompt

    
    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        """
        构建工具Schema列表（OpenAI function calling格式）
        
        Returns:
            工具Schema列表
        """
        tools_schema = []
        
        for name, tool in self.tools.items():
            # 白名单过滤
            if self.tool_whitelist and name not in self.tool_whitelist:
                continue
            
            # 获取工具Schema
            if hasattr(tool, 'get_openai_schema'):
                schema = tool.get_openai_schema()
            else:
                # 默认Schema
                description = tool.get_description() if hasattr(tool, 'get_description') else f"工具: {name}"
                schema = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
            
            tools_schema.append(schema)
        
        return tools_schema
    
    def _parse_decision(
        self,
        response: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentDecision:
        """
        解析LLM响应为决策
        
        Args:
            response: LLM响应
            context: 执行上下文
        
        Returns:
            AgentDecision: 决策结果
        """
        # 尝试解析工具调用
        tool_call = None
        if hasattr(self.llm_client, 'parse_tool_call'):
            try:
                tool_call = asyncio.get_event_loop().run_until_complete(
                    self.llm_client.parse_tool_call(response)
                )
            except RuntimeError:
                # 如果已经在事件循环中，直接解析
                pass
        
        # 如果没有工具调用，检查响应内容
        if not tool_call:
            # 检查是否有tool_calls字段（OpenAI格式）
            if "choices" in response:
                choice = response["choices"][0]
                message = choice.get("message", {})
                
                if message.get("tool_calls"):
                    tc = message["tool_calls"][0]
                    function = tc.get("function", {})
                    tool_call = {
                        "name": function.get("name"),
                        "arguments": json.loads(function.get("arguments", "{}"))
                    }
                elif message.get("content"):
                    # 没有工具调用，返回完成
                    return AgentDecision(
                        action=AgentAction.FINISH,
                        response=message["content"],
                        reasoning="LLM生成了最终回答"
                    )
        
        # 如果有工具调用
        if tool_call:
            return AgentDecision(
                action=AgentAction.CALL_TOOL,
                tool_name=tool_call.get("name"),
                tool_params=tool_call.get("arguments", {}),
                reasoning=f"LLM决定调用工具: {tool_call.get('name')}"
            )
        
        # 默认返回思考
        return AgentDecision(
            action=AgentAction.THINK,
            reasoning="无法解析LLM响应，继续思考"
        )

    
    # =========================================================================
    # 安全检查方法
    # =========================================================================
    
    def _safety_check(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> SafetyCheckResult:
        """
        安全检查：执行Layer3规则
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            user_profile: 用户档案
        
        Returns:
            SafetyCheckResult: 安全检查结果
        """
        warnings = []
        
        for rule in self.layer3_rules:
            if not rule.enabled:
                continue
            
            # 评估规则条件
            try:
                should_apply = self._evaluate_rule_condition(
                    rule=rule,
                    tool_name=tool_name,
                    params=params,
                    user_profile=user_profile
                )
                
                if not should_apply:
                    continue
                
                # 根据严重程度处理
                severity = rule.severity.value if hasattr(rule.severity, 'value') else str(rule.severity)
                
                if severity == "absolute":
                    # 绝对禁忌：阻止执行
                    logger.warning(f"   🚫 绝对禁忌规则触发: {rule.name}")
                    return SafetyCheckResult(
                        passed=False,
                        reason=rule.description,
                        warnings=[f"绝对禁忌: {rule.name}"],
                        blocked_by_rule=rule.rule_id
                    )
                
                elif severity == "relative":
                    # 相对禁忌：添加警告但允许执行
                    warnings.append(f"相对禁忌: {rule.name} - {rule.description}")
                    logger.info(f"   ⚠️ 相对禁忌规则触发: {rule.name}")
                
                elif severity == "caution":
                    # 注意事项：添加警告
                    warnings.append(f"注意: {rule.name} - {rule.description}")
                    logger.info(f"   ℹ️ 注意规则触发: {rule.name}")
                    
            except Exception as e:
                logger.warning(f"规则 {rule.rule_id} 评估失败: {e}")
                continue
        
        return SafetyCheckResult(
            passed=True,
            reason=None,
            warnings=warnings
        )
    
    def _evaluate_rule_condition(
        self,
        rule: 'Layer3Rule',
        tool_name: str,
        params: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> bool:
        """
        评估规则条件
        
        Args:
            rule: Layer3规则
            tool_name: 工具名称
            params: 工具参数
            user_profile: 用户档案
        
        Returns:
            bool: 规则是否应该应用
        """
        condition = rule.condition
        
        # 特殊条件处理
        if condition == "always":
            return True
        
        if condition == "never":
            return False
        
        # 用户健康状况相关条件
        if condition == "user_has_joint_injury":
            injuries = user_profile.get("injuries", [])
            conditions = user_profile.get("conditions", [])
            joint_keywords = ["关节", "膝", "肩", "腰", "踝", "腕", "肘"]
            
            for injury in injuries + conditions:
                if any(kw in str(injury) for kw in joint_keywords):
                    return True
            return False
        
        if condition == "user_has_postural_issues":
            postural_issues = user_profile.get("postural_issues", [])
            return len(postural_issues) > 0
        
        if condition == "user_in_rehabilitation":
            return user_profile.get("in_rehabilitation", False)
        
        if condition == "user_in_calorie_deficit":
            tdee = user_profile.get("tdee", 2000)
            intake = user_profile.get("daily_calorie_intake", tdee)
            threshold = rule.parameters.get("deficit_threshold", 0.8)
            return intake < tdee * threshold
        
        if condition == "user_has_body_type":
            return "body_type" in user_profile
        
        if condition == "user_has_goal":
            return "goal" in user_profile
        
        if condition == "muscle_not_recovered":
            # 检查肌肉恢复状态
            last_training = user_profile.get("last_training", {})
            return len(last_training) > 0
        
        if condition == "session_has_imbalance":
            # 检查训练平衡
            return False  # 默认不触发
        
        # 默认不触发
        return False

    
    # =========================================================================
    # 敏感操作检查和人工确认 - Requirements 8.7
    # =========================================================================
    
    async def _check_sensitive_operation(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_profile: Dict[str, Any],
        pending_confirmations: List[HumanConfirmationRequest],
        audit_logs: List[SecurityAuditLog]
    ) -> Dict[str, Any]:
        """
        检查敏感操作并处理人工确认
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            user_profile: 用户档案
            pending_confirmations: 待确认请求列表
            audit_logs: 审计日志列表
        
        Returns:
            Dict包含:
            - approved: 是否批准执行
            - status: pending | approved | rejected | not_sensitive
            - request_id: 确认请求ID（如果需要确认）
        
        Requirements: 8.7
        """
        user_id = user_profile.get("user_id", "unknown")
        
        # 检查是否是敏感工具
        if tool_name not in self.sensitive_tools:
            return {"approved": True, "status": "not_sensitive"}
        
        operation_type = self.sensitive_tools[tool_name]
        
        # 生成确认请求
        import uuid
        request_id = str(uuid.uuid4())[:8]
        
        confirmation_request = HumanConfirmationRequest(
            request_id=request_id,
            tool_name=tool_name,
            tool_params=params,
            operation_type=operation_type,
            reason=f"敏感操作: {operation_type.value}",
            user_id=user_id
        )
        
        # 记录审计日志
        self._log_security_event(
            audit_logs=audit_logs,
            event_type="human_confirm_request",
            user_id=user_id,
            tool_name=tool_name,
            tool_params=params,
            action_taken="pending_confirmation",
            details={
                "request_id": request_id,
                "operation_type": operation_type.value
            }
        )
        
        self._human_confirmations_requested += 1
        
        # 如果有回调函数，调用它获取确认
        if self.confirmation_callback:
            try:
                # 调用确认回调
                confirmation_result = await self._wait_for_confirmation(
                    confirmation_request
                )
                
                if confirmation_result["approved"]:
                    self._human_confirmations_approved += 1
                    confirmation_request.status = "approved"
                    confirmation_request.response_timestamp = time.time()
                    
                    self._log_security_event(
                        audit_logs=audit_logs,
                        event_type="human_confirm_approved",
                        user_id=user_id,
                        tool_name=tool_name,
                        action_taken="approved",
                        details={"request_id": request_id}
                    )
                    
                    return {"approved": True, "status": "approved", "request_id": request_id}
                else:
                    self._human_confirmations_rejected += 1
                    confirmation_request.status = "rejected"
                    confirmation_request.response_timestamp = time.time()
                    
                    self._log_security_event(
                        audit_logs=audit_logs,
                        event_type="human_confirm_rejected",
                        user_id=user_id,
                        tool_name=tool_name,
                        action_taken="rejected",
                        details={"request_id": request_id}
                    )
                    
                    pending_confirmations.append(confirmation_request)
                    return {"approved": False, "status": "rejected", "request_id": request_id}
                    
            except asyncio.TimeoutError:
                confirmation_request.status = "timeout"
                self._log_security_event(
                    audit_logs=audit_logs,
                    event_type="human_confirm_timeout",
                    user_id=user_id,
                    tool_name=tool_name,
                    action_taken="timeout",
                    details={"request_id": request_id}
                )
                pending_confirmations.append(confirmation_request)
                return {"approved": False, "status": "timeout", "request_id": request_id}
        
        # 没有回调函数，将请求添加到待确认列表
        pending_confirmations.append(confirmation_request)
        self._pending_confirmations[request_id] = confirmation_request
        
        return {"approved": False, "status": "pending", "request_id": request_id}
    
    async def _wait_for_confirmation(
        self,
        request: HumanConfirmationRequest
    ) -> Dict[str, Any]:
        """
        等待人工确认
        
        Args:
            request: 确认请求
        
        Returns:
            确认结果
        
        Requirements: 8.7
        """
        if self.confirmation_callback:
            try:
                # 使用超时等待确认
                result = await asyncio.wait_for(
                    self.confirmation_callback(request),
                    timeout=self.confirmation_timeout
                )
                return result
            except asyncio.TimeoutError:
                raise
        
        # 默认拒绝
        return {"approved": False, "reason": "no_callback"}
    
    def approve_confirmation(self, request_id: str, responder: str = "system") -> bool:
        """
        批准待确认的请求
        
        Args:
            request_id: 请求ID
            responder: 响应者
        
        Returns:
            是否成功批准
        
        Requirements: 8.7
        """
        if request_id not in self._pending_confirmations:
            return False
        
        request = self._pending_confirmations[request_id]
        request.status = "approved"
        request.response_timestamp = time.time()
        request.responder = responder
        
        self._human_confirmations_approved += 1
        
        # 记录安全日志
        security_logger.info(
            f"[CONFIRM_APPROVED] request_id={request_id} "
            f"tool={request.tool_name} "
            f"user={request.user_id} "
            f"responder={responder}"
        )
        
        return True
    
    def reject_confirmation(self, request_id: str, responder: str = "system", reason: str = "") -> bool:
        """
        拒绝待确认的请求
        
        Args:
            request_id: 请求ID
            responder: 响应者
            reason: 拒绝原因
        
        Returns:
            是否成功拒绝
        
        Requirements: 8.7
        """
        if request_id not in self._pending_confirmations:
            return False
        
        request = self._pending_confirmations[request_id]
        request.status = "rejected"
        request.response_timestamp = time.time()
        request.responder = responder
        
        self._human_confirmations_rejected += 1
        
        # 记录安全日志
        security_logger.info(
            f"[CONFIRM_REJECTED] request_id={request_id} "
            f"tool={request.tool_name} "
            f"user={request.user_id} "
            f"responder={responder} "
            f"reason={reason}"
        )
        
        return True
    
    def get_pending_confirmations(self) -> List[HumanConfirmationRequest]:
        """
        获取所有待确认的请求
        
        Returns:
            待确认请求列表
        """
        return [
            req for req in self._pending_confirmations.values()
            if req.status == "pending"
        ]
    
    # =========================================================================
    # 安全审计日志方法 - Requirements 8.7
    # =========================================================================
    
    def _log_security_event(
        self,
        audit_logs: List[SecurityAuditLog],
        event_type: str,
        user_id: str,
        tool_name: Optional[str] = None,
        tool_params: Optional[Dict[str, Any]] = None,
        safety_result: Optional[Dict[str, Any]] = None,
        rule_triggered: Optional[str] = None,
        action_taken: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityAuditLog:
        """
        记录安全审计日志
        
        Args:
            audit_logs: 审计日志列表（会被修改）
            event_type: 事件类型
            user_id: 用户ID
            tool_name: 工具名称
            tool_params: 工具参数
            safety_result: 安全检查结果
            rule_triggered: 触发的规则
            action_taken: 采取的动作
            details: 额外详情
        
        Returns:
            创建的审计日志
        
        Requirements: 8.7
        """
        import uuid
        
        log = SecurityAuditLog(
            log_id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            event_type=event_type,
            user_id=user_id,
            tool_name=tool_name,
            tool_params=tool_params,
            safety_result=safety_result,
            rule_triggered=rule_triggered,
            action_taken=action_taken,
            details=details or {}
        )
        
        # 添加到列表
        audit_logs.append(log)
        
        # 写入安全日志文件
        security_logger.info(log.to_log_string())
        
        return log
    
    def get_audit_logs_by_user(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取指定用户的审计日志
        
        注意：此方法需要从持久化存储读取，当前仅返回内存中的日志
        
        Args:
            user_id: 用户ID
            limit: 最大返回数量
        
        Returns:
            审计日志列表
        """
        # TODO: 从持久化存储读取
        return []
    
    # =========================================================================
    # 工具执行方法
    # =========================================================================
    
    def _check_whitelist(self, tool_name: str) -> bool:
        """
        检查工具是否在白名单中
        
        Args:
            tool_name: 工具名称
        
        Returns:
            bool: 是否允许调用
        
        Requirements: 8.3
        """
        # 如果没有设置白名单，允许所有工具
        if self.tool_whitelist is None:
            return True
        
        return tool_name in self.tool_whitelist
    
    async def _execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            user_profile: 用户档案
        
        Returns:
            工具执行结果
        """
        tool = self.tools.get(tool_name)
        if not tool:
            logger.error(f"工具不存在: {tool_name}")
            return {
                "success": False,
                "tool": tool_name,
                "error": f"工具 {tool_name} 不存在"
            }
        
        try:
            # 合并用户档案到参数
            input_data = {
                **params,
                "user_profile": user_profile
            }
            
            # 执行工具
            if hasattr(tool, 'execute'):
                result = await tool.execute(input_data)
            else:
                # 如果工具是可调用对象
                result = await tool(input_data)
            
            # 标准化结果格式
            if isinstance(result, dict):
                if "success" not in result:
                    result["success"] = True
                result["tool"] = tool_name
                return result
            else:
                return {
                    "success": True,
                    "tool": tool_name,
                    "data": result
                }
                
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e)
            }
    
    # =========================================================================
    # 工具管理方法
    # =========================================================================
    
    def add_tool(self, tool: Union[ToolInterface, Any]) -> None:
        """
        添加工具
        
        Args:
            tool: 工具实例
        """
        tool_name = tool.get_name() if hasattr(tool, 'get_name') else str(tool)
        self.tools[tool_name] = tool
        logger.info(f"添加工具: {tool_name}")
    
    def remove_tool(self, tool_name: str) -> bool:
        """
        移除工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            bool: 是否成功移除
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"移除工具: {tool_name}")
            return True
        return False
    
    def get_tool(self, tool_name: str) -> Optional[Union[ToolInterface, Any]]:
        """
        获取工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具实例或None
        """
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """
        列出所有工具
        
        Returns:
            工具名称列表
        """
        return list(self.tools.keys())
    
    def list_available_tools(self) -> List[str]:
        """
        列出可用工具（考虑白名单）
        
        Returns:
            可用工具名称列表
        """
        if self.tool_whitelist is None:
            return list(self.tools.keys())
        return [name for name in self.tools.keys() if name in self.tool_whitelist]

    
    # =========================================================================
    # 白名单管理方法
    # =========================================================================
    
    def set_whitelist(self, whitelist: Optional[List[str]]) -> None:
        """
        设置工具白名单
        
        Args:
            whitelist: 白名单列表（None表示允许所有工具）
        
        Requirements: 8.3
        """
        self.tool_whitelist = set(whitelist) if whitelist else None
        logger.info(f"设置工具白名单: {whitelist or '全部'}")
    
    def add_to_whitelist(self, tool_name: str) -> None:
        """
        添加工具到白名单
        
        Args:
            tool_name: 工具名称
        """
        if self.tool_whitelist is None:
            self.tool_whitelist = set()
        self.tool_whitelist.add(tool_name)
        logger.info(f"添加到白名单: {tool_name}")
    
    def remove_from_whitelist(self, tool_name: str) -> bool:
        """
        从白名单移除工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            bool: 是否成功移除
        """
        if self.tool_whitelist and tool_name in self.tool_whitelist:
            self.tool_whitelist.remove(tool_name)
            logger.info(f"从白名单移除: {tool_name}")
            return True
        return False
    
    def get_whitelist(self) -> Optional[List[str]]:
        """
        获取白名单
        
        Returns:
            白名单列表或None
        """
        return list(self.tool_whitelist) if self.tool_whitelist else None
    
    # =========================================================================
    # 配置方法
    # =========================================================================
    
    def set_max_iterations(self, max_iterations: int) -> None:
        """
        设置最大迭代次数
        
        Args:
            max_iterations: 最大迭代次数
        
        Requirements: 8.2
        """
        if max_iterations < 1:
            raise ValueError("最大迭代次数必须大于0")
        self.max_iterations = max_iterations
        logger.info(f"设置最大迭代次数: {max_iterations}")
    
    def set_timeout(self, timeout_seconds: float) -> None:
        """
        设置执行超时时间
        
        Args:
            timeout_seconds: 超时时间（秒）
        """
        if timeout_seconds <= 0:
            raise ValueError("超时时间必须大于0")
        self.timeout_seconds = timeout_seconds
        logger.info(f"设置超时时间: {timeout_seconds}s")
    
    def enable_safety_checks(self, enabled: bool = True) -> None:
        """
        启用/禁用安全检查
        
        Args:
            enabled: 是否启用
        
        Requirements: 8.4
        """
        self.enable_safety_check = enabled
        logger.info(f"安全检查: {'启用' if enabled else '禁用'}")
    
    def enable_human_confirmations(self, enabled: bool = True) -> None:
        """
        启用/禁用人工确认
        
        Args:
            enabled: 是否启用
        
        Requirements: 8.7
        """
        self.enable_human_confirmation = enabled
        logger.info(f"人工确认: {'启用' if enabled else '禁用'}")
    
    def set_confirmation_callback(self, callback: Optional[Callable]) -> None:
        """
        设置人工确认回调函数
        
        Args:
            callback: 回调函数，接收HumanConfirmationRequest，返回Dict
        
        Requirements: 8.7
        """
        self.confirmation_callback = callback
        logger.info(f"人工确认回调: {'已设置' if callback else '已清除'}")
    
    def set_confirmation_timeout(self, timeout_seconds: float) -> None:
        """
        设置人工确认超时时间
        
        Args:
            timeout_seconds: 超时时间（秒）
        
        Requirements: 8.7
        """
        if timeout_seconds <= 0:
            raise ValueError("超时时间必须大于0")
        self.confirmation_timeout = timeout_seconds
        logger.info(f"人工确认超时: {timeout_seconds}s")
    
    # =========================================================================
    # 敏感工具管理方法 - Requirements 8.7
    # =========================================================================
    
    def add_sensitive_tool(
        self,
        tool_name: str,
        operation_type: SensitiveOperationType
    ) -> None:
        """
        添加敏感工具
        
        Args:
            tool_name: 工具名称
            operation_type: 操作类型
        
        Requirements: 8.7
        """
        self.sensitive_tools[tool_name] = operation_type
        logger.info(f"添加敏感工具: {tool_name} -> {operation_type.value}")
    
    def remove_sensitive_tool(self, tool_name: str) -> bool:
        """
        移除敏感工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            是否成功移除
        
        Requirements: 8.7
        """
        if tool_name in self.sensitive_tools:
            del self.sensitive_tools[tool_name]
            logger.info(f"移除敏感工具: {tool_name}")
            return True
        return False
    
    def get_sensitive_tools(self) -> Dict[str, SensitiveOperationType]:
        """
        获取所有敏感工具
        
        Returns:
            敏感工具映射表
        
        Requirements: 8.7
        """
        return self.sensitive_tools.copy()
    
    def is_sensitive_tool(self, tool_name: str) -> bool:
        """
        检查工具是否是敏感工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            是否是敏感工具
        
        Requirements: 8.7
        """
        return tool_name in self.sensitive_tools
    
    # =========================================================================
    # 统计方法
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取执行统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "execution_count": self._execution_count,
            "total_iterations": self._total_iterations,
            "total_tool_calls": self._total_tool_calls,
            "average_iterations": (
                self._total_iterations / self._execution_count
                if self._execution_count > 0 else 0
            ),
            "tools_count": len(self.tools),
            "whitelist_count": len(self.tool_whitelist) if self.tool_whitelist else None,
            "rules_count": len(self.layer3_rules),
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            # 安全相关统计
            "blocked_by_safety": self._blocked_by_safety,
            "human_confirmations_requested": self._human_confirmations_requested,
            "human_confirmations_approved": self._human_confirmations_approved,
            "human_confirmations_rejected": self._human_confirmations_rejected,
            "pending_confirmations_count": len(self._pending_confirmations),
            "sensitive_tools_count": len(self.sensitive_tools),
            "human_confirmation_enabled": self.enable_human_confirmation,
            "safety_check_enabled": self.enable_safety_check
        }
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._execution_count = 0
        self._total_iterations = 0
        self._total_tool_calls = 0
        self._blocked_by_safety = 0
        self._human_confirmations_requested = 0
        self._human_confirmations_approved = 0
        self._human_confirmations_rejected = 0
        logger.info("统计信息已重置")


# =============================================================================
# 便捷函数
# =============================================================================

def create_agent_executor(
    tools: List[Union[ToolInterface, Any]],
    layer3_rules: List['Layer3Rule'],
    llm_client: LLMClientInterface,
    **kwargs
) -> AgentExecutor:
    """
    创建Agent执行器的便捷函数
    
    Args:
        tools: 工具列表
        layer3_rules: Layer3规则列表
        llm_client: LLM客户端
        **kwargs: 其他参数
    
    Returns:
        AgentExecutor: Agent执行器实例
    """
    return AgentExecutor(
        tools=tools,
        layer3_rules=layer3_rules,
        llm_client=llm_client,
        **kwargs
    )
