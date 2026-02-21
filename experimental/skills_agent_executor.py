# -*- coding: utf-8 -*-
"""
SkillsAgentExecutor - 基于Skills的Agent模式执行器

核心特性（与传统Agent的区别）：
1. 渐进式披露：LLM先看技能列表（Level 1），按需加载详情（Level 2）
2. 技能驱动：LLM通过load_skill获取执行指令，而非直接调用工具
3. Token优化：只加载需要的技能，避免context window bloat
4. 安全机制：Layer3规则在工具执行前强制检查

工作流程：
1. LLM看到技能列表（~650 tokens）
2. LLM调用load_skill获取技能详情（~500 tokens/skill）
3. LLM根据技能指令调用工具
4. 安全检查 + 工具执行
5. LLM综合结果生成响应

Requirements: 8.1-8.4

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
import time
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING, Callable
from enum import Enum

from .skill_manager import SkillManager
from .load_skill_tool import LoadSkillTool

if TYPE_CHECKING:
    from src.framework.adapters.domain_adapter import Layer3Rule

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举定义
# =============================================================================

class AgentAction(Enum):
    """Agent动作类型"""
    LOAD_SKILL = "load_skill"  # 加载技能（Level 2）
    CALL_TOOL = "call_tool"    # 调用工具（Level 3）
    FINISH = "finish"          # 完成任务
    THINK = "think"            # 继续思考


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class AgentDecision:
    """
    Agent决策结果
    
    Attributes:
        action: 动作类型
        skill_id: 技能ID（LOAD_SKILL时使用）
        tool_name: 工具名称（CALL_TOOL时使用）
        tool_params: 工具参数
        response: 最终响应（FINISH时使用）
        reasoning: 决策推理过程
    """
    action: AgentAction
    skill_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    response: Optional[str] = None
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "action": self.action.value,
            "skill_id": self.skill_id,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "response": self.response,
            "reasoning": self.reasoning
        }


@dataclass
class AgentExecutionResult:
    """
    Agent执行结果
    
    Attributes:
        success: 是否成功
        response: 最终响应
        iterations: 迭代次数
        skills_loaded: 加载的技能列表
        tool_calls: 工具调用记录
        total_time_ms: 总执行时间（毫秒）
        safety_warnings: 安全警告列表
        token_usage: Token使用统计
    """
    success: bool
    response: str
    iterations: int
    skills_loaded: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    total_time_ms: float = 0.0
    safety_warnings: List[str] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "response": self.response,
            "iterations": self.iterations,
            "skills_loaded": self.skills_loaded,
            "tool_calls": self.tool_calls,
            "total_time_ms": self.total_time_ms,
            "safety_warnings": self.safety_warnings,
            "token_usage": self.token_usage
        }


@dataclass
class SafetyCheckResult:
    """安全检查结果"""
    passed: bool
    reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    blocked_by_rule: Optional[str] = None


# =============================================================================
# SkillsAgentExecutor
# =============================================================================

class SkillsAgentExecutor:
    """
    基于Skills的Agent模式执行器
    
    核心特性（与传统Agent的区别）：
    1. 渐进式披露：LLM先看技能列表（Level 1），按需加载详情（Level 2）
    2. 技能驱动：LLM通过load_skill获取执行指令，而非直接调用工具
    3. Token优化：只加载需要的技能，避免context window bloat
    4. 安全机制：Layer3规则在工具执行前强制检查
    
    工作流程：
    1. LLM看到技能列表（~650 tokens）
    2. LLM调用load_skill获取技能详情（~500 tokens/skill）
    3. LLM根据技能指令调用工具
    4. 安全检查 + 工具执行
    5. LLM综合结果生成响应
    
    使用示例:
    ```python
    from src.framework.skills import SkillsAgentExecutor, SkillManager
    
    # 创建管理器
    manager = SkillManager()
    manager.register_from_dag_templates(templates)
    
    # 创建执行器
    executor = SkillsAgentExecutor(
        skill_manager=manager,
        tools=mcp_tools,
        layer3_rules=rules,
        llm_client=llm_client
    )
    
    # 执行
    result = await executor.execute(
        query="帮我制定一个增肌训练计划",
        user_profile={"goal": "增肌"}
    )
    ```
    
    Requirements: 8.1-8.4
    """
    
    # 默认配置
    DEFAULT_MAX_ITERATIONS = 10
    DEFAULT_TIMEOUT_SECONDS = 60
    
    def __init__(
        self,
        skill_manager: SkillManager,
        tools: Dict[str, Any],
        layer3_rules: List['Layer3Rule'],
        llm_client: Any,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        enable_human_confirmation: bool = False,
        tool_whitelist: Optional[List[str]] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    ):
        """
        初始化SkillsAgentExecutor
        
        Args:
            skill_manager: 技能管理器
            tools: 工具实例映射（工具名 -> 工具实例）
            layer3_rules: Layer3安全规则列表
            llm_client: LLM客户端
            max_iterations: 最大迭代次数
            enable_human_confirmation: 是否启用人工确认
            tool_whitelist: 工具白名单（None表示允许所有）
            timeout_seconds: 超时时间（秒）
        
        Requirements: 8.1-8.4
        """
        self.skill_manager = skill_manager
        self.tools = tools
        self.layer3_rules = layer3_rules
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.enable_human_confirmation = enable_human_confirmation
        self.tool_whitelist = tool_whitelist
        self.timeout_seconds = timeout_seconds
        
        # 创建load_skill工具
        self.load_skill_tool = LoadSkillTool(skill_manager)
        
        # 统计信息
        self._execution_count = 0
        self._total_iterations = 0
        self._total_tool_calls = 0
        self._safety_blocks = 0
        
        logger.info(
            f"✅ SkillsAgentExecutor初始化完成: "
            f"{skill_manager.get_skill_count()}个技能, "
            f"{len(tools)}个工具, "
            f"{len(layer3_rules)}条规则, "
            f"最大迭代={max_iterations}"
        )
    
    # =========================================================================
    # System Prompt生成
    # =========================================================================
    
    def get_system_prompt(self, domain: str = "健身") -> str:
        """
        生成Agent模式的system prompt
        
        包含：
        - 角色定义
        - 技能列表（Level 1）
        - 使用说明
        
        Args:
            domain: 领域名称
        
        Returns:
            str: system prompt
        """
        skills_list = self.skill_manager.get_system_prompt_skills()
        
        return f"""你是一个专业的{domain}教练AI助手。

{skills_list}

## 使用说明
1. 根据用户问题，选择合适的技能
2. 调用 load_skill(skill_id) 获取技能详情
3. 根据技能指令调用相应工具
4. 综合工具结果生成专业回答

## 响应格式
当你需要执行动作时，使用以下JSON格式：
```json
{{"action": "load_skill", "skill_id": "技能ID"}}
```
或
```json
{{"action": "call_tool", "tool_name": "工具名", "params": {{...}}}}
```
或
```json
{{"action": "finish", "response": "最终回答"}}
```

## 注意事项
- 必须先load_skill再执行工具
- 遵守技能中的安全约束
- 响应要专业、友好、实用
- 如果用户问题简单，可以直接回答，不需要调用技能
"""
    
    # =========================================================================
    # 主执行方法
    # =========================================================================
    
    async def execute(
        self,
        query: str,
        user_profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AgentExecutionResult:
        """
        执行基于Skills的Agent模式
        
        流程：
        1. 构建包含技能列表的system prompt
        2. LLM决策（选择技能或工具）
        3. 如果是load_skill，加载技能内容
        4. 如果是call_tool，执行安全检查+工具
        5. 重复直到完成或达到最大迭代
        
        Args:
            query: 用户查询
            user_profile: 用户档案
            context: 额外上下文
            conversation_history: 对话历史
        
        Returns:
            AgentExecutionResult: 执行结果
        
        Requirements: 8.1-8.4
        """
        self._execution_count += 1
        start_time = time.time()
        
        logger.info(f"🤖 Agent执行 #{self._execution_count}: {query[:50]}...")
        
        # 初始化执行上下文
        skills_loaded = []
        tool_calls = []
        safety_warnings = []
        
        # 构建初始消息
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
        ]
        
        # 添加对话历史
        if conversation_history:
            messages.extend(conversation_history)
        
        # 添加用户查询
        messages.append({"role": "user", "content": query})
        
        # 迭代执行
        for i in range(self.max_iterations):
            self._total_iterations += 1
            iteration = i + 1
            
            logger.info(f"   迭代 {iteration}/{self.max_iterations}")
            
            # LLM决策
            decision = await self._llm_decide(messages, user_profile, context)
            
            logger.info(f"   决策: {decision.action.value}")
            
            # 处理决策
            if decision.action == AgentAction.FINISH:
                # 完成任务
                total_time = (time.time() - start_time) * 1000
                
                logger.info(f"✅ Agent执行完成: {iteration}次迭代, {total_time:.0f}ms")
                
                return AgentExecutionResult(
                    success=True,
                    response=decision.response or "",
                    iterations=iteration,
                    skills_loaded=skills_loaded,
                    tool_calls=tool_calls,
                    total_time_ms=total_time,
                    safety_warnings=safety_warnings
                )
            
            elif decision.action == AgentAction.LOAD_SKILL:
                # 加载技能（Level 2）
                skill_id = decision.skill_id
                if skill_id:
                    skill_content = self.skill_manager.load_skill(skill_id)
                    skills_loaded.append(skill_id)
                    
                    # 将技能内容添加到对话
                    messages.append({
                        "role": "assistant",
                        "content": f"调用 load_skill(\"{skill_id}\")"
                    })
                    messages.append({
                        "role": "tool",
                        "content": skill_content
                    })
                    
                    logger.info(f"   📖 加载技能: {skill_id}")
            
            elif decision.action == AgentAction.CALL_TOOL:
                # 调用工具（Level 3）
                tool_name = decision.tool_name
                tool_params = decision.tool_params or {}
                
                # 白名单检查
                if self.tool_whitelist and tool_name not in self.tool_whitelist:
                    logger.warning(f"   ⚠️ 工具 {tool_name} 不在白名单中")
                    messages.append({
                        "role": "tool",
                        "content": f"错误：工具 {tool_name} 不在允许列表中"
                    })
                    continue
                
                # 安全检查
                safety_result = self._safety_check(
                    tool_name,
                    tool_params,
                    user_profile
                )
                
                if not safety_result.passed:
                    self._safety_blocks += 1
                    safety_warnings.extend(safety_result.warnings)
                    
                    logger.warning(f"   🛡️ 安全检查未通过: {safety_result.reason}")
                    
                    messages.append({
                        "role": "tool",
                        "content": f"安全检查未通过: {safety_result.reason}"
                    })
                    continue
                
                # 执行工具
                result = await self._execute_tool(
                    tool_name,
                    tool_params,
                    user_profile
                )
                
                self._total_tool_calls += 1
                
                tool_calls.append({
                    "tool": tool_name,
                    "params": tool_params,
                    "result": result,
                    "iteration": iteration
                })
                
                # 将结果添加到对话
                messages.append({
                    "role": "assistant",
                    "content": f"调用 {tool_name}({json.dumps(tool_params, ensure_ascii=False)})"
                })
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False, indent=2)
                })
                
                logger.info(f"   🔧 执行工具: {tool_name}")
            
            elif decision.action == AgentAction.THINK:
                # 继续思考
                messages.append({
                    "role": "assistant",
                    "content": decision.reasoning
                })
        
        # 达到最大迭代次数
        total_time = (time.time() - start_time) * 1000
        
        logger.warning(f"⚠️ Agent达到最大迭代次数: {self.max_iterations}")
        
        return AgentExecutionResult(
            success=False,
            response="抱歉，我需要更多时间来处理您的请求。请尝试简化您的问题。",
            iterations=self.max_iterations,
            skills_loaded=skills_loaded,
            tool_calls=tool_calls,
            total_time_ms=total_time,
            safety_warnings=safety_warnings
        )
    
    # =========================================================================
    # LLM决策
    # =========================================================================
    
    async def _llm_decide(
        self,
        messages: List[Dict[str, str]],
        user_profile: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> AgentDecision:
        """
        LLM决策：选择下一步动作
        
        Args:
            messages: 对话消息列表
            user_profile: 用户档案
            context: 额外上下文
        
        Returns:
            AgentDecision: 决策结果
        """
        try:
            # 调用LLM
            response = await self.llm_client.chat(messages)
            
            # 解析决策
            return self._parse_decision(response)
            
        except Exception as e:
            logger.error(f"❌ LLM决策失败: {e}")
            return AgentDecision(
                action=AgentAction.FINISH,
                response=f"抱歉，处理您的请求时出现了问题: {str(e)}",
                reasoning=f"LLM调用失败: {e}"
            )
    
    def _parse_decision(self, response: str) -> AgentDecision:
        """
        解析LLM响应为决策
        
        Args:
            response: LLM响应文本
        
        Returns:
            AgentDecision: 解析后的决策
        """
        # 尝试提取JSON
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                action_str = data.get("action", "finish")
                
                if action_str == "load_skill":
                    return AgentDecision(
                        action=AgentAction.LOAD_SKILL,
                        skill_id=data.get("skill_id"),
                        reasoning=data.get("reasoning", "")
                    )
                
                elif action_str == "call_tool":
                    return AgentDecision(
                        action=AgentAction.CALL_TOOL,
                        tool_name=data.get("tool_name"),
                        tool_params=data.get("params", {}),
                        reasoning=data.get("reasoning", "")
                    )
                
                elif action_str == "finish":
                    return AgentDecision(
                        action=AgentAction.FINISH,
                        response=data.get("response", response),
                        reasoning=data.get("reasoning", "")
                    )
                
                elif action_str == "think":
                    return AgentDecision(
                        action=AgentAction.THINK,
                        reasoning=data.get("reasoning", response)
                    )
                    
            except json.JSONDecodeError:
                pass
        
        # 如果没有找到有效的JSON，假设是最终响应
        return AgentDecision(
            action=AgentAction.FINISH,
            response=response,
            reasoning="无法解析为动作，作为最终响应"
        )
    
    # =========================================================================
    # 安全检查
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
        
        Requirements: 8.4
        """
        warnings = []
        
        for rule in self.layer3_rules:
            # 检查规则是否启用
            if hasattr(rule, 'enabled') and not rule.enabled:
                continue
            
            # 评估规则条件
            if self._evaluate_rule_condition(rule, tool_name, params, user_profile):
                severity = getattr(rule, 'severity', None)
                severity_value = severity.value if hasattr(severity, 'value') else str(severity)
                
                if severity_value == "absolute":
                    # 绝对禁忌，阻止执行
                    rule_name = getattr(rule, 'name', 'unknown')
                    rule_desc = getattr(rule, 'description', '')
                    return SafetyCheckResult(
                        passed=False,
                        reason=f"绝对禁忌: {rule_desc}",
                        warnings=[f"规则 {rule_name} 阻止了此操作"],
                        blocked_by_rule=getattr(rule, 'rule_id', None)
                    )
                
                elif severity_value == "relative":
                    # 相对禁忌，添加警告但允许执行
                    rule_name = getattr(rule, 'name', 'unknown')
                    warnings.append(f"注意: {rule_name}")
                
                elif severity_value == "caution":
                    # 注意事项
                    rule_name = getattr(rule, 'name', 'unknown')
                    warnings.append(f"提示: {rule_name}")
        
        return SafetyCheckResult(
            passed=True,
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
            bool: 条件是否满足
        """
        condition = getattr(rule, 'condition', '')
        
        # 简单条件评估
        if condition == "always":
            return True
        
        if condition == "user_has_joint_injury":
            injuries = user_profile.get("injuries", [])
            conditions = user_profile.get("conditions", [])
            return bool(injuries or conditions)
        
        if condition == "user_has_postural_issues":
            postural_issues = user_profile.get("postural_issues", [])
            return bool(postural_issues)
        
        if condition == "user_in_rehabilitation":
            return user_profile.get("in_rehabilitation", False)
        
        if condition == "user_in_calorie_deficit":
            return user_profile.get("calorie_deficit", False)
        
        # 默认不触发
        return False
    
    # =========================================================================
    # 工具执行
    # =========================================================================
    
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
            Dict: 工具执行结果
        """
        # 特殊处理load_skill
        if tool_name == "load_skill":
            return await self.load_skill_tool.execute(params)
        
        # 获取工具实例
        tool = self.tools.get(tool_name)
        if not tool:
            return {"error": f"工具 {tool_name} 不存在"}
        
        try:
            # 注入用户档案
            execution_params = {**params, "user_profile": user_profile}
            
            # 执行工具
            if hasattr(tool, 'execute'):
                result = await tool.execute(execution_params)
            elif callable(tool):
                result = await tool(execution_params)
            else:
                return {"error": f"工具 {tool_name} 不可执行"}
            
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"❌ 工具 {tool_name} 执行失败: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # 统计信息
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取执行器统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            "execution_count": self._execution_count,
            "total_iterations": self._total_iterations,
            "total_tool_calls": self._total_tool_calls,
            "safety_blocks": self._safety_blocks,
            "avg_iterations": (
                self._total_iterations / self._execution_count
                if self._execution_count > 0 else 0
            ),
            "skills_count": self.skill_manager.get_skill_count(),
            "tools_count": len(self.tools),
            "rules_count": len(self.layer3_rules),
            "max_iterations": self.max_iterations
        }
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._execution_count = 0
        self._total_iterations = 0
        self._total_tool_calls = 0
        self._safety_blocks = 0
        logger.info("📊 统计信息已重置")


# =============================================================================
# 工厂函数
# =============================================================================

def create_skills_agent_executor(
    skill_manager: SkillManager,
    tools: Dict[str, Any],
    layer3_rules: List['Layer3Rule'],
    llm_client: Any,
    max_iterations: int = SkillsAgentExecutor.DEFAULT_MAX_ITERATIONS
) -> SkillsAgentExecutor:
    """
    创建SkillsAgentExecutor实例
    
    Args:
        skill_manager: 技能管理器
        tools: 工具实例映射
        layer3_rules: Layer3规则列表
        llm_client: LLM客户端
        max_iterations: 最大迭代次数
    
    Returns:
        SkillsAgentExecutor: 执行器实例
    """
    return SkillsAgentExecutor(
        skill_manager=skill_manager,
        tools=tools,
        layer3_rules=layer3_rules,
        llm_client=llm_client,
        max_iterations=max_iterations
    )
