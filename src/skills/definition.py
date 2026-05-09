# -*- coding: utf-8 -*-
"""
Skill 定义数据类

定义 SkillDefinition 数据结构，描述一个 Skill 的完整元信息。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SkillDefinition:
    """Skill 定义数据类

    描述一个 Skill 的完整元信息，包括触发条件、所需工具、
    安全前置条件、输出标准等。

    Attributes:
        id: Skill 唯一标识符
        name: Skill 显示名称
        description: Skill 功能描述（供 LLM 选择时参考）
        triggers: 触发场景列表
        required_tools: 必须执行的工具列表（按顺序）
        optional_tools: 可选工具列表（根据上下文决定是否调用）
        safety_preconditions: 安全前置条件
        output_standard: 输出标准描述
        example_output: 输出示例
        degradation: 降级策略描述
        harness_checkpoints: Harness 检查点配置
    """

    id: str
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    optional_tools: List[str] = field(default_factory=list)
    safety_preconditions: Dict[str, Any] = field(default_factory=dict)
    output_standard: str = ""
    example_output: str = ""
    degradation: str = ""
    harness_checkpoints: Dict[str, str] = field(default_factory=dict)
