# -*- coding: utf-8 -*-
"""
策略选择器 - 双策略架构核心组件（简化版）

基于会员权限和技能匹配选择DAG或Agent模式。
移除了复杂度分类器（用户反馈没有意义），改为简单的会员权限控制。

核心功能：
1. 技能匹配（通过SkillManager）
2. 会员权限检查
3. 策略自动选择
4. 支持手动指定策略

设计原则：
- 简单优先：移除复杂度分类器，直接基于会员权限选择
- 技能驱动：通过SkillManager匹配技能，而非复杂度评估
- 权限控制：FREE/WARMHEART只能用DAG，ENERGY可用Agent

Requirements: 8.5, 8.6

版本: v3.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from src.framework.adapters.domain_adapter import DAGTemplateDefinition
    from src.framework.auth.membership_controller import MembershipController, MembershipLevel
    from src.framework.skills.skill_manager import SkillManager

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举定义
# =============================================================================

class ExecutionStrategy(Enum):
    """执行策略枚举"""
    DAG = "dag"      # DAG模式：预定义模板，程序控制
    AGENT = "agent"  # Agent模式：LLM自主决策（基于Skills）


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class StrategyDecision:
    """
    策略决策结果
    
    Attributes:
        strategy: 选择的执行策略
        reasoning: 决策推理过程
        skill_id: 匹配的技能ID（DAG模式时使用）
        template_id: DAG模式时的模板ID（兼容旧代码）
        confidence: 决策置信度 (0-1)
        metadata: 额外元数据
        membership_restricted: 是否因会员权限限制而降级
        original_strategy: 原本应该使用的策略（如果被降级）
    """
    strategy: ExecutionStrategy
    reasoning: str
    skill_id: Optional[str] = None
    template_id: Optional[str] = None  # 兼容旧代码，等于skill_id
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    membership_restricted: bool = False
    original_strategy: Optional[ExecutionStrategy] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "strategy": self.strategy.value,
            "reasoning": self.reasoning,
            "skill_id": self.skill_id,
            "template_id": self.template_id,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "membership_restricted": self.membership_restricted,
        }
        if self.original_strategy:
            result["original_strategy"] = self.original_strategy.value
        return result


# =============================================================================
# 简单查询检测器（保留，用于快速过滤）
# =============================================================================

class SimpleQueryDetector:
    """
    简单查询检测器
    
    用于快速识别问候、确认等简单查询，直接使用DAG模式。
    """
    
    # 简单查询关键词（精确匹配）
    SIMPLE_KEYWORDS = [
        "你好", "谢谢", "再见", "好的", "明白",
        "嗯", "哦", "是的", "不是", "可以"
    ]
    
    def is_simple_query(self, query: str) -> bool:
        """
        检查是否是简单查询
        
        Args:
            query: 用户查询
        
        Returns:
            是否是简单查询
        """
        query_stripped = query.strip()
        
        # 检查简单关键词（精确匹配）
        for kw in self.SIMPLE_KEYWORDS:
            if query_stripped == kw or query_stripped.startswith(kw + "，") or query_stripped.startswith(kw + "。"):
                return True
        
        # 非常短的查询（少于6个字符）
        if len(query_stripped) < 6:
            return True
        
        return False


# =============================================================================
# 策略选择器（简化版）
# =============================================================================

class StrategySelector:
    """
    策略选择器（简化版）
    
    基于会员权限和技能匹配选择DAG或Agent模式。
    移除了复杂度分类器（用户反馈没有意义），改为简单的会员权限控制。
    
    核心特性：
    1. 技能匹配：通过SkillManager匹配技能
    2. 会员权限：FREE/WARMHEART只能用DAG，ENERGY可用Agent
    3. 简单优先：默认使用DAG模式
    4. 支持手动指定策略
    
    使用示例:
    ```python
    from src.framework.orchestration.strategy_selector import StrategySelector
    from src.framework.skills import SkillManager
    
    # 创建选择器
    skill_manager = SkillManager()
    selector = StrategySelector(
        skill_manager=skill_manager,
        default_strategy=ExecutionStrategy.DAG
    )
    
    # 选择策略
    decision = await selector.select_strategy(
        query="帮我制定一个增肌训练计划",
        user_profile={"goal": "增肌"},
        membership_level="warmheart"
    )
    
    print(f"策略: {decision.strategy.value}")
    print(f"技能: {decision.skill_id}")
    ```
    
    Requirements: 8.5, 8.6
    """
    
    def __init__(
        self,
        skill_manager: Optional['SkillManager'] = None,
        dag_templates: Optional[Dict[str, 'DAGTemplateDefinition']] = None,
        default_strategy: ExecutionStrategy = ExecutionStrategy.DAG,
        membership_controller: Optional['MembershipController'] = None
    ):
        """
        初始化策略选择器
        
        Args:
            skill_manager: 技能管理器（推荐使用）
            dag_templates: DAG模板字典（兼容旧代码）
            default_strategy: 默认策略
            membership_controller: 会员权限控制器（可选）
        
        Requirements: 8.5, 8.6
        """
        self.skill_manager = skill_manager
        self.dag_templates = dag_templates or {}
        self.default_strategy = default_strategy
        self.membership_controller = membership_controller
        self.simple_query_detector = SimpleQueryDetector()
        
        # 统计信息
        self._selection_count = 0
        self._dag_count = 0
        self._agent_count = 0
        self._skill_match_count = 0
        self._membership_restricted_count = 0
        
        logger.info(
            f"✅ StrategySelector初始化完成（简化版）: "
            f"技能管理器={'已集成' if skill_manager else '未集成'}, "
            f"DAG模板={len(self.dag_templates)}个, "
            f"默认策略: {default_strategy.value}, "
            f"会员控制: {'已集成' if membership_controller else '未集成'}"
        )
    
    async def select_strategy(
        self,
        query: str,
        user_profile: Dict[str, Any],
        force_strategy: Optional[ExecutionStrategy] = None,
        context: Optional[Dict[str, Any]] = None,
        membership_level: Optional[str] = None
    ) -> StrategyDecision:
        """
        选择执行策略（简化版）
        
        决策逻辑（简化）：
        1. 如果强制指定策略，检查会员权限后使用
        2. 检查是否是简单查询（问候等）
        3. 尝试匹配技能（通过SkillManager）
        4. 如果匹配成功，使用DAG模式
        5. 如果匹配失败且用户是ENERGY会员，可选择Agent模式
        6. 默认使用DAG模式
        
        Args:
            query: 用户查询
            user_profile: 用户档案
            force_strategy: 强制使用的策略
            context: 额外上下文
            membership_level: 会员等级（free/warmheart/energy）
        
        Returns:
            StrategyDecision: 策略决策结果
        
        Requirements: 8.5, 8.6
        """
        self._selection_count += 1
        
        logger.info(f"🎯 策略选择 #{self._selection_count}")
        logger.info(f"   查询: {query[:50]}...")
        if membership_level:
            logger.info(f"   会员等级: {membership_level}")
        
        # 1. 强制策略（需要检查会员权限）
        if force_strategy:
            # 检查会员权限
            decision = self._check_membership_permission(
                force_strategy, membership_level
            )
            if decision:
                return decision
            
            logger.info(f"   📌 强制策略: {force_strategy.value}")
            if force_strategy == ExecutionStrategy.DAG:
                self._dag_count += 1
            else:
                self._agent_count += 1
            
            return StrategyDecision(
                strategy=force_strategy,
                reasoning=f"用户强制指定策略: {force_strategy.value}",
                confidence=1.0,
                metadata={"forced": True}
            )
        
        # 2. 检查简单查询
        if self.simple_query_detector.is_simple_query(query):
            logger.info(f"   📝 简单查询，使用DAG模式")
            self._dag_count += 1
            return StrategyDecision(
                strategy=ExecutionStrategy.DAG,
                reasoning="简单查询（问候/确认等），使用DAG模式",
                skill_id="greeting",
                template_id="greeting",
                confidence=0.95,
                metadata={"simple_query": True}
            )
        
        # 3. 尝试匹配技能（通过SkillManager）
        matched_skill_id = None
        if self.skill_manager:
            matched_skill_id = self.skill_manager.match_skill_by_query(query)
        
        if matched_skill_id:
            logger.info(f"   📋 匹配到技能: {matched_skill_id}")
            self._dag_count += 1
            self._skill_match_count += 1
            
            # 获取技能元数据
            skill_metadata = self.skill_manager.get_skill_metadata(matched_skill_id)
            skill_name = skill_metadata.name if skill_metadata else matched_skill_id
            
            return StrategyDecision(
                strategy=ExecutionStrategy.DAG,
                reasoning=f"匹配到技能: {skill_name}",
                skill_id=matched_skill_id,
                template_id=matched_skill_id,  # 兼容旧代码
                confidence=0.85,
                metadata={"matched_skill": matched_skill_id}
            )
        
        # 4. 尝试匹配DAG模板（兼容旧代码）
        if not self.skill_manager and self.dag_templates:
            matched_template = self._match_template(query, user_profile)
            if matched_template:
                logger.info(f"   📋 匹配到模板: {matched_template.get('template_id', 'unknown')}")
                self._dag_count += 1
                return StrategyDecision(
                    strategy=ExecutionStrategy.DAG,
                    reasoning=f"匹配到DAG模板: {matched_template.get('name', 'unknown')}",
                    template_id=matched_template.get('template_id'),
                    skill_id=matched_template.get('template_id'),
                    confidence=matched_template.get('match_score', 0.8),
                    metadata={"matched_template": matched_template}
                )
        
        # 5. 检查是否可以使用Agent模式（仅ENERGY会员）
        if self._can_use_agent(membership_level):
            # ENERGY会员可以选择Agent模式处理未匹配的复杂查询
            logger.info(f"   🤖 未匹配技能，ENERGY会员可使用Agent模式")
            self._agent_count += 1
            return StrategyDecision(
                strategy=ExecutionStrategy.AGENT,
                reasoning="未匹配到技能，使用Agent模式（ENERGY会员）",
                confidence=0.7,
                metadata={"fallback_to_agent": True}
            )
        
        # 6. 默认使用DAG模式（通用对话技能）
        logger.info(f"   📋 使用DAG模式（默认）")
        self._dag_count += 1
        return StrategyDecision(
            strategy=ExecutionStrategy.DAG,
            reasoning="使用默认DAG模式",
            skill_id="general_consultation",
            template_id="general_consultation",
            confidence=0.6,
            metadata={"default_fallback": True}
        )

    def _can_use_agent(self, membership_level: Optional[str]) -> bool:
        """
        检查是否可以使用Agent模式
        
        只有ENERGY会员可以使用Agent模式
        
        Args:
            membership_level: 会员等级
        
        Returns:
            bool: 是否可以使用Agent模式
        """
        # 如果没有会员控制器，检查Feature Flag
        if not self.membership_controller:
            return False
        
        # 如果会员控制已禁用，所有用户都可以使用Agent
        if not self.membership_controller.is_membership_control_enabled():
            return True
        
        # 只有ENERGY会员可以使用Agent
        return membership_level and membership_level.lower() == "energy"
    
    def _check_membership_permission(
        self,
        requested_strategy: ExecutionStrategy,
        membership_level: Optional[str]
    ) -> Optional[StrategyDecision]:
        """
        检查会员权限是否允许使用指定策略
        
        Args:
            requested_strategy: 请求的策略
            membership_level: 会员等级（free/warmheart/energy）
        
        Returns:
            如果权限不足，返回降级决策；否则返回None
        
        Requirements: 8.6
        """
        # 如果没有会员控制器，不做限制
        if not self.membership_controller:
            return None
        
        # 如果会员控制已禁用，不做限制
        if not self.membership_controller.is_membership_control_enabled():
            return None
        
        # DAG模式所有用户都可以使用
        if requested_strategy == ExecutionStrategy.DAG:
            return None
        
        # Agent模式需要检查权限
        if requested_strategy == ExecutionStrategy.AGENT:
            # 获取会员等级
            from ..auth.membership_controller import (
                get_membership_level_from_string,
                ExecutionStrategy as MembershipStrategy
            )
            
            level = get_membership_level_from_string(membership_level or "free")
            
            # 检查是否可以使用Agent策略
            result = self.membership_controller.can_use_strategy(
                level, 
                MembershipStrategy.AGENT
            )
            
            if not result.allowed:
                # 权限不足，降级到DAG模式
                self._membership_restricted_count += 1
                self._dag_count += 1
                
                logger.info(
                    f"   ⚠️ 会员权限限制: {result.reason}, "
                    f"降级到DAG模式"
                )
                
                return StrategyDecision(
                    strategy=ExecutionStrategy.DAG,
                    reasoning=f"会员权限限制: {result.reason}",
                    confidence=0.8,
                    membership_restricted=True,
                    original_strategy=ExecutionStrategy.AGENT,
                    metadata={
                        "membership_level": membership_level or "free",
                        "upgrade_hint": result.upgrade_hint
                    }
                )
        
        return None
    
    def _match_template(
        self,
        query: str,
        user_profile: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        匹配DAG模板（兼容旧代码）
        
        Args:
            query: 用户查询
            user_profile: 用户档案
        
        Returns:
            匹配的模板信息或None
        """
        query_lower = query.lower()
        best_match = None
        best_score = 0.0
        
        for template_id, template in self.dag_templates.items():
            # 获取适用意图列表
            intents = []
            if hasattr(template, 'applicable_intents'):
                intents = template.applicable_intents
            elif isinstance(template, dict):
                intents = template.get('applicable_intents', [])
            
            # 计算匹配分数
            match_score = 0.0
            matched_intent = None
            
            for intent in intents:
                intent_lower = intent.lower()
                
                # 完全包含
                if intent_lower in query_lower:
                    score = len(intent_lower) / len(query_lower) * 0.8 + 0.2
                    if score > match_score:
                        match_score = score
                        matched_intent = intent
                
                # 部分匹配（关键词）
                elif any(kw in query_lower for kw in intent_lower.split()):
                    score = 0.5
                    if score > match_score:
                        match_score = score
                        matched_intent = intent
            
            if match_score > best_score:
                best_score = match_score
                best_match = {
                    "template_id": template_id,
                    "name": getattr(template, 'name', template_id) if hasattr(template, 'name') else template.get('name', template_id),
                    "match_score": match_score,
                    "matched_intent": matched_intent
                }
        
        # 只返回分数足够高的匹配
        if best_match and best_score >= 0.3:
            return best_match
        
        return None

    # =========================================================================
    # 技能/模板管理方法
    # =========================================================================
    
    def set_skill_manager(self, skill_manager: 'SkillManager') -> None:
        """
        设置技能管理器
        
        Args:
            skill_manager: 技能管理器实例
        """
        self.skill_manager = skill_manager
        logger.info(f"📋 技能管理器已设置: {skill_manager.get_skill_count()}个技能")
    
    def register_template(
        self,
        template_id: str,
        template: 'DAGTemplateDefinition'
    ) -> None:
        """
        注册DAG模板（兼容旧代码）
        
        Args:
            template_id: 模板ID
            template: 模板定义
        """
        self.dag_templates[template_id] = template
        logger.info(f"📋 注册模板: {template_id}")
    
    def unregister_template(self, template_id: str) -> bool:
        """
        注销DAG模板
        
        Args:
            template_id: 模板ID
        
        Returns:
            是否成功注销
        """
        if template_id in self.dag_templates:
            del self.dag_templates[template_id]
            logger.info(f"📋 注销模板: {template_id}")
            return True
        return False
    
    def get_template(self, template_id: str) -> Optional['DAGTemplateDefinition']:
        """
        获取DAG模板
        
        Args:
            template_id: 模板ID
        
        Returns:
            模板定义或None
        """
        return self.dag_templates.get(template_id)
    
    def list_templates(self) -> List[str]:
        """
        列出所有模板ID
        
        Returns:
            模板ID列表
        """
        return list(self.dag_templates.keys())

    # =========================================================================
    # 统计信息方法
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取策略选择统计信息
        
        Returns:
            统计信息字典
        """
        total = self._selection_count
        dag_ratio = self._dag_count / total if total > 0 else 0
        agent_ratio = self._agent_count / total if total > 0 else 0
        skill_match_ratio = self._skill_match_count / total if total > 0 else 0
        membership_restricted_ratio = self._membership_restricted_count / total if total > 0 else 0
        
        return {
            "total_selections": total,
            "dag_count": self._dag_count,
            "agent_count": self._agent_count,
            "skill_match_count": self._skill_match_count,
            "membership_restricted_count": self._membership_restricted_count,
            "dag_ratio": round(dag_ratio, 4),
            "agent_ratio": round(agent_ratio, 4),
            "skill_match_ratio": round(skill_match_ratio, 4),
            "membership_restricted_ratio": round(membership_restricted_ratio, 4),
            "skills_registered": self.skill_manager.get_skill_count() if self.skill_manager else 0,
            "templates_registered": len(self.dag_templates),
            "default_strategy": self.default_strategy.value,
            "membership_controller_enabled": (
                self.membership_controller is not None and 
                self.membership_controller.is_membership_control_enabled()
            )
        }
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._selection_count = 0
        self._dag_count = 0
        self._agent_count = 0
        self._skill_match_count = 0
        self._membership_restricted_count = 0
        logger.info("📊 统计信息已重置")
    
    # =========================================================================
    # 配置方法
    # =========================================================================
    
    def set_default_strategy(self, strategy: ExecutionStrategy) -> None:
        """
        设置默认策略
        
        Args:
            strategy: 默认策略
        """
        self.default_strategy = strategy
        logger.info(f"📌 默认策略设置为: {strategy.value}")
    
    def set_membership_controller(
        self,
        controller: Optional['MembershipController']
    ) -> None:
        """
        设置会员权限控制器
        
        Args:
            controller: 会员权限控制器实例
        
        Requirements: 8.6
        """
        self.membership_controller = controller
        if controller:
            enabled = controller.is_membership_control_enabled()
            logger.info(
                f"🔐 会员控制器已设置: "
                f"{'启用' if enabled else '禁用（所有用户享有energy权限）'}"
            )
        else:
            logger.info("🔐 会员控制器已移除")


# =============================================================================
# 工厂函数
# =============================================================================

def create_strategy_selector(
    skill_manager: Optional['SkillManager'] = None,
    dag_templates: Optional[Dict[str, 'DAGTemplateDefinition']] = None,
    default_strategy: ExecutionStrategy = ExecutionStrategy.DAG,
    membership_controller: Optional['MembershipController'] = None
) -> StrategySelector:
    """
    创建策略选择器实例
    
    Args:
        skill_manager: 技能管理器（推荐使用）
        dag_templates: DAG模板字典（兼容旧代码）
        default_strategy: 默认策略
        membership_controller: 会员权限控制器（可选）
    
    Returns:
        StrategySelector: 策略选择器实例
    
    Requirements: 8.5, 8.6
    """
    return StrategySelector(
        skill_manager=skill_manager,
        dag_templates=dag_templates,
        default_strategy=default_strategy,
        membership_controller=membership_controller
    )
