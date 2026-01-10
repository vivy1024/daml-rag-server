# -*- coding: utf-8 -*-
"""
Skills架构集成模块

将Skills架构集成到主流程中，提供：
1. SkillManager初始化和配置
2. 与StrategySelector的集成
3. 与DAG编排器的集成
4. Feature Flag控制

Requirements: 8.5, 8.6

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import os
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from .skill_manager import SkillManager, create_skill_manager
from .skill_definition import Skill, SkillCategory

if TYPE_CHECKING:
    from ..orchestration.strategy_selector import StrategySelector, ExecutionStrategy
    from ..auth.membership_controller import MembershipController
    from ..adapters.domain_adapter import DomainAdapter

logger = logging.getLogger(__name__)


# =============================================================================
# Feature Flags
# =============================================================================

def is_skills_mode_enabled() -> bool:
    """
    检查是否启用Skills模式
    
    通过环境变量 USE_SKILLS_MODE 控制：
    - true/1/yes: 启用Skills模式（渐进式披露）
    - false/0/no（默认）: 使用传统DAG模式
    
    Returns:
        bool: 是否启用Skills模式
    """
    return os.getenv('USE_SKILLS_MODE', 'false').lower() in ('true', '1', 'yes')


def is_agent_mode_enabled() -> bool:
    """
    检查是否启用Agent模式
    
    通过环境变量 USE_AGENT_MODE 控制：
    - true/1/yes: 启用Agent模式（LLM自主决策）
    - false/0/no（默认）: 禁用Agent模式
    
    注意：Agent模式需要ENERGY会员权限
    
    Returns:
        bool: 是否启用Agent模式
    """
    return os.getenv('USE_AGENT_MODE', 'false').lower() in ('true', '1', 'yes')


# =============================================================================
# Skills架构集成器
# =============================================================================

class SkillsIntegration:
    """
    Skills架构集成器
    
    负责将Skills架构集成到主流程中：
    1. 初始化SkillManager
    2. 从DomainAdapter加载技能
    3. 配置StrategySelector
    4. 提供统一的技能访问接口
    
    使用示例:
    ```python
    from src.framework.skills import SkillsIntegration
    
    # 创建集成器
    integration = SkillsIntegration()
    
    # 从领域适配器初始化
    integration.initialize_from_adapter(fitness_adapter)
    
    # 获取技能管理器
    skill_manager = integration.get_skill_manager()
    
    # 获取system prompt中的技能列表
    skills_prompt = integration.get_skills_prompt()
    ```
    
    Requirements: 8.5, 8.6
    """
    
    _instance: Optional['SkillsIntegration'] = None
    
    def __init__(self):
        """初始化Skills集成器"""
        self._skill_manager: Optional[SkillManager] = None
        self._strategy_selector: Optional['StrategySelector'] = None
        self._membership_controller: Optional['MembershipController'] = None
        self._initialized = False
        
        # Feature Flags
        self._skills_mode_enabled = is_skills_mode_enabled()
        self._agent_mode_enabled = is_agent_mode_enabled()
        
        logger.info(
            f"✅ SkillsIntegration初始化: "
            f"Skills模式={'启用' if self._skills_mode_enabled else '禁用'}, "
            f"Agent模式={'启用' if self._agent_mode_enabled else '禁用'}"
        )
    
    @classmethod
    def get_instance(cls) -> 'SkillsIntegration':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（用于测试）"""
        cls._instance = None
    
    # =========================================================================
    # 初始化方法
    # =========================================================================
    
    def initialize_from_adapter(
        self,
        adapter: 'DomainAdapter',
        membership_controller: Optional['MembershipController'] = None
    ) -> None:
        """
        从领域适配器初始化Skills架构
        
        Args:
            adapter: 领域适配器
            membership_controller: 会员权限控制器（可选）
        
        Requirements: 8.5
        """
        logger.info(f"🔧 从领域适配器初始化Skills架构: {adapter.get_name()}")
        
        # 创建SkillManager
        self._skill_manager = create_skill_manager()
        
        # 从DAG模板注册技能
        dag_templates = adapter.get_dag_templates()
        if dag_templates:
            count = self._skill_manager.register_from_dag_templates(dag_templates)
            logger.info(f"📋 从DAG模板注册了 {count} 个技能")
        
        # 设置会员控制器
        self._membership_controller = membership_controller
        
        # 创建StrategySelector
        self._create_strategy_selector()
        
        self._initialized = True
        logger.info(f"✅ Skills架构初始化完成: {self._skill_manager.get_skill_count()} 个技能")
    
    def initialize_with_skill_manager(
        self,
        skill_manager: SkillManager,
        membership_controller: Optional['MembershipController'] = None
    ) -> None:
        """
        使用已有的SkillManager初始化
        
        Args:
            skill_manager: 技能管理器
            membership_controller: 会员权限控制器（可选）
        """
        self._skill_manager = skill_manager
        self._membership_controller = membership_controller
        self._create_strategy_selector()
        self._initialized = True
        logger.info(f"✅ Skills架构初始化完成（使用已有SkillManager）")
    
    def _create_strategy_selector(self) -> None:
        """创建StrategySelector"""
        from ..orchestration.strategy_selector import (
            StrategySelector,
            ExecutionStrategy,
            create_strategy_selector
        )
        
        self._strategy_selector = create_strategy_selector(
            skill_manager=self._skill_manager,
            membership_controller=self._membership_controller,
            default_strategy=ExecutionStrategy.DAG
        )
    
    # =========================================================================
    # 访问方法
    # =========================================================================
    
    def get_skill_manager(self) -> Optional[SkillManager]:
        """获取技能管理器"""
        return self._skill_manager
    
    def get_strategy_selector(self) -> Optional['StrategySelector']:
        """获取策略选择器"""
        return self._strategy_selector
    
    def get_membership_controller(self) -> Optional['MembershipController']:
        """获取会员权限控制器"""
        return self._membership_controller
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    # =========================================================================
    # 技能操作方法
    # =========================================================================
    
    def get_skills_prompt(self) -> str:
        """
        获取system prompt中的技能列表
        
        Returns:
            str: 技能列表字符串
        """
        if not self._skill_manager:
            return "## 可用技能\n暂无可用技能"
        return self._skill_manager.get_system_prompt_skills()
    
    def get_skills_prompt_compact(self) -> str:
        """
        获取紧凑格式的技能列表
        
        Returns:
            str: 紧凑格式的技能列表
        """
        if not self._skill_manager:
            return "可用技能: 无"
        return self._skill_manager.get_system_prompt_skills_compact()
    
    def load_skill(self, skill_id: str) -> str:
        """
        加载技能完整内容
        
        Args:
            skill_id: 技能ID
        
        Returns:
            str: SKILL.md格式的技能内容
        """
        if not self._skill_manager:
            return f"错误：Skills架构未初始化"
        return self._skill_manager.load_skill(skill_id)
    
    def match_skill(self, query: str) -> Optional[str]:
        """
        根据查询匹配技能
        
        Args:
            query: 用户查询
        
        Returns:
            str或None: 匹配的技能ID
        """
        if not self._skill_manager:
            return None
        return self._skill_manager.match_skill_by_query(query)
    
    # =========================================================================
    # 策略选择方法
    # =========================================================================
    
    async def select_strategy(
        self,
        query: str,
        user_profile: Dict[str, Any],
        membership_level: Optional[str] = None,
        force_strategy: Optional['ExecutionStrategy'] = None
    ) -> Dict[str, Any]:
        """
        选择执行策略
        
        Args:
            query: 用户查询
            user_profile: 用户档案
            membership_level: 会员等级
            force_strategy: 强制策略
        
        Returns:
            Dict: 策略决策结果
        """
        if not self._strategy_selector:
            return {
                "strategy": "dag",
                "reasoning": "Skills架构未初始化，使用默认DAG模式",
                "skill_id": None
            }
        
        decision = await self._strategy_selector.select_strategy(
            query=query,
            user_profile=user_profile,
            membership_level=membership_level,
            force_strategy=force_strategy
        )
        
        return decision.to_dict()
    
    # =========================================================================
    # Feature Flag方法
    # =========================================================================
    
    def is_skills_mode_enabled(self) -> bool:
        """检查是否启用Skills模式"""
        return self._skills_mode_enabled
    
    def is_agent_mode_enabled(self) -> bool:
        """检查是否启用Agent模式"""
        return self._agent_mode_enabled
    
    def set_skills_mode(self, enabled: bool) -> None:
        """设置Skills模式（运行时）"""
        self._skills_mode_enabled = enabled
        logger.info(f"📌 Skills模式设置为: {'启用' if enabled else '禁用'}")
    
    def set_agent_mode(self, enabled: bool) -> None:
        """设置Agent模式（运行时）"""
        self._agent_mode_enabled = enabled
        logger.info(f"📌 Agent模式设置为: {'启用' if enabled else '禁用'}")
    
    # =========================================================================
    # 统计信息
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {
            "initialized": self._initialized,
            "skills_mode_enabled": self._skills_mode_enabled,
            "agent_mode_enabled": self._agent_mode_enabled,
        }
        
        if self._skill_manager:
            stats["skill_manager"] = self._skill_manager.get_statistics()
        
        if self._strategy_selector:
            stats["strategy_selector"] = self._strategy_selector.get_statistics()
        
        return stats


# =============================================================================
# 工厂函数
# =============================================================================

def get_skills_integration() -> SkillsIntegration:
    """
    获取Skills集成器单例
    
    Returns:
        SkillsIntegration: 集成器实例
    """
    return SkillsIntegration.get_instance()


def initialize_skills_from_adapter(
    adapter: 'DomainAdapter',
    membership_controller: Optional['MembershipController'] = None
) -> SkillsIntegration:
    """
    从领域适配器初始化Skills架构
    
    Args:
        adapter: 领域适配器
        membership_controller: 会员权限控制器
    
    Returns:
        SkillsIntegration: 初始化后的集成器
    """
    integration = get_skills_integration()
    integration.initialize_from_adapter(adapter, membership_controller)
    return integration


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'SkillsIntegration',
    'get_skills_integration',
    'initialize_skills_from_adapter',
    'is_skills_mode_enabled',
    'is_agent_mode_enabled',
]
