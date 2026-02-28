# -*- coding: utf-8 -*-
"""
LLM决策引擎 - 智能DAG方案选择

基于三段式架构的核心组件：使用LLM智能选择最合适的DAG方案。
LLM从预定义的DAG模板库中选择，避免直接调用MCP工具，防止幻觉。

核心特性：
1. LLM智能意图理解
2. 从DAG模板库中选择最合适方案
3. 结构化输出验证
4. 降级策略（规则匹配）
5. 选择理由可追溯

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import logging
import json
import warnings
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .dag_template_system import DAGTemplate, DAGTemplateManager
from ...framework.clients.llm_client import call_deepseek, call_ollama, LLMConfig

logger = logging.getLogger(__name__)


class SelectionConfidence(Enum):
    """选择置信度"""
    HIGH = "high"       # >= 0.8
    MEDIUM = "medium"   # 0.5 - 0.8
    LOW = "low"         # < 0.5


@dataclass
class DAGSelectionRequest:
    """DAG选择请求"""
    user_query: str
    user_profile: Dict[str, Any]
    available_templates: List[DAGTemplate]
    session_context: Optional[Dict[str, Any]] = None
    few_shot_examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DAGSelectionResult:
    """DAG选择结果"""
    selected_template_id: str
    selection_reason: str
    expected_tools: List[str]
    confidence: float
    confidence_level: SelectionConfidence
    alternative_templates: List[str] = field(default_factory=list)
    llm_raw_response: Optional[str] = None
    fallback_used: bool = False
    matched_keywords: List[str] = field(default_factory=list)
    method: str = "llm"  # "llm" 或 "fallback"


class LLMDecisionEngine:
    """LLM决策引擎"""
    
    def __init__(self, template_manager: Optional[DAGTemplateManager] = None):
        """
        初始化LLM决策引擎
        
        Args:
            template_manager: DAG模板管理器（可选，默认创建新实例）
        """
        self.template_manager = template_manager or DAGTemplateManager()
        
        # 验证LLM配置
        LLMConfig.validate()
        
        # 统计信息
        self.selection_stats = {
            "total_selections": 0,
            "successful_selections": 0,
            "fallback_selections": 0,
            "by_template": {},
            "average_confidence": 0.0
        }
        
        logger.info("✅ LLM决策引擎初始化完成")
    
    async def select_dag_template(
        self,
        request: DAGSelectionRequest
    ) -> DAGSelectionResult:
        """
        智能选择最合适的DAG模板（v2: 统一LLM分类，不再使用关键词匹配）

        所有查询统一走LLM分类，避免关键词匹配导致的复合意图误判。
        LLM分类失败时 fallback 到 general_qa 模板。

        Args:
            request: DAG选择请求

        Returns:
            DAGSelectionResult: 选择结果
        """
        self.selection_stats["total_selections"] += 1

        try:
            logger.info(f"🤔 开始DAG模板选择: 用户查询='{request.user_query[:50]}...'")

            # 统一走LLM分类
            prompt = self._build_selection_prompt(request)
            llm_response = await self._call_llm(prompt, request)
            selection_result = self._parse_llm_response(
                llm_response,
                request.available_templates
            )

            # 验证选择结果
            if not self._validate_selection(selection_result, request.available_templates):
                logger.warning("⚠️ LLM选择验证失败，fallback到quick_consultation")
                return DAGSelectionResult(
                    selected_template_id="quick_consultation",
                    selection_reason="LLM分类验证失败，使用通用问答模板",
                    expected_tools=[],
                    confidence=0.5,
                    confidence_level=SelectionConfidence.MEDIUM,
                    fallback_used=True,
                    method="fallback",
                )

            # 更新统计
            self.selection_stats["successful_selections"] += 1
            template_id = selection_result.selected_template_id
            self.selection_stats["by_template"][template_id] = \
                self.selection_stats["by_template"].get(template_id, 0) + 1

            total = self.selection_stats["successful_selections"]
            avg = self.selection_stats["average_confidence"]
            self.selection_stats["average_confidence"] = \
                (avg * (total - 1) + selection_result.confidence) / total

            logger.info(
                f"✅ LLM分类完成: {selection_result.selected_template_id} "
                f"(置信度: {selection_result.confidence:.2f})"
            )
            logger.info(f"   选择理由: {selection_result.selection_reason}")
            if selection_result.alternative_templates:
                logger.info(f"   备选模板: {', '.join(selection_result.alternative_templates)}")

            return selection_result

        except Exception as e:
            logger.error(f"❌ DAG模板选择失败: {e}", exc_info=True)
            return DAGSelectionResult(
                selected_template_id="quick_consultation",
                selection_reason=f"LLM分类异常({str(e)[:50]})，使用通用问答模板",
                expected_tools=[],
                confidence=0.5,
                confidence_level=SelectionConfidence.MEDIUM,
                fallback_used=True,
                method="fallback",
            )
    
    def _build_selection_prompt(self, request: DAGSelectionRequest) -> str:
        """构建LLM选择提示词"""
        
        # 提取用户档案关键信息
        user_profile = request.user_profile
        basic_info = user_profile.get('basic_info', {})
        fitness_config = user_profile.get('fitness_config', {})
        health_profile = user_profile.get('health_status', {})
        fitness_goals = user_profile.get('fitness_goals', {})
        
        # 构建用户信息摘要
        user_summary = f"""
- 年龄: {basic_info.get('age', '未知')}岁
- 性别: {basic_info.get('gender', '未知')}
- 训练水平: {fitness_config.get('fitness_level', '未知')}
- 训练频率: 每星期{fitness_config.get('training_days_per_week', '未知')}次
- 健身目标: {', '.join(fitness_goals.get('primary_goals', ['未设置']))}
- 健康状况: {', '.join(health_profile.get('chronic_diseases', ['无'])) if health_profile.get('chronic_diseases') else '无'}
- 损伤史: {', '.join(health_profile.get('injury_history', ['无'])) if health_profile.get('injury_history') else '无'}
"""
        
        # 获取格式化的模板列表
        templates_description = self.template_manager.get_templates_for_llm()
        
        # 构建提示词
        prompt = f"""你是玉珍健身APP的专业AI助手。用户向你咨询健身问题，你需要选择最合适的工作流程来回答用户。

## 用户信息
{user_summary}

## 用户查询
"{request.user_query}"

## 可选的工作流程（DAG模板）

{templates_description}

## 你的任务
1. **分析用户查询意图**：理解用户的核心需求和具体问题
2. **选择最合适的工作流程**：从上述工作流程中选择最匹配的一个
3. **说明选择理由**：解释为什么这个工作流程最适合
4. **评估置信度**：给出你对这个选择的置信度（0.0-1.0）

## 详细选择指南（请仔细阅读每个模板的定义和示例）

### 1. 问候闲聊 (greeting)
**定义**: 用户**仅仅**是打招呼、问候或简单闲聊，**不涉及任何具体的健身问题**
**示例查询**:
  - "你好" ✅
  - "早上好" ✅
  - "在吗" ✅
**反例（不要选greeting）**:
  - "你好，帮我推荐一个胸肌训练动作" ❌ → 应选 exercise_optimization
  - "嗨，我想制定训练计划" ❌ → 应选 complete_training_plan
  - "你好，我膝盖疼能练什么" ❌ → 应选 safety_assessment
**重要**: 如果用户在问候之后紧跟了具体的健身问题，必须根据问题内容选择对应模板，而非greeting

### 2. 完整训练计划 (complete_training_plan) ⭐⭐⭐ 高权重
**定义**: 用户需要系统的、详细的训练方案，包含动作选择、训练量计算、周期化安排
**高权重关键词**: 完整、详细、系统、全面、4周、8周、12周、训练计划、增肌计划、减脂计划、力量计划
**中权重关键词**: 制定、设计、帮我、给我、想要
**示例查询**:
  - "帮我设计一个完整的4周增肌训练计划" ✅ 高置信度（0.95+）
  - "我想制定一个详细的力量训练计划" ✅ 高置信度（0.90+）
  - "给我一个系统的增肌方案" ✅ 高置信度（0.90+）
  - "我需要一个12周的训练计划" ✅ 高置信度（0.95+）
  - "帮我设计增肌训练" ✅ 中等置信度（0.75+）
**置信度要求**: 包含"完整/详细/系统"或"X周"时置信度应>0.85

### 3. 营养规划 (nutrition_planning)
**定义**: 用户关注饮食、营养摄入、膳食计划
**关键词**: 营养、饮食、吃什么、膳食、食物、热量、蛋白质、碳水
**示例查询**:
  - "我应该吃什么来增肌？"
  - "帮我制定营养计划"
  - "增肌期间怎么吃？"
**置信度要求**: 明确提到营养/饮食时置信度应>0.80

### 4. 安全评估 (safety_assessment)
**定义**: 用户关心运动安全性、禁忌动作、风险评估
**关键词**: 安全、禁忌、风险、能否、可以做、不能做、危险
**示例查询**:
  - "我有腰椎问题，哪些动作不能做？"
  - "深蹲安全吗？"
  - "我能做硬拉吗？"
**置信度要求**: 明确提到安全/禁忌时置信度应>0.80

### 5. 动作优化 (exercise_optimization)
**定义**: 用户需要动作推荐、替代方案、动作调整
**关键词**: 动作、替代、换、推荐、选择、哪些动作
**示例查询**:
  - "深蹲可以换成什么动作？"
  - "推荐一些练胸的动作"
  - "有什么动作可以练背？"
**置信度要求**: 明确提到动作推荐/替代时置信度应>0.75

### 6. 综合健身方案 (comprehensive_fitness)
**定义**: 用户需要训练+营养的完整解决方案
**关键词**: 综合、全面、完整方案、系统方案、训练和营养
**示例查询**:
  - "给我一个完整的健身方案，包括训练和饮食"
  - "我需要综合的增肌指导"
**置信度要求**: 同时提到训练和营养时置信度应>0.85

### 7. 快速咨询 (quick_consultation)
**定义**: 简单的、一般性的健身问题，不需要复杂的工具链
**关键词**: 简单问题、一般咨询、基础问题
**示例查询**:
  - "什么是渐进超负荷？"
  - "训练后要拉伸吗？"
  - "一般建议"
**置信度要求**: 仅当查询非常简单且不涉及具体计划时选择（置信度0.6-0.8）
**重要**: 如果用户明确要求"完整"、"详细"、"系统"的计划，绝对不要选择此模板！

### 8. 进展分析 (progress_analysis)
**定义**: 用户想查看训练效果、数据分析、进度评估
**关键词**: 进展、分析、效果、数据、进度、评估
**示例查询**:
  - "帮我分析一下最近的训练效果"
  - "我的进展怎么样？"
**置信度要求**: 明确提到进展/分析时置信度应>0.80

### 9. 康复训练 (rehabilitation_training)
**定义**: 用户有伤病史，需要安全的康复训练方案
**关键词**: 康复、伤后、恢复、受伤、伤病
**示例查询**:
  - "我膝盖受伤了，怎么训练？"
  - "伤后康复训练计划"
**置信度要求**: 明确提到康复/伤后时置信度应>0.85

### 10. 体态矫正 (posture_correction)
**定义**: 用户有体态问题（圆肩驼背、骨盆前倾等），需要矫正训练方案
**关键词**: 体态、矫正、圆肩、驼背、骨盆前倾、姿势、改善体态
**示例查询**:
  - "我有圆肩驼背怎么矫正？"
  - "骨盆前倾该做什么训练？"
  - "帮我评估一下体态问题"
**置信度要求**: 明确提到体态/矫正时置信度应>0.80

### 11. 训练计划调整 (plan_adjustment)
**定义**: 用户已有训练计划，需要根据反馈或进展进行调整
**关键词**: 调整、修改、优化、换动作、调整训练量
**示例查询**:
  - "我觉得现在的计划太轻了，帮我调整一下"
  - "这个动作做不了，帮我换一个"
  - "训练量需要调整"
**置信度要求**: 明确提到调整/修改现有计划时置信度应>0.75

### 12. 减脂专项 (fat_loss_program)
**定义**: 用户以减脂/减肥为主要目标，需要训练+营养的综合减脂方案
**关键词**: 减脂、减肥、降体脂、瘦身、燃脂
**示例查询**:
  - "我想减脂，帮我制定方案"
  - "怎么减肥最有效？"
  - "帮我设计一个燃脂训练计划"
**置信度要求**: 明确提到减脂/减肥时置信度应>0.85
**重要**: 如果用户只是泛泛提到"减脂"作为目标之一，但主要需求是训练计划，应选 complete_training_plan

### 13. 力量专项 (strength_program)
**定义**: 用户以增强力量为主要目标，需要力量训练专项计划
**关键词**: 力量、大重量、最大力量、爆发力、力量提升
**示例查询**:
  - "我想提高深蹲力量"
  - "帮我设计一个力量训练计划"
  - "怎么提高卧推重量？"
**置信度要求**: 明确以力量为核心目标时置信度应>0.85
**重要**: 如果用户要的是"完整训练计划"且力量只是目标之一，应选 complete_training_plan

## 意图理解规则（重要！）
1. **语义优先**: 理解用户的真实意图，不要被开头的问候语干扰
2. **复合意图**: 如果用户同时包含问候+具体问题，以具体问题为准
3. **上下文感知**: 结合用户档案（训练水平、目标、伤病史）判断最合适的模板
4. **具体优先**: 越具体的需求越应该匹配专业模板，而非通用模板

## 复合意图示例
- "你好，帮我推荐胸肌训练动作" → exercise_optimization（不是greeting）
- "嗨，我想制定一个4周增肌计划" → complete_training_plan（不是greeting）
- "你好，我有腰椎问题能做深蹲吗" → safety_assessment（不是greeting）
- "早上好，分析一下我最近的训练数据" → progress_analysis（不是greeting）
- "你好，我想减肥" → fat_loss_program（不是greeting）
- "帮我调整一下现在的训练计划" → plan_adjustment（不是complete_training_plan）
- "我有圆肩驼背，怎么改善" → posture_correction（不是safety_assessment）
- "我想提高深蹲的最大力量" → strength_program（不是complete_training_plan）

## 决策流程
1. 首先检查是否包含高权重关键词
2. 如果包含"完整/详细/系统"或"X周"，强烈倾向于 complete_training_plan
3. 如果同时提到训练和营养，选择 comprehensive_fitness
4. 如果只提到营养/饮食，选择 nutrition_planning
5. 如果只提到安全/禁忌，选择 safety_assessment
6. 如果只提到动作推荐/替代，选择 exercise_optimization
7. 如果明确以减脂/减肥为目标，选择 fat_loss_program
8. 如果明确以力量提升为核心目标，选择 strength_program
9. 如果提到体态问题（圆肩/驼背/骨盆前倾），选择 posture_correction
10. 如果要调整/修改现有计划，选择 plan_adjustment
11. 只有在查询非常简单且不涉及具体计划时，才选择 quick_consultation

## 输出格式（必须是有效的JSON）
{{
  "selected_template_id": "模板ID（必须是上述模板之一）",
  "selection_reason": "选择理由（简洁明确，50字以内，说明匹配了哪些关键词）",
  "expected_tools": ["预期使用的工具列表"],
  "confidence": 0.95,
  "alternative_templates": ["备选模板ID1", "备选模板ID2"],
  "matched_keywords": ["匹配到的关键词列表"]
}}

## 重要约束
- ❌ 绝对不要编造模板ID，必须从上述模板中选择
- ✅ 选择理由必须基于用户查询和用户档案
- ✅ 置信度必须真实反映你的判断
- ✅ 必须列出匹配到的关键词
- ⚠️ 如果用户明确要求"完整"、"详细"、"系统"的计划，置信度必须>0.85，且不要选择quick_consultation

请输出你的选择（只输出JSON，不要其他内容）：
"""
        
        return prompt
    
    async def _call_llm(self, prompt: str, request: DAGSelectionRequest) -> str:
        """
        调用LLM（使用降级管理器）
        
        使用LLMFallbackManager进行LLM调用，支持自动降级和重试。
        降级策略：DeepSeek → Ollama → Template
        """
        try:
            # ✅ 使用DI容器单例
            from ..workflow.singletons import get_llm_degradation_manager
            from ...framework.clients.llm_fallback_manager import LLMRequest

            fallback_manager = get_llm_degradation_manager()
            
            # 准备LLM请求
            llm_request = LLMRequest(
                query=prompt,
                few_shot_examples=[],
                tool_results={},
                system_prompt="你是专业的健身AI助手，负责选择最合适的工作流程。",
                max_tokens=1000,
                temperature=0.3,  # 较低温度以获得更确定的选择
                stream=False
            )
            
            # 使用降级管理器调用LLM
            llm_response = await fallback_manager.call_with_fallback(llm_request)
            
            # 记录降级信息
            if llm_response.fallback_used:
                logger.warning(
                    f"⚠️ DAG选择使用了降级策略 "
                    f"(backend={llm_response.backend_used.value}, "
                    f"attempts={llm_response.attempt_count})"
                )
            
            if llm_response.error:
                logger.warning(
                    f"⚠️ DAG选择LLM调用有错误 "
                    f"(error={llm_response.error})"
                )
            
            logger.debug(
                f"LLM调用完成: backend={llm_response.backend_used.value}, "
                f"fallback={llm_response.fallback_used}, "
                f"attempts={llm_response.attempt_count}, "
                f"duration={llm_response.duration_ms:.0f}ms"
            )
            
            return llm_response.content
                
        except Exception as e:
            logger.error(f"LLM调用失败: {e}", exc_info=True)
            raise
    
    def _parse_llm_response(
        self,
        llm_response: str,
        available_templates: List[DAGTemplate]
    ) -> DAGSelectionResult:
        """解析LLM响应"""
        try:
            # 提取JSON（可能包含在markdown代码块中）
            json_str = llm_response.strip()
            
            # 移除可能的markdown代码块标记
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            elif json_str.startswith("```"):
                json_str = json_str[3:]
            
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            
            json_str = json_str.strip()
            
            # 解析JSON
            data = json.loads(json_str)
            
            # 提取字段
            selected_template_id = data.get("selected_template_id", "")
            selection_reason = data.get("selection_reason", "")
            expected_tools = data.get("expected_tools", [])
            confidence = float(data.get("confidence", 0.5))
            alternative_templates = data.get("alternative_templates", [])
            matched_keywords = data.get("matched_keywords", [])  # 新增：提取匹配的关键词
            
            # 确定置信度等级
            if confidence >= 0.8:
                confidence_level = SelectionConfidence.HIGH
            elif confidence >= 0.5:
                confidence_level = SelectionConfidence.MEDIUM
            else:
                confidence_level = SelectionConfidence.LOW
            
            return DAGSelectionResult(
                selected_template_id=selected_template_id,
                selection_reason=selection_reason,
                expected_tools=expected_tools,
                confidence=confidence,
                confidence_level=confidence_level,
                alternative_templates=alternative_templates,
                llm_raw_response=llm_response,
                fallback_used=False,
                matched_keywords=matched_keywords
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.debug(f"LLM原始响应: {llm_response}")
            raise ValueError(f"LLM响应不是有效的JSON: {e}")
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}", exc_info=True)
            raise
    
    def _validate_selection(
        self,
        selection_result: DAGSelectionResult,
        available_templates: List[DAGTemplate]
    ) -> bool:
        """验证选择结果"""
        # 检查模板ID是否存在
        template_ids = {t.template_id for t in available_templates}
        
        if selection_result.selected_template_id not in template_ids:
            logger.error(
                f"❌ LLM选择的模板ID不存在: {selection_result.selected_template_id}"
            )
            return False
        
        # 检查置信度范围
        if not (0.0 <= selection_result.confidence <= 1.0):
            logger.warning(
                f"⚠️ 置信度超出范围: {selection_result.confidence}"
            )
            return False
        
        # 检查选择理由
        if not selection_result.selection_reason:
            logger.warning("⚠️ 缺少选择理由")
            return False
        
        return True
    
    def _keyword_matching(self, request: DAGSelectionRequest) -> DAGSelectionResult:
        """
        @deprecated 关键词匹配策略（快速路径）— 已废弃

        v2 起所有查询统一走 LLM 分类，此方法仅保留供 _fallback_selection() 降级使用。
        后续版本将移除。
        """
        warnings.warn(
            "_keyword_matching() 已废弃，所有查询应走 LLM 分类",
            DeprecationWarning,
            stacklevel=2,
        )
        query_lower = request.user_query.lower()
        
        # 定义关键词映射（按优先级排序）
        # 每个关键词都有权重：高权重关键词（2.0）、中权重关键词（1.5）、普通关键词（1.0）
        keyword_mapping = {
            # 高优先级：完整训练计划
            "complete_training_plan": {
                "keywords": {
                    # 高权重关键词（权重×2.0）
                    "完整": 2.0, "详细": 2.0, "系统": 2.0, "全面": 2.0,
                    "4周": 2.0, "8周": 2.0, "12周": 2.0, "周计划": 2.0,
                    # 中权重关键词（权重×1.5）
                    "训练计划": 1.5, "增肌计划": 1.5, "减脂计划": 1.5, "力量计划": 1.5,
                    "制定": 1.5, "设计": 1.5, "帮我": 1.5, "给我": 1.5,
                    # 普通关键词（权重×1.0）
                    "训练": 1.0, "计划": 1.0, "增肌": 1.0, "减脂": 1.0, "力量": 1.0
                },
                "base_confidence": 0.7  # 基础置信度
            },
            # 中优先级：其他专业模板
            "comprehensive_fitness": {
                "keywords": {
                    "综合方案": 2.0, "完整方案": 2.0, "系统方案": 2.0,
                    "训练和营养": 1.5, "训练+营养": 1.5,
                    "综合": 1.0, "方案": 1.0
                },
                "base_confidence": 0.7
            },
            "nutrition_planning": {
                "keywords": {
                    "营养计划": 2.0, "饮食计划": 2.0, "膳食计划": 2.0,
                    "营养": 1.5, "饮食": 1.5, "膳食": 1.5,
                    "吃什么": 1.0, "餐食": 1.0, "热量": 1.0, "蛋白质": 1.0
                },
                "base_confidence": 0.7
            },
            "safety_assessment": {
                "keywords": {
                    "安全评估": 2.0, "风险评估": 2.0,
                    "安全": 1.5, "禁忌": 1.5, "风险": 1.5,
                    "能否": 1.0, "可以做": 1.0, "不能做": 1.0, "危险": 1.0
                },
                "base_confidence": 0.7
            },
            "exercise_optimization": {
                "keywords": {
                    "动作推荐": 2.0, "动作选择": 2.0, "动作替代": 2.0,
                    "动作": 1.5, "替代": 1.5, "推荐": 1.5,
                    "换": 1.0, "哪些动作": 1.0, "练": 1.0
                },
                "base_confidence": 0.7
            },
            "progress_analysis": {
                "keywords": {
                    "进展分析": 2.0, "效果分析": 2.0,
                    "进展": 1.5, "分析": 1.5, "效果": 1.5,
                    "数据": 1.0, "进度": 1.0, "评估": 1.0
                },
                "base_confidence": 0.7
            },
            "rehabilitation_training": {
                "keywords": {
                    "康复训练": 2.0, "伤后训练": 2.0,
                    "康复": 1.5, "伤后": 1.5, "恢复": 1.5,
                    "受伤": 1.0, "伤病": 1.0
                },
                "base_confidence": 0.7
            },
            # 特殊：问候闲聊（精确匹配）
            "greeting": {
                "keywords": {
                    "你好": 2.0, "早上好": 2.0, "晚上好": 2.0,
                    "hi": 2.0, "hello": 2.0, "嗨": 2.0, "在吗": 2.0
                },
                "base_confidence": 0.9  # 问候语置信度高
            },
            # 低优先级：快速咨询（最后匹配）
            "quick_consultation": {
                "keywords": {
                    "简单": 1.0, "快速": 1.0, "一般": 1.0, "基础": 1.0
                },
                "base_confidence": 0.5
            }
        }
        
        # 计算每个模板的匹配得分
        template_scores = {}
        
        for template_id, config in keyword_mapping.items():
            keywords = config["keywords"]
            base_confidence = config["base_confidence"]
            
            # 计算匹配得分
            matched_kws = []
            total_weight = 0.0
            
            for keyword, weight in keywords.items():
                if keyword in query_lower:
                    matched_kws.append(keyword)
                    total_weight += weight
            
            if matched_kws:
                # 置信度 = 基础置信度 + (总权重 × 0.05)，最高0.95
                confidence = min(base_confidence + total_weight * 0.05, 0.95)
                
                template_scores[template_id] = {
                    "confidence": confidence,
                    "matched_keywords": matched_kws,
                    "total_weight": total_weight
                }
        
        # 选择得分最高的模板
        if template_scores:
            # 按置信度排序
            sorted_templates = sorted(
                template_scores.items(),
                key=lambda x: x[1]["confidence"],
                reverse=True
            )
            
            best_template_id = sorted_templates[0][0]
            best_score = sorted_templates[0][1]
            
            template = self.template_manager.get_template(best_template_id)
            
            if template:
                # 提取备选模板（置信度前3名）
                alternative_templates = [
                    t[0] for t in sorted_templates[1:3]
                ]
                
                # 确定置信度等级
                confidence = best_score["confidence"]
                if confidence >= 0.8:
                    confidence_level = SelectionConfidence.HIGH
                elif confidence >= 0.5:
                    confidence_level = SelectionConfidence.MEDIUM
                else:
                    confidence_level = SelectionConfidence.LOW
                
                logger.debug(f"关键词匹配: {best_template_id}")
                logger.debug(f"  匹配关键词: {', '.join(best_score['matched_keywords'])}")
                logger.debug(f"  总权重: {best_score['total_weight']:.1f}")
                logger.debug(f"  置信度: {confidence:.2f}")
                
                return DAGSelectionResult(
                    selected_template_id=best_template_id,
                    selection_reason=f"关键词匹配: {', '.join(best_score['matched_keywords'][:3])}",
                    expected_tools=template.required_tools,
                    confidence=confidence,
                    confidence_level=confidence_level,
                    alternative_templates=alternative_templates,
                    llm_raw_response=None,
                    fallback_used=False,
                    matched_keywords=best_score["matched_keywords"]
                )
        
        # 没有匹配到任何关键词：使用默认模板（快速咨询）
        logger.debug("⚠️ 无法匹配关键词，使用默认模板: quick_consultation")
        template = self.template_manager.get_template("quick_consultation")
        
        return DAGSelectionResult(
            selected_template_id="quick_consultation",
            selection_reason="无法明确意图，使用快速咨询模板",
            expected_tools=template.required_tools if template else [],
            confidence=0.4,
            confidence_level=SelectionConfidence.LOW,
            alternative_templates=["complete_training_plan", "exercise_optimization"],
            llm_raw_response=None,
            fallback_used=False,
            matched_keywords=[]
        )
    
    def _fallback_selection(self, request: DAGSelectionRequest) -> DAGSelectionResult:
        """
        降级策略：当LLM失败时使用关键词匹配
        
        这个方法现在只是 _keyword_matching 的别名，保持向后兼容。
        """
        logger.info("🔄 使用降级策略（关键词匹配）")
        self.selection_stats["fallback_selections"] += 1
        
        result = self._keyword_matching(request)
        result.fallback_used = True  # 标记为降级
        
        return result
    
    def get_selection_statistics(self) -> Dict[str, Any]:
        """获取选择统计信息"""
        return {
            **self.selection_stats,
            "success_rate": (
                self.selection_stats["successful_selections"] / 
                self.selection_stats["total_selections"]
                if self.selection_stats["total_selections"] > 0 else 0.0
            ),
            "fallback_rate": (
                self.selection_stats["fallback_selections"] / 
                self.selection_stats["total_selections"]
                if self.selection_stats["total_selections"] > 0 else 0.0
            )
        }


# 使用示例
if __name__ == "__main__":
    import asyncio
    
    async def test_llm_decision_engine():
        """测试LLM决策引擎"""
        
        # 初始化
        engine = LLMDecisionEngine()
        
        # 模拟用户档案
        user_profile = {
            "user_id": "test_user_123",
            "basic_info": {
                "age": 28,
                "gender": "男",
                "weight": 75,
                "height": 175
            },
            "fitness_config": {
                "fitness_level": "intermediate",
                "training_days_per_week": 4
            },
            "fitness_goals": {
                "primary_goals": ["增肌", "力量提升"]
            },
            "health_status": {
                "chronic_diseases": [],
                "injury_history": []
            }
        }
        
        # 测试用例
        test_queries = [
            "我想制定一个增肌训练计划",
            "我应该吃什么来增肌？",
            "我有腰椎问题，哪些动作不能做？",
            "帮我分析一下最近的训练效果",
            "深蹲可以换成什么动作？"
        ]
        
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"用户查询: {query}")
            print(f"{'='*60}")
            
            # 创建请求
            request = DAGSelectionRequest(
                user_query=query,
                user_profile=user_profile,
                available_templates=engine.template_manager.get_all_templates()
            )
            
            # 执行选择
            result = await engine.select_dag_template(request)
            
            # 输出结果
            print(f"✅ 选择模板: {result.selected_template_id}")
            print(f"📝 选择理由: {result.selection_reason}")
            print(f"🎯 置信度: {result.confidence:.2f} ({result.confidence_level.value})")
            print(f"🔧 预期工具: {len(result.expected_tools)}个")
            if result.fallback_used:
                print(f"⚠️ 使用了降级策略")
        
        # 输出统计
        print(f"\n{'='*60}")
        print("统计信息:")
        print(f"{'='*60}")
        stats = engine.get_selection_statistics()
        print(f"总选择次数: {stats['total_selections']}")
        print(f"成功率: {stats['success_rate']:.1%}")
        print(f"降级率: {stats['fallback_rate']:.1%}")
        print(f"平均置信度: {stats['average_confidence']:.2f}")
        print(f"按模板统计: {stats['by_template']}")
    
    # 运行测试
    asyncio.run(test_llm_decision_engine())
