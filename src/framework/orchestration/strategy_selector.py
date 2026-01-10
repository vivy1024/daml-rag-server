# -*- coding: utf-8 -*-
"""
策略选择器 - 双策略架构核心组件

根据查询复杂度自动选择DAG或Agent模式。

核心功能：
1. 查询复杂度评估
2. DAG模板匹配
3. 策略自动选择
4. 支持手动指定策略

Requirements: 8.5

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from src.framework.adapters.domain_adapter import DAGTemplateDefinition

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举定义
# =============================================================================

class ExecutionStrategy(Enum):
    """执行策略枚举"""
    DAG = "dag"      # DAG模式：预定义模板，程序控制
    AGENT = "agent"  # Agent模式：LLM自主决策


class QueryComplexity(Enum):
    """查询复杂度"""
    SIMPLE = "simple"        # 简单查询，使用DAG
    MODERATE = "moderate"    # 中等复杂度，使用DAG
    COMPLEX = "complex"      # 复杂查询，使用Agent


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class StrategyDecision:
    """
    策略决策结果
    
    Attributes:
        strategy: 选择的执行策略
        complexity: 查询复杂度
        reasoning: 决策推理过程
        template_id: DAG模式时的模板ID
        confidence: 决策置信度 (0-1)
        metadata: 额外元数据
    """
    strategy: ExecutionStrategy
    complexity: QueryComplexity
    reasoning: str
    template_id: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy": self.strategy.value,
            "complexity": self.complexity.value,
            "reasoning": self.reasoning,
            "template_id": self.template_id,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass
class ComplexityIndicators:
    """
    复杂度指标
    
    用于评估查询复杂度的各项指标
    """
    query_length: int = 0
    question_count: int = 0
    condition_count: int = 0
    entity_count: int = 0
    has_comparison: bool = False
    has_temporal: bool = False
    has_multi_step: bool = False
    has_personalization: bool = False
    
    def calculate_score(self) -> float:
        """
        计算复杂度分数 (0-1)
        
        Returns:
            复杂度分数
        """
        score = 0.0
        
        # 查询长度贡献（增强权重）
        if self.query_length > 80:
            score += 0.25
        elif self.query_length > 50:
            score += 0.15
        elif self.query_length > 30:
            score += 0.08
        
        # 问题数量贡献
        score += min(self.question_count * 0.12, 0.25)
        
        # 条件数量贡献
        score += min(self.condition_count * 0.1, 0.25)
        
        # 实体数量贡献
        score += min(self.entity_count * 0.08, 0.2)
        
        # 布尔指标贡献（增强权重）
        if self.has_comparison:
            score += 0.15
        if self.has_temporal:
            score += 0.12
        if self.has_multi_step:
            score += 0.25  # 多步骤是复杂查询的强信号
        if self.has_personalization:
            score += 0.08
        
        return min(score, 1.0)


# =============================================================================
# 复杂度分类器
# =============================================================================

class ComplexityClassifier:
    """
    查询复杂度分类器
    
    基于规则和关键词的复杂度评估
    """
    
    # 高复杂度关键词（权重高）
    HIGH_COMPLEX_KEYWORDS = [
        "综合", "全面", "详细", "完整", "系统",
        "分析", "评估", "权衡", "规划", "方案",
        "长期", "周期", "阶段", "进阶", "专业",
        "康复", "矫正", "调整", "优化", "改进"
    ]
    
    # 中等复杂度关键词
    MEDIUM_COMPLEX_KEYWORDS = [
        "对比", "比较", "区别", "差异",
        "为什么", "怎么样", "如何", "什么原因",
        "结合", "考虑", "根据", "基于", "针对",
        "多个", "几种", "各种", "所有", "全部"
    ]
    
    # 简单查询关键词（精确匹配）
    SIMPLE_KEYWORDS = [
        "你好", "谢谢", "再见", "好的", "明白",
        "嗯", "哦", "是的", "不是", "可以"
    ]
    
    # 简单查询模式（开头匹配）
    SIMPLE_PATTERNS = [
        "是什么", "有哪些", "推荐", "建议",
        "多少", "几个", "哪个"
    ]
    
    # 多步骤指示词
    MULTI_STEP_INDICATORS = [
        "首先", "然后", "接着", "最后", "第一", "第二",
        "先", "再", "之后", "同时", "另外", "此外",
        "包括", "以及", "还有", "并且"
    ]
    
    # 比较指示词
    COMPARISON_INDICATORS = [
        "比", "更", "最", "还是", "或者", "哪个更",
        "对比", "区别", "差异", "优缺点", "利弊"
    ]
    
    # 时间指示词
    TEMPORAL_INDICATORS = [
        "每天", "每周", "每月", "长期", "短期",
        "周期", "阶段", "持续", "多久", "什么时候"
    ]
    
    # 个性化指示词
    PERSONALIZATION_INDICATORS = [
        "我", "我的", "适合我", "针对我", "根据我",
        "我想", "我要", "我需要", "帮我", "给我"
    ]
    
    def __init__(self):
        """初始化分类器"""
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """编译正则表达式模式"""
        self._question_pattern = re.compile(r'[？?]')
        self._condition_pattern = re.compile(r'如果|假如|要是|当|若|除非')
        self._entity_pattern = re.compile(r'[\u4e00-\u9fa5]{2,4}(?:肌|动作|训练|计划|饮食|营养)')
    
    async def classify(self, query: str) -> float:
        """
        分类查询复杂度
        
        Args:
            query: 用户查询
        
        Returns:
            复杂度分数 (0-1)
        """
        indicators = self._extract_indicators(query)
        return indicators.calculate_score()
    
    def _extract_indicators(self, query: str) -> ComplexityIndicators:
        """
        提取复杂度指标
        
        Args:
            query: 用户查询
        
        Returns:
            ComplexityIndicators: 复杂度指标
        """
        indicators = ComplexityIndicators()
        
        # 查询长度
        indicators.query_length = len(query)
        
        # 问题数量
        indicators.question_count = len(self._question_pattern.findall(query))
        
        # 条件数量
        indicators.condition_count = len(self._condition_pattern.findall(query))
        
        # 实体数量
        indicators.entity_count = len(self._entity_pattern.findall(query))
        
        # 检查高复杂度关键词
        high_complex_count = sum(1 for kw in self.HIGH_COMPLEX_KEYWORDS if kw in query)
        if high_complex_count >= 2:
            indicators.has_multi_step = True
        
        # 检查中等复杂度关键词
        medium_complex_count = sum(1 for kw in self.MEDIUM_COMPLEX_KEYWORDS if kw in query)
        
        # 检查比较指示词
        indicators.has_comparison = any(ind in query for ind in self.COMPARISON_INDICATORS)
        
        # 检查时间指示词
        indicators.has_temporal = any(ind in query for ind in self.TEMPORAL_INDICATORS)
        
        # 检查多步骤指示词
        multi_step_count = sum(1 for ind in self.MULTI_STEP_INDICATORS if ind in query)
        if multi_step_count >= 2:
            indicators.has_multi_step = True
        
        # 检查个性化指示词
        indicators.has_personalization = any(ind in query for ind in self.PERSONALIZATION_INDICATORS)
        
        return indicators
    
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
# 策略选择器
# =============================================================================

class StrategySelector:
    """
    策略选择器
    
    根据查询复杂度自动选择DAG或Agent模式。
    
    核心特性：
    1. 查询复杂度评估
    2. DAG模板匹配
    3. 策略自动选择
    4. 支持手动指定策略
    
    使用示例:
    ```python
    from src.framework.orchestration.strategy_selector import StrategySelector
    
    # 创建选择器
    selector = StrategySelector(
        dag_templates=my_templates,
        default_strategy=ExecutionStrategy.DAG
    )
    
    # 选择策略
    decision = await selector.select_strategy(
        query="帮我制定一个增肌训练计划",
        user_profile={"goal": "增肌"}
    )
    
    print(f"策略: {decision.strategy.value}")
    print(f"模板: {decision.template_id}")
    ```
    
    Requirements: 8.5
    """
    
    # 复杂度阈值
    COMPLEXITY_THRESHOLD_HIGH = 0.5   # 高复杂度阈值（降低以更容易触发Agent）
    COMPLEXITY_THRESHOLD_MEDIUM = 0.3  # 中等复杂度阈值
    
    def __init__(
        self,
        dag_templates: Optional[Dict[str, 'DAGTemplateDefinition']] = None,
        complexity_classifier: Optional[ComplexityClassifier] = None,
        default_strategy: ExecutionStrategy = ExecutionStrategy.DAG,
        enable_auto_selection: bool = True
    ):
        """
        初始化策略选择器
        
        Args:
            dag_templates: DAG模板字典
            complexity_classifier: 复杂度分类器
            default_strategy: 默认策略
            enable_auto_selection: 是否启用自动选择
        
        Requirements: 8.5
        """
        self.dag_templates = dag_templates or {}
        self.complexity_classifier = complexity_classifier or ComplexityClassifier()
        self.default_strategy = default_strategy
        self.enable_auto_selection = enable_auto_selection
        
        # 统计信息
        self._selection_count = 0
        self._dag_count = 0
        self._agent_count = 0
        self._template_match_count = 0
        
        logger.info(
            f"✅ StrategySelector初始化完成: "
            f"{len(self.dag_templates)}个模板, "
            f"默认策略: {default_strategy.value}, "
            f"自动选择: {'启用' if enable_auto_selection else '禁用'}"
        )
    
    async def select_strategy(
        self,
        query: str,
        user_profile: Dict[str, Any],
        force_strategy: Optional[ExecutionStrategy] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> StrategyDecision:
        """
        选择执行策略
        
        决策逻辑：
        1. 如果强制指定策略，使用指定策略
        2. 检查是否是简单查询（问候等）
        3. 尝试匹配DAG模板
        4. 如果匹配成功，使用DAG模式
        5. 如果匹配失败，评估复杂度
        6. 复杂查询使用Agent模式
        
        Args:
            query: 用户查询
            user_profile: 用户档案
            force_strategy: 强制使用的策略
            context: 额外上下文
        
        Returns:
            StrategyDecision: 策略决策结果
        
        Requirements: 8.5
        """
        self._selection_count += 1
        
        logger.info(f"🎯 策略选择 #{self._selection_count}")
        logger.info(f"   查询: {query[:50]}...")
        
        # 1. 强制策略
        if force_strategy:
            logger.info(f"   📌 强制策略: {force_strategy.value}")
            if force_strategy == ExecutionStrategy.DAG:
                self._dag_count += 1
            else:
                self._agent_count += 1
            
            return StrategyDecision(
                strategy=force_strategy,
                complexity=QueryComplexity.MODERATE,
                reasoning=f"用户强制指定策略: {force_strategy.value}",
                confidence=1.0,
                metadata={"forced": True}
            )
        
        # 2. 检查简单查询
        if self.complexity_classifier.is_simple_query(query):
            logger.info(f"   📝 简单查询，使用DAG模式")
            self._dag_count += 1
            return StrategyDecision(
                strategy=ExecutionStrategy.DAG,
                complexity=QueryComplexity.SIMPLE,
                reasoning="简单查询（问候/确认等），使用DAG模式",
                confidence=0.95,
                metadata={"simple_query": True}
            )
        
        # 3. 尝试匹配DAG模板
        matched_template = self._match_template(query, user_profile)
        if matched_template:
            logger.info(f"   📋 匹配到模板: {matched_template.get('template_id', 'unknown')}")
            self._dag_count += 1
            self._template_match_count += 1
            return StrategyDecision(
                strategy=ExecutionStrategy.DAG,
                complexity=QueryComplexity.SIMPLE,
                reasoning=f"匹配到DAG模板: {matched_template.get('name', 'unknown')}",
                template_id=matched_template.get('template_id'),
                confidence=matched_template.get('match_score', 0.8),
                metadata={"matched_template": matched_template}
            )
        
        # 4. 如果禁用自动选择，使用默认策略
        if not self.enable_auto_selection:
            logger.info(f"   📌 自动选择禁用，使用默认策略: {self.default_strategy.value}")
            if self.default_strategy == ExecutionStrategy.DAG:
                self._dag_count += 1
            else:
                self._agent_count += 1
            return StrategyDecision(
                strategy=self.default_strategy,
                complexity=QueryComplexity.MODERATE,
                reasoning="自动选择禁用，使用默认策略",
                confidence=0.7
            )
        
        # 5. 评估复杂度
        complexity_score = await self.complexity_classifier.classify(query)
        complexity = self._score_to_complexity(complexity_score)
        
        logger.info(f"   📊 复杂度评分: {complexity_score:.2f} -> {complexity.value}")
        
        # 6. 根据复杂度选择策略
        if complexity == QueryComplexity.COMPLEX:
            logger.info(f"   🤖 复杂查询，使用Agent模式")
            self._agent_count += 1
            return StrategyDecision(
                strategy=ExecutionStrategy.AGENT,
                complexity=complexity,
                reasoning=f"查询复杂度高({complexity_score:.2f})，使用Agent模式",
                confidence=complexity_score,
                metadata={"complexity_score": complexity_score}
            )
        
        # 7. 默认使用DAG模式
        logger.info(f"   📋 使用DAG模式（默认）")
        self._dag_count += 1
        return StrategyDecision(
            strategy=ExecutionStrategy.DAG,
            complexity=complexity,
            reasoning=f"查询复杂度适中({complexity_score:.2f})，使用DAG模式",
            confidence=1.0 - complexity_score,
            metadata={"complexity_score": complexity_score}
        )
    
    def _match_template(
        self,
        query: str,
        user_profile: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        匹配DAG模板
        
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
    
    def _score_to_complexity(self, score: float) -> QueryComplexity:
        """
        将分数转换为复杂度等级
        
        Args:
            score: 复杂度分数 (0-1)
        
        Returns:
            QueryComplexity: 复杂度等级
        """
        if score >= self.COMPLEXITY_THRESHOLD_HIGH:
            return QueryComplexity.COMPLEX
        elif score >= self.COMPLEXITY_THRESHOLD_MEDIUM:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE

    # =========================================================================
    # 模板管理方法
    # =========================================================================
    
    def register_template(
        self,
        template_id: str,
        template: 'DAGTemplateDefinition'
    ) -> None:
        """
        注册DAG模板
        
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
        template_match_ratio = self._template_match_count / total if total > 0 else 0
        
        return {
            "total_selections": total,
            "dag_count": self._dag_count,
            "agent_count": self._agent_count,
            "template_match_count": self._template_match_count,
            "dag_ratio": round(dag_ratio, 4),
            "agent_ratio": round(agent_ratio, 4),
            "template_match_ratio": round(template_match_ratio, 4),
            "templates_registered": len(self.dag_templates),
            "default_strategy": self.default_strategy.value,
            "auto_selection_enabled": self.enable_auto_selection
        }
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._selection_count = 0
        self._dag_count = 0
        self._agent_count = 0
        self._template_match_count = 0
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
    
    def set_auto_selection(self, enabled: bool) -> None:
        """
        设置是否启用自动选择
        
        Args:
            enabled: 是否启用
        """
        self.enable_auto_selection = enabled
        logger.info(f"🔧 自动选择: {'启用' if enabled else '禁用'}")
    
    def set_complexity_thresholds(
        self,
        high: Optional[float] = None,
        medium: Optional[float] = None
    ) -> None:
        """
        设置复杂度阈值
        
        Args:
            high: 高复杂度阈值 (0-1)
            medium: 中等复杂度阈值 (0-1)
        """
        if high is not None:
            self.COMPLEXITY_THRESHOLD_HIGH = high
        if medium is not None:
            self.COMPLEXITY_THRESHOLD_MEDIUM = medium
        logger.info(
            f"📊 复杂度阈值: 高={self.COMPLEXITY_THRESHOLD_HIGH}, "
            f"中={self.COMPLEXITY_THRESHOLD_MEDIUM}"
        )


# =============================================================================
# 工厂函数
# =============================================================================

def create_strategy_selector(
    dag_templates: Optional[Dict[str, 'DAGTemplateDefinition']] = None,
    default_strategy: ExecutionStrategy = ExecutionStrategy.DAG,
    enable_auto_selection: bool = True
) -> StrategySelector:
    """
    创建策略选择器实例
    
    Args:
        dag_templates: DAG模板字典
        default_strategy: 默认策略
        enable_auto_selection: 是否启用自动选择
    
    Returns:
        StrategySelector: 策略选择器实例
    """
    return StrategySelector(
        dag_templates=dag_templates,
        default_strategy=default_strategy,
        enable_auto_selection=enable_auto_selection
    )
