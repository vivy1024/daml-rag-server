# -*- coding: utf-8 -*-
"""
MCP Prompts — REQ-5

将可复用的 prompt 模板暴露为 MCP Prompt，
供 LLM 客户端通过 prompts/get 端点获取预制提示词。

MCP 三层架构:
  - Tools:     mcp_tools/ 目录（执行动作）
  - Resources: mcp_resources/ 目录（静态知识）
  - Prompts:   本目录（预制 prompt 模板）

版本: v1.0.0
日期: 2026-04-05
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MCPPromptArgument:
    """Prompt 参数定义"""
    name: str
    description: str
    required: bool = True


@dataclass
class MCPPrompt:
    """MCP Prompt 定义"""
    name: str
    description: str
    arguments: List[MCPPromptArgument] = field(default_factory=list)
    template: str = ""  # 模板文本（支持 {arg_name} 占位符）

    def render(self, **kwargs) -> str:
        """渲染 prompt"""
        text = self.template
        for key, value in kwargs.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text

    def to_mcp_format(self) -> Dict[str, Any]:
        """转换为 MCP prompts/list 响应格式"""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [
                {
                    "name": arg.name,
                    "description": arg.description,
                    "required": arg.required,
                }
                for arg in self.arguments
            ],
        }


class MCPPromptRegistry:
    """
    MCP Prompt 注册表

    管理所有预制 prompt 模板，支持：
    - list: 列出所有 prompt
    - get: 按名称获取并渲染 prompt
    """

    def __init__(self):
        self._prompts: Dict[str, MCPPrompt] = {}
        self._register_builtin()

    def _register_builtin(self):
        """注册内置健身领域 prompt"""

        # 训练计划综合
        self.register(MCPPrompt(
            name="training-plan-synthesis",
            description="综合 DAG 工具结果，生成完整训练计划的 LLM 指令",
            arguments=[
                MCPPromptArgument("user_name", "用户姓名"),
                MCPPromptArgument("fitness_goal", "训练目标"),
                MCPPromptArgument("experience_level", "经验等级"),
                MCPPromptArgument("hard_constraints", "硬约束列表", required=False),
            ],
            template="""你是一位专业的健身教练。请综合以下工具执行结果，为 {user_name} 生成完整的训练计划。

## 用户目标
{fitness_goal}

## 经验等级
{experience_level}

## 硬约束（绝对不可违反）
{hard_constraints}

## 输出要求
1. 分阶段列出每个训练日的动作、组数、次数、重量
2. 标注安全注意事项
3. 提供渐进超负荷建议
4. 如果工具结果中有任何安全警告，必须在计划中体现

请用专业但友好的语气输出。""",
        ))

        # 安全评估
        self.register(MCPPrompt(
            name="safety-assessment-report",
            description="生成安全评估报告的 LLM 指令",
            arguments=[
                MCPPromptArgument("user_name", "用户姓名"),
                MCPPromptArgument("health_conditions", "健康状况描述"),
            ],
            template="""你是一位运动医学专家。请综合禁忌症检查和损伤风险评估结果，为 {user_name} 生成安全评估报告。

## 用户健康状况
{health_conditions}

## 报告要求
1. 列出所有发现的禁忌动作，按严重程度分级
2. 给出安全替代方案
3. 标注需要医疗咨询的情况
4. 语气严谨专业，安全优先""",
        ))

        # 营养方案
        self.register(MCPPrompt(
            name="nutrition-plan-synthesis",
            description="综合营养工具结果，生成膳食方案的 LLM 指令",
            arguments=[
                MCPPromptArgument("user_name", "用户姓名"),
                MCPPromptArgument("fitness_goal", "训练目标"),
                MCPPromptArgument("dietary_preferences", "饮食偏好", required=False),
            ],
            template="""你是一位运动营养师。请综合 TDEE 计算结果和营养分析数据，为 {user_name} 制定膳食方案。

## 训练目标
{fitness_goal}

## 饮食偏好
{dietary_preferences}

## 输出要求
1. 每日总热量和宏量营养素分配
2. 三餐 + 训练前后加餐的具体食谱
3. 补剂建议（如有）
4. 实用的采购和备餐建议""",
        ))

        # Harness 降级提示
        self.register(MCPPrompt(
            name="harness-policy-deny-fallback",
            description="当 harness 策略拒绝时，引导 LLM 给出安全降级回复",
            arguments=[
                MCPPromptArgument("deny_reason", "拒绝原因"),
                MCPPromptArgument("template_id", "被拒绝的模板"),
            ],
            template="""系统安全策略拦截了本次操作。

## 拦截信息
- 模板: {template_id}
- 原因: {deny_reason}

## 你的任务
1. 向用户解释当前无法完成该请求的原因（不要暴露内部系统细节）
2. 建议用户补充健康信息或选择更安全的训练方案
3. 如果涉及健康风险，建议咨询医生
4. 保持友好专业的语气""",
        ))

        logger.info(f"📝 MCP Prompts 注册完成: {len(self._prompts)} 个模板")

    def register(self, prompt: MCPPrompt):
        """注册 prompt"""
        self._prompts[prompt.name] = prompt

    def list_prompts(self) -> List[Dict[str, Any]]:
        """列出所有 prompt（MCP prompts/list 格式）"""
        return [p.to_mcp_format() for p in self._prompts.values()]

    def get_prompt(self, name: str, **kwargs) -> Optional[str]:
        """
        获取并渲染 prompt

        Args:
            name: prompt 名称
            **kwargs: 模板参数

        Returns:
            渲染后的 prompt 文本
        """
        prompt = self._prompts.get(name)
        if prompt is None:
            logger.warning(f"⚠️ 未知 prompt: {name}")
            return None
        return prompt.render(**kwargs)

    def get_prompt_definition(self, name: str) -> Optional[MCPPrompt]:
        """获取 prompt 定义"""
        return self._prompts.get(name)


# 单例
_registry: Optional[MCPPromptRegistry] = None


def get_prompt_registry() -> MCPPromptRegistry:
    """获取 prompt 注册表（单例）"""
    global _registry
    if _registry is None:
        _registry = MCPPromptRegistry()
    return _registry
