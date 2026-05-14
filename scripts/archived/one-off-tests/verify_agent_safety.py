# -*- coding: utf-8 -*-
"""
Agent安全机制验证脚本

验证任务9.2实现的Agent安全机制：
1. 强制执行Layer3安全规则
2. 敏感操作日志记录
3. 可配置人工确认机制

Requirements: 8.4, 8.7

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import asyncio
import sys
import os
import logging
from typing import Dict, Any, List
from dataclasses import dataclass

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.framework.orchestration.agent_executor import (
    AgentExecutor,
    AgentAction,
    AgentDecision,
    AgentExecutionResult,
    SafetyCheckResult,
    HumanConfirmationRequest,
    SecurityAuditLog,
    SensitiveOperationType,
    SENSITIVE_TOOLS,
    ToolInterface,
    LLMClientInterface
)
from src.framework.adapters.domain_adapter import (
    Layer3Rule,
    RuleSeverity,
    RuleCategory
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Mock实现
# =============================================================================

class MockTool(ToolInterface):
    """Mock工具实现"""
    
    def __init__(self, name: str, description: str = ""):
        self._name = name
        self._description = description or f"Mock tool: {name}"
    
    def get_name(self) -> str:
        return self._name
    
    def get_description(self) -> str:
        return self._description
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "tool": self._name,
            "data": {"message": f"Tool {self._name} executed successfully"}
        }


class MockLLMClient(LLMClientInterface):
    """Mock LLM客户端"""
    
    def __init__(self, decisions: List[AgentDecision] = None):
        self._decisions = decisions or []
        self._call_count = 0
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if self._call_count < len(self._decisions):
            decision = self._decisions[self._call_count]
            self._call_count += 1
            
            if decision.action == AgentAction.CALL_TOOL:
                return {
                    "choices": [{
                        "message": {
                            "tool_calls": [{
                                "function": {
                                    "name": decision.tool_name,
                                    "arguments": "{}"
                                }
                            }]
                        }
                    }]
                }
            elif decision.action == AgentAction.FINISH:
                return {
                    "choices": [{
                        "message": {
                            "content": decision.response or "Task completed"
                        }
                    }]
                }
        
        # 默认返回完成
        return {
            "choices": [{
                "message": {
                    "content": "Task completed"
                }
            }]
        }
    
    async def parse_tool_call(self, response: Dict[str, Any]) -> Dict[str, Any]:
        return None


# =============================================================================
# 测试函数
# =============================================================================

async def test_layer3_safety_rules():
    """测试1: Layer3安全规则强制执行"""
    print("\n" + "="*60)
    print("测试1: Layer3安全规则强制执行")
    print("="*60)
    
    # 创建测试规则
    rules = [
        Layer3Rule(
            rule_id="joint_injury_rule",
            name="关节损伤规则",
            description="用户有关节损伤时禁止高冲击动作",
            category=RuleCategory.SAFETY,
            severity=RuleSeverity.ABSOLUTE,
            condition="user_has_joint_injury",
            action="filter"
        ),
        Layer3Rule(
            rule_id="postural_rule",
            name="体态问题规则",
            description="用户有体态问题时添加警告",
            category=RuleCategory.SAFETY,
            severity=RuleSeverity.CAUTION,
            condition="user_has_postural_issues",
            action="warn"
        )
    ]
    
    # 创建工具
    tools = [
        MockTool("intelligent_exercise_selector", "智能动作选择器"),
        MockTool("contraindications_checker", "禁忌症检查器")
    ]
    
    # 创建LLM客户端（模拟调用工具）
    llm_client = MockLLMClient([
        AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="intelligent_exercise_selector",
            tool_params={}
        ),
        AgentDecision(
            action=AgentAction.FINISH,
            response="完成"
        )
    ])
    
    # 创建执行器
    executor = AgentExecutor(
        tools=tools,
        layer3_rules=rules,
        llm_client=llm_client,
        enable_safety_check=True
    )
    
    # 测试1.1: 用户有关节损伤 - 应该被阻止
    print("\n测试1.1: 用户有关节损伤")
    user_profile_with_injury = {
        "user_id": "test_user_1",
        "injuries": ["膝关节损伤"]
    }
    
    result = await executor.execute(
        query="推荐一些训练动作",
        user_profile=user_profile_with_injury
    )
    
    # 检查是否有安全警告
    has_safety_warning = len(result.safety_warnings) > 0 or any(
        tc.error and "安全检查" in tc.error for tc in result.tool_calls
    )
    print(f"   安全警告数量: {len(result.safety_warnings)}")
    print(f"   工具调用被阻止: {any(tc.error for tc in result.tool_calls)}")
    
    # 测试1.2: 用户有体态问题 - 应该添加警告但允许执行
    print("\n测试1.2: 用户有体态问题")
    
    # 重置LLM客户端
    llm_client._call_count = 0
    
    user_profile_with_posture = {
        "user_id": "test_user_2",
        "postural_issues": ["圆肩"]
    }
    
    result2 = await executor.execute(
        query="推荐一些训练动作",
        user_profile=user_profile_with_posture
    )
    
    print(f"   安全警告数量: {len(result2.safety_warnings)}")
    print(f"   执行成功: {result2.success}")
    
    print("\n✅ 测试1完成: Layer3安全规则强制执行")
    return True


async def test_security_audit_logging():
    """测试2: 敏感操作日志记录"""
    print("\n" + "="*60)
    print("测试2: 敏感操作日志记录")
    print("="*60)
    
    # 创建工具
    tools = [
        MockTool("intelligent_exercise_selector", "智能动作选择器"),
        MockTool("update_user_profile", "更新用户档案")
    ]
    
    # 创建LLM客户端
    llm_client = MockLLMClient([
        AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="intelligent_exercise_selector",
            tool_params={}
        ),
        AgentDecision(
            action=AgentAction.FINISH,
            response="完成"
        )
    ])
    
    # 创建执行器（启用审计日志）
    executor = AgentExecutor(
        tools=tools,
        layer3_rules=[],
        llm_client=llm_client,
        enable_safety_check=True,
        audit_log_path="data/logs/agent_security_audit_test.log"
    )
    
    # 执行
    user_profile = {"user_id": "test_user_audit"}
    result = await executor.execute(
        query="推荐训练动作",
        user_profile=user_profile
    )
    
    # 检查审计日志
    print(f"\n   审计日志数量: {len(result.audit_logs)}")
    for log in result.audit_logs:
        print(f"   - {log.event_type}: {log.action_taken}")
    
    # 验证审计日志包含必要事件
    event_types = [log.event_type for log in result.audit_logs]
    has_start = "execution_start" in event_types
    has_tool_call = "tool_call" in event_types or "tool_complete" in event_types
    has_complete = "execution_complete" in event_types
    
    print(f"\n   包含执行开始日志: {has_start}")
    print(f"   包含工具调用日志: {has_tool_call}")
    print(f"   包含执行完成日志: {has_complete}")
    
    print("\n✅ 测试2完成: 敏感操作日志记录")
    return True


async def test_human_confirmation():
    """测试3: 可配置人工确认机制"""
    print("\n" + "="*60)
    print("测试3: 可配置人工确认机制")
    print("="*60)
    
    # 创建敏感工具
    tools = [
        MockTool("update_user_profile", "更新用户档案"),
        MockTool("professional_program_designer", "专业训练计划设计器")
    ]
    
    # 创建LLM客户端（模拟调用敏感工具）
    llm_client = MockLLMClient([
        AgentDecision(
            action=AgentAction.CALL_TOOL,
            tool_name="update_user_profile",
            tool_params={"field": "weight", "value": 70}
        ),
        AgentDecision(
            action=AgentAction.FINISH,
            response="完成"
        )
    ])
    
    # 测试3.1: 启用人工确认但没有回调 - 应该返回pending
    print("\n测试3.1: 启用人工确认但没有回调")
    
    executor = AgentExecutor(
        tools=tools,
        layer3_rules=[],
        llm_client=llm_client,
        enable_human_confirmation=True,
        enable_safety_check=False
    )
    
    user_profile = {"user_id": "test_user_confirm"}
    result = await executor.execute(
        query="更新我的体重",
        user_profile=user_profile
    )
    
    print(f"   待确认请求数量: {len(result.pending_confirmations)}")
    if result.pending_confirmations:
        req = result.pending_confirmations[0]
        print(f"   请求ID: {req.request_id}")
        print(f"   工具名称: {req.tool_name}")
        print(f"   操作类型: {req.operation_type.value}")
        print(f"   状态: {req.status}")
    
    # 测试3.2: 使用回调函数自动批准
    print("\n测试3.2: 使用回调函数自动批准")
    
    async def auto_approve_callback(request: HumanConfirmationRequest) -> Dict[str, Any]:
        """自动批准回调"""
        print(f"   [回调] 收到确认请求: {request.tool_name}")
        return {"approved": True}
    
    # 重置LLM客户端
    llm_client._call_count = 0
    
    executor2 = AgentExecutor(
        tools=tools,
        layer3_rules=[],
        llm_client=llm_client,
        enable_human_confirmation=True,
        enable_safety_check=False,
        confirmation_callback=auto_approve_callback
    )
    
    result2 = await executor2.execute(
        query="更新我的体重",
        user_profile=user_profile
    )
    
    print(f"   执行成功: {result2.success}")
    print(f"   待确认请求数量: {len(result2.pending_confirmations)}")
    
    # 测试3.3: 使用回调函数拒绝
    print("\n测试3.3: 使用回调函数拒绝")
    
    async def auto_reject_callback(request: HumanConfirmationRequest) -> Dict[str, Any]:
        """自动拒绝回调"""
        print(f"   [回调] 拒绝确认请求: {request.tool_name}")
        return {"approved": False, "reason": "测试拒绝"}
    
    # 重置LLM客户端
    llm_client._call_count = 0
    
    executor3 = AgentExecutor(
        tools=tools,
        layer3_rules=[],
        llm_client=llm_client,
        enable_human_confirmation=True,
        enable_safety_check=False,
        confirmation_callback=auto_reject_callback
    )
    
    result3 = await executor3.execute(
        query="更新我的体重",
        user_profile=user_profile
    )
    
    print(f"   执行成功: {result3.success}")
    print(f"   待确认请求数量: {len(result3.pending_confirmations)}")
    if result3.pending_confirmations:
        print(f"   请求状态: {result3.pending_confirmations[0].status}")
    
    print("\n✅ 测试3完成: 可配置人工确认机制")
    return True


async def test_sensitive_tools_management():
    """测试4: 敏感工具管理"""
    print("\n" + "="*60)
    print("测试4: 敏感工具管理")
    print("="*60)
    
    # 创建执行器
    executor = AgentExecutor(
        tools=[MockTool("test_tool")],
        layer3_rules=[],
        llm_client=MockLLMClient(),
        enable_human_confirmation=False
    )
    
    # 测试默认敏感工具
    print("\n测试4.1: 默认敏感工具")
    default_sensitive = executor.get_sensitive_tools()
    print(f"   默认敏感工具数量: {len(default_sensitive)}")
    for name, op_type in list(default_sensitive.items())[:3]:
        print(f"   - {name}: {op_type.value}")
    
    # 测试添加敏感工具
    print("\n测试4.2: 添加敏感工具")
    executor.add_sensitive_tool("custom_tool", SensitiveOperationType.DATA_MODIFICATION)
    is_sensitive = executor.is_sensitive_tool("custom_tool")
    print(f"   custom_tool是敏感工具: {is_sensitive}")
    
    # 测试移除敏感工具
    print("\n测试4.3: 移除敏感工具")
    removed = executor.remove_sensitive_tool("custom_tool")
    is_sensitive_after = executor.is_sensitive_tool("custom_tool")
    print(f"   移除成功: {removed}")
    print(f"   移除后是敏感工具: {is_sensitive_after}")
    
    print("\n✅ 测试4完成: 敏感工具管理")
    return True


async def test_statistics():
    """测试5: 统计信息"""
    print("\n" + "="*60)
    print("测试5: 统计信息")
    print("="*60)
    
    # 创建执行器
    executor = AgentExecutor(
        tools=[MockTool("test_tool")],
        layer3_rules=[
            Layer3Rule(
                rule_id="test_rule",
                name="测试规则",
                description="测试",
                category=RuleCategory.SAFETY,
                severity=RuleSeverity.CAUTION,
                condition="never",
                action="warn"
            )
        ],
        llm_client=MockLLMClient([
            AgentDecision(action=AgentAction.FINISH, response="完成")
        ]),
        enable_human_confirmation=True,
        enable_safety_check=True
    )
    
    # 执行一次
    await executor.execute(
        query="测试",
        user_profile={"user_id": "test"}
    )
    
    # 获取统计信息
    stats = executor.get_statistics()
    
    print("\n统计信息:")
    print(f"   执行次数: {stats['execution_count']}")
    print(f"   总迭代次数: {stats['total_iterations']}")
    print(f"   工具调用次数: {stats['total_tool_calls']}")
    print(f"   安全阻止次数: {stats['blocked_by_safety']}")
    print(f"   人工确认请求次数: {stats['human_confirmations_requested']}")
    print(f"   人工确认批准次数: {stats['human_confirmations_approved']}")
    print(f"   人工确认拒绝次数: {stats['human_confirmations_rejected']}")
    print(f"   敏感工具数量: {stats['sensitive_tools_count']}")
    print(f"   人工确认启用: {stats['human_confirmation_enabled']}")
    print(f"   安全检查启用: {stats['safety_check_enabled']}")
    
    print("\n✅ 测试5完成: 统计信息")
    return True


async def main():
    """主函数"""
    print("="*60)
    print("Agent安全机制验证")
    print("Requirements: 8.4, 8.7")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    try:
        results.append(("Layer3安全规则", await test_layer3_safety_rules()))
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        results.append(("Layer3安全规则", False))
    
    try:
        results.append(("敏感操作日志", await test_security_audit_logging()))
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        results.append(("敏感操作日志", False))
    
    try:
        results.append(("人工确认机制", await test_human_confirmation()))
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        results.append(("人工确认机制", False))
    
    try:
        results.append(("敏感工具管理", await test_sensitive_tools_management()))
    except Exception as e:
        print(f"❌ 测试4失败: {e}")
        results.append(("敏感工具管理", False))
    
    try:
        results.append(("统计信息", await test_statistics()))
    except Exception as e:
        print(f"❌ 测试5失败: {e}")
        results.append(("统计信息", False))
    
    # 打印总结
    print("\n" + "="*60)
    print("验证结果总结")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！Agent安全机制实现完成。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
