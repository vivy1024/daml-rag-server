# -*- coding: utf-8 -*-
"""
load_skill MCP工具

这是Skills架构的核心工具，供LLM按需加载技能内容。

使用场景：
1. LLM看到system prompt中的技能列表（Level 1）
2. LLM决定需要某个技能
3. LLM调用 load_skill(skill_id) 获取完整指令（Level 2）
4. LLM根据指令执行技能

Requirements: 8.2

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .skill_manager import SkillManager

logger = logging.getLogger(__name__)


# =============================================================================
# 输入Schema
# =============================================================================

class LoadSkillInput(BaseModel):
    """
    load_skill工具输入Schema
    
    Attributes:
        skill_id: 要加载的技能ID
    """
    skill_id: str = Field(
        ...,
        description="要加载的技能ID，如 'complete_training_plan', 'nutrition_planning' 等"
    )


class LoadSkillOutput(BaseModel):
    """
    load_skill工具输出Schema
    
    Attributes:
        success: 是否成功
        skill_id: 技能ID
        content: 技能内容（SKILL.md格式）
        error: 错误信息（如果失败）
    """
    success: bool = Field(..., description="是否成功加载")
    skill_id: str = Field(..., description="技能ID")
    content: Optional[str] = Field(None, description="技能内容（SKILL.md格式）")
    error: Optional[str] = Field(None, description="错误信息")


# =============================================================================
# load_skill MCP工具
# =============================================================================

class LoadSkillTool:
    """
    load_skill MCP工具
    
    这是Skills架构的核心工具，供LLM按需加载技能内容。
    
    使用场景：
    1. LLM看到system prompt中的技能列表（Level 1）
    2. LLM决定需要某个技能
    3. LLM调用 load_skill(skill_id) 获取完整指令（Level 2）
    4. LLM根据指令执行技能
    
    使用示例:
    ```python
    from src.framework.skills import SkillManager, LoadSkillTool
    
    # 创建管理器和工具
    manager = SkillManager()
    manager.register_from_dag_templates(templates)
    
    tool = LoadSkillTool(manager)
    
    # 执行工具
    result = await tool.execute({"skill_id": "complete_training_plan"})
    print(result["content"])
    ```
    
    Requirements: 8.2
    """
    
    # 工具元数据
    TOOL_NAME = "load_skill"
    TOOL_DESCRIPTION = "加载技能的完整指令。在执行任何技能前，必须先调用此工具获取详细指令。"
    TOOL_CATEGORY = "skills"
    TOOL_PRIORITY = "P0"
    
    def __init__(self, skill_manager: 'SkillManager'):
        """
        初始化load_skill工具
        
        Args:
            skill_manager: 技能管理器实例
        """
        self.skill_manager = skill_manager
        self._call_count = 0
        
        logger.info(f"✅ LoadSkillTool初始化完成: {self.skill_manager.get_skill_count()}个技能可用")
    
    def get_name(self) -> str:
        """返回工具名称"""
        return self.TOOL_NAME
    
    def get_description(self) -> str:
        """返回工具描述"""
        return self.TOOL_DESCRIPTION
    
    def get_category(self) -> str:
        """返回工具类别"""
        return self.TOOL_CATEGORY
    
    def get_priority(self) -> str:
        """返回工具优先级"""
        return self.TOOL_PRIORITY
    
    def get_input_schema(self) -> type[BaseModel]:
        """返回输入Schema（Pydantic模型类）"""
        return LoadSkillInput
    
    def get_output_schema(self) -> type[BaseModel]:
        """返回输出Schema（Pydantic模型类）"""
        return LoadSkillOutput
    
    def get_schema_dict(self) -> Dict[str, Any]:
        """
        返回工具Schema字典（用于MCP注册）
        
        Returns:
            Dict: 工具Schema
        """
        return {
            "name": self.TOOL_NAME,
            "description": self.TOOL_DESCRIPTION,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": "要加载的技能ID，如 'complete_training_plan', 'nutrition_planning' 等"
                    }
                },
                "required": ["skill_id"]
            }
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行load_skill工具
        
        Args:
            input_data: 输入数据，包含skill_id
        
        Returns:
            Dict: 执行结果
        
        Requirements: 8.2
        """
        self._call_count += 1
        
        # 获取skill_id
        skill_id = input_data.get("skill_id")
        
        if not skill_id:
            logger.warning("⚠️ load_skill调用缺少skill_id参数")
            return {
                "success": False,
                "skill_id": "",
                "content": None,
                "error": "缺少skill_id参数"
            }
        
        # 加载技能内容
        content = self.skill_manager.load_skill(skill_id)
        
        # 检查是否是错误信息
        if content.startswith("错误"):
            logger.warning(f"⚠️ load_skill失败: {content}")
            return {
                "success": False,
                "skill_id": skill_id,
                "content": None,
                "error": content
            }
        
        logger.info(f"✅ load_skill成功: {skill_id} (第{self._call_count}次调用)")
        
        return {
            "success": True,
            "skill_id": skill_id,
            "content": content,
            "error": None
        }
    
    def execute_sync(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        同步执行load_skill工具
        
        Args:
            input_data: 输入数据，包含skill_id
        
        Returns:
            Dict: 执行结果
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.execute(input_data))
    
    def get_available_skills(self) -> list[str]:
        """
        获取可用技能列表
        
        Returns:
            List[str]: 技能ID列表
        """
        return self.skill_manager.list_skills()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取工具统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            "tool_name": self.TOOL_NAME,
            "call_count": self._call_count,
            "available_skills": len(self.skill_manager.list_skills()),
            "loaded_skills": len(self.skill_manager.get_loaded_skills()),
            "skill_manager_stats": self.skill_manager.get_statistics()
        }


# =============================================================================
# MCP工具注册辅助函数
# =============================================================================

def create_load_skill_tool(skill_manager: 'SkillManager') -> LoadSkillTool:
    """
    创建load_skill工具实例
    
    Args:
        skill_manager: 技能管理器实例
    
    Returns:
        LoadSkillTool: 工具实例
    """
    return LoadSkillTool(skill_manager)


def get_load_skill_schema() -> Dict[str, Any]:
    """
    获取load_skill工具的MCP Schema
    
    用于注册到MCP工具列表。
    
    Returns:
        Dict: MCP工具Schema
    """
    return {
        "name": LoadSkillTool.TOOL_NAME,
        "description": LoadSkillTool.TOOL_DESCRIPTION,
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "要加载的技能ID"
                }
            },
            "required": ["skill_id"]
        }
    }


def register_load_skill_to_mcp_registry(
    registry: Dict[str, Any],
    skill_manager: 'SkillManager'
) -> LoadSkillTool:
    """
    将load_skill工具注册到MCP注册表
    
    Args:
        registry: MCP工具注册表
        skill_manager: 技能管理器实例
    
    Returns:
        LoadSkillTool: 创建的工具实例
    """
    tool = LoadSkillTool(skill_manager)
    
    # 添加到注册表
    if "python_tools" not in registry:
        registry["python_tools"] = {"tools": []}
    
    registry["python_tools"]["tools"].append({
        "name": tool.get_name(),
        "description": tool.get_description(),
        "category": tool.get_category(),
        "priority": tool.get_priority()
    })
    
    logger.info(f"✅ load_skill工具已注册到MCP注册表")
    
    return tool
