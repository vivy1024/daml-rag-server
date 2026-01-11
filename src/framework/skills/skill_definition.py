# -*- coding: utf-8 -*-
"""
Skills数据结构定义

渐进式披露（Progressive Disclosure）三层架构：
- Level 1: SkillMetadata - 轻量元数据（~50 tokens/skill，始终在system prompt）
- Level 2: SkillContent - 完整指令（~500 tokens/skill，按需加载）
- Level 3: SkillExecution - 执行资源（执行时加载）

核心优势：
- 传统Agent模式：13个DAG模板 + 18个MCP工具 = ~5000 tokens（始终占用）
- Skills模式：13个技能元数据 = ~650 tokens + 按需加载

Requirements: 8.1

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from src.framework.adapters.domain_adapter import DAGTemplateDefinition, Layer3Rule

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举定义
# =============================================================================

class SkillCategory(Enum):
    """
    技能类别
    
    与DAG模板类别对应
    """
    TRAINING = "training"           # 训练相关
    NUTRITION = "nutrition"         # 营养相关
    SAFETY = "safety"               # 安全评估
    COMPREHENSIVE = "comprehensive" # 综合方案
    QUICK = "quick"                 # 快速咨询
    CUSTOM = "custom"               # 自定义


# =============================================================================
# Level 1: 技能元数据（轻量，始终在system prompt）
# =============================================================================

@dataclass
class SkillMetadata:
    """
    Level 1: 技能元数据
    
    设计原则：
    - 每个技能的元数据控制在50 tokens以内
    - 只包含名称、描述、适用场景
    - 不包含具体实现细节
    
    Attributes:
        skill_id: 技能唯一标识
        name: 技能名称
        description: 一句话描述（不超过50字）
        category: 技能类别
        keywords: 触发关键词（用于意图匹配）
        complexity_level: 复杂度级别（1-3）
        estimated_tokens: 预估token消耗
    
    Requirements: 8.1
    """
    skill_id: str
    name: str
    description: str  # 一句话描述，不超过50字
    category: SkillCategory
    keywords: List[str] = field(default_factory=list)
    complexity_level: int = 1
    estimated_tokens: int = 50
    
    def to_system_prompt_format(self) -> str:
        """
        转换为system prompt格式
        
        格式：- skill_id: description
        
        Returns:
            str: system prompt格式的技能描述
        """
        return f"- {self.skill_id}: {self.description}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "keywords": self.keywords,
            "complexity_level": self.complexity_level,
            "estimated_tokens": self.estimated_tokens
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillMetadata':
        """从字典创建"""
        return cls(
            skill_id=data["skill_id"],
            name=data["name"],
            description=data["description"],
            category=SkillCategory(data.get("category", "custom")),
            keywords=data.get("keywords", []),
            complexity_level=data.get("complexity_level", 1),
            estimated_tokens=data.get("estimated_tokens", 50)
        )


# =============================================================================
# Level 2: 技能完整内容（按需加载）
# =============================================================================

@dataclass
class SkillContent:
    """
    Level 2: 技能完整内容
    
    设计原则：
    - 包含完整的执行指令
    - 包含工具调用顺序和依赖
    - 包含安全约束和响应提示
    - 通过load_skill工具按需加载
    
    Attributes:
        skill_id: 技能唯一标识
        full_description: 详细描述
        applicable_intents: 适用意图列表
        required_tools: 必需工具列表
        optional_tools: 可选工具列表
        tool_dependencies: 工具依赖关系
        parallel_groups: 并行执行组
        safety_constraints: 安全约束
        response_hint: 响应生成提示
        expected_output: 预期输出
        estimated_duration_seconds: 预估执行时间
    
    Requirements: 8.1
    """
    skill_id: str
    full_description: str
    applicable_intents: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    optional_tools: List[str] = field(default_factory=list)
    tool_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    parallel_groups: List[List[str]] = field(default_factory=list)
    safety_constraints: List[str] = field(default_factory=list)
    response_hint: str = ""
    expected_output: Dict[str, str] = field(default_factory=dict)
    estimated_duration_seconds: float = 10.0
    
    def to_skill_md(self) -> str:
        """
        转换为SKILL.md格式（供LLM阅读）
        
        Returns:
            str: Markdown格式的技能说明
        """
        # 工具列表
        required_tools_str = ", ".join(self.required_tools) if self.required_tools else "无"
        optional_tools_str = ", ".join(self.optional_tools) if self.optional_tools else "无"
        
        # 安全约束
        constraints_str = "\n".join(f"- {c}" for c in self.safety_constraints) if self.safety_constraints else "- 无特殊约束"
        
        # 适用场景
        intents_str = ", ".join(self.applicable_intents[:5]) if self.applicable_intents else "通用"
        
        # 工具依赖关系
        deps_lines = []
        for tool, deps in self.tool_dependencies.items():
            if deps:
                deps_lines.append(f"- {tool} 依赖: {', '.join(deps)}")
        deps_str = "\n".join(deps_lines) if deps_lines else "- 无依赖关系"
        
        # 预期输出
        output_lines = [f"- {k}: {v}" for k, v in self.expected_output.items()]
        output_str = "\n".join(output_lines) if output_lines else "- 根据用户需求生成响应"
        
        return f"""# 技能: {self.skill_id}

## 描述
{self.full_description}

## 适用场景
{intents_str}

## 必需工具
{required_tools_str}

## 可选工具
{optional_tools_str}

## 工具依赖关系
{deps_str}

## 安全约束
{constraints_str}

## 预期输出
{output_str}

## 响应指南
{self.response_hint if self.response_hint else "根据工具结果生成专业、友好的响应"}

## 预估执行时间
{self.estimated_duration_seconds}秒
"""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "full_description": self.full_description,
            "applicable_intents": self.applicable_intents,
            "required_tools": self.required_tools,
            "optional_tools": self.optional_tools,
            "tool_dependencies": self.tool_dependencies,
            "parallel_groups": self.parallel_groups,
            "safety_constraints": self.safety_constraints,
            "response_hint": self.response_hint,
            "expected_output": self.expected_output,
            "estimated_duration_seconds": self.estimated_duration_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillContent':
        """从字典创建"""
        return cls(
            skill_id=data["skill_id"],
            full_description=data.get("full_description", ""),
            applicable_intents=data.get("applicable_intents", []),
            required_tools=data.get("required_tools", []),
            optional_tools=data.get("optional_tools", []),
            tool_dependencies=data.get("tool_dependencies", {}),
            parallel_groups=data.get("parallel_groups", []),
            safety_constraints=data.get("safety_constraints", []),
            response_hint=data.get("response_hint", ""),
            expected_output=data.get("expected_output", {}),
            estimated_duration_seconds=data.get("estimated_duration_seconds", 10.0)
        )


# =============================================================================
# Level 3: 技能执行资源（执行时加载）
# =============================================================================

@dataclass
class SkillExecution:
    """
    Level 3: 技能执行资源
    
    设计原则：
    - 包含实际的工具实例
    - 包含执行上下文
    - 由DAG编排器或Agent执行器使用
    - 在实际执行时才加载
    
    Attributes:
        skill_id: 技能唯一标识
        tools: 工具实例映射（工具名 -> 工具实例）
        layer3_rules: 安全规则列表
        execution_context: 执行上下文
        user_profile: 用户档案
    
    Requirements: 8.1
    """
    skill_id: str
    tools: Dict[str, Any] = field(default_factory=dict)  # 工具名 -> 工具实例
    layer3_rules: List[Any] = field(default_factory=list)  # Layer3Rule列表
    execution_context: Dict[str, Any] = field(default_factory=dict)
    user_profile: Optional[Dict[str, Any]] = None
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """获取工具实例"""
        return self.tools.get(tool_name)
    
    def has_tool(self, tool_name: str) -> bool:
        """检查是否有指定工具"""
        return tool_name in self.tools
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self.tools.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含工具实例）"""
        return {
            "skill_id": self.skill_id,
            "available_tools": list(self.tools.keys()),
            "rules_count": len(self.layer3_rules),
            "has_user_profile": self.user_profile is not None
        }


# =============================================================================
# 完整技能定义（三层合一）
# =============================================================================

@dataclass
class Skill:
    """
    完整技能定义（三层合一）
    
    包含：
    - metadata: Level 1 元数据
    - content: Level 2 完整内容
    - execution: Level 3 执行资源（可选，执行时填充）
    
    Requirements: 8.1
    """
    metadata: SkillMetadata
    content: SkillContent
    execution: Optional[SkillExecution] = None
    
    @classmethod
    def from_dag_template(cls, template: 'DAGTemplateDefinition') -> 'Skill':
        """
        从现有DAG模板转换为Skill
        
        这是Skills架构的核心转换方法，将现有的13个DAG模板
        转换为Skills格式，实现渐进式披露。
        
        Args:
            template: DAG模板定义
        
        Returns:
            Skill: 转换后的技能
        
        Requirements: 8.1
        """
        # 映射类别
        category_map = {
            "training": SkillCategory.TRAINING,
            "nutrition": SkillCategory.NUTRITION,
            "safety": SkillCategory.SAFETY,
            "comprehensive": SkillCategory.COMPREHENSIVE,
            "quick": SkillCategory.QUICK,
        }
        
        # 获取模板属性（支持dataclass和dict两种格式）
        if hasattr(template, 'template_id'):
            template_id = template.template_id
            name = template.name
            description = template.description
            category_str = template.category
            applicable_intents = template.applicable_intents
            required_tools = template.required_tools
            optional_tools = template.optional_tools
            tool_dependencies = template.tool_dependencies
            parallel_groups = template.parallel_groups
            safety_constraints = template.safety_constraints
            response_hint = template.response_hint
            expected_output = template.expected_output
            estimated_duration = template.estimated_duration_seconds
            complexity_level = template.complexity_level
        else:
            # dict格式
            template_id = template.get('template_id', '')
            name = template.get('name', '')
            description = template.get('description', '')
            category_str = template.get('category', 'custom')
            applicable_intents = template.get('applicable_intents', [])
            required_tools = template.get('required_tools', [])
            optional_tools = template.get('optional_tools', [])
            tool_dependencies = template.get('tool_dependencies', {})
            parallel_groups = template.get('parallel_groups', [])
            safety_constraints = template.get('safety_constraints', [])
            response_hint = template.get('response_hint', '')
            expected_output = template.get('expected_output', {})
            estimated_duration = template.get('estimated_duration_seconds', 10.0)
            complexity_level = template.get('complexity_level', 1)
        
        # 获取类别
        category = category_map.get(category_str, SkillCategory.CUSTOM)
        
        # 截断描述为50字以内（Level 1元数据要求）
        short_description = description[:50] if len(description) > 50 else description
        if len(description) > 50:
            short_description = short_description[:47] + "..."
        
        # 创建Level 1: 元数据
        metadata = SkillMetadata(
            skill_id=template_id,
            name=name,
            description=short_description,
            category=category,
            keywords=applicable_intents[:5],  # 取前5个关键词
            complexity_level=complexity_level,
            estimated_tokens=50  # 元数据约50 tokens
        )
        
        # 创建Level 2: 完整内容
        content = SkillContent(
            skill_id=template_id,
            full_description=description,
            applicable_intents=applicable_intents,
            required_tools=required_tools,
            optional_tools=optional_tools,
            tool_dependencies=tool_dependencies,
            parallel_groups=parallel_groups,
            safety_constraints=safety_constraints,
            response_hint=response_hint,
            expected_output=expected_output,
            estimated_duration_seconds=estimated_duration
        )
        
        logger.debug(f"从DAG模板创建Skill: {template_id}")
        
        return cls(metadata=metadata, content=content)
    
    def get_skill_id(self) -> str:
        """获取技能ID"""
        return self.metadata.skill_id
    
    def get_name(self) -> str:
        """获取技能名称"""
        return self.metadata.name
    
    def get_category(self) -> SkillCategory:
        """获取技能类别"""
        return self.metadata.category
    
    def get_required_tools(self) -> List[str]:
        """获取必需工具列表"""
        return self.content.required_tools
    
    def get_all_tools(self) -> List[str]:
        """获取所有工具列表（必需+可选）"""
        return self.content.required_tools + self.content.optional_tools
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "metadata": self.metadata.to_dict(),
            "content": self.content.to_dict()
        }
        if self.execution:
            result["execution"] = self.execution.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Skill':
        """从字典创建"""
        metadata = SkillMetadata.from_dict(data["metadata"])
        content = SkillContent.from_dict(data["content"])
        return cls(metadata=metadata, content=content)
