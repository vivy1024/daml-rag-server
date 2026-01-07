# -*- coding: utf-8 -*-
"""
Find Similar Training Cases MCP Tool

基于质量评分和用户特征推荐相似的训练案例。
利用现有的Few-Shot存储机制和质量评分系统。

功能：
1. 根据用户查询和特征查找相似案例
2. 基于三轨评分过滤高质量案例
3. 考虑训练效果标签（excellent/good/fair/poor）
4. 支持用户反馈文本存储
5. 实现降级策略（检索器不可用时降级到后端API）
6. 返回可参考的成功案例

版本: v2.0.0
日期: 2025-12-31
作者: 薛小川

@requirements 4.2, 4.3, 4.4, 4.5, 4.6
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from .base_tool import BaseMCPTool, ToolMetadata

# 导入统一的Few-Shot类型
try:
    from ..types.fewshot_types import (
        UnifiedFewShotExample,
        FewShotRetrievalStats,
        TrainingEffectLabel,
        TRAINING_EFFECT_CONFIG,
        get_training_effect_from_score,
        check_basic_fewshot_eligibility
    )
    UNIFIED_TYPES_AVAILABLE = True
except ImportError:
    UNIFIED_TYPES_AVAILABLE = False

logger = logging.getLogger(__name__)


# 输入Schema
class FindSimilarTrainingCasesInput(BaseModel):
    """查找相似训练案例的输入"""
    query: str = Field(..., description="用户查询（如：'增肌训练计划'）")
    user_profile: Dict[str, Any] = Field(..., description="用户档案")
    training_goal: Optional[str] = Field(None, description="训练目标（可选，如：'增肌'、'减脂'、'力量'）")
    min_quality_score: float = Field(4.0, description="最低质量评分（默认4.0）")
    training_effect_filter: Optional[str] = Field(None, description="训练效果过滤（可选，如：'excellent'、'good'、'fair'、'poor'）")
    top_k: int = Field(5, description="返回案例数量（默认5）")
    only_fewshot_eligible: bool = Field(True, description="只返回符合Few-Shot条件的案例（默认True）")
    include_user_feedback: bool = Field(True, description="是否包含用户反馈文本（默认True）")


# 输出Schema
class FindSimilarTrainingCasesOutput(BaseModel):
    """查找相似训练案例的输出"""
    success: bool = Field(..., description="是否成功")
    similar_cases: List[Dict[str, Any]] = Field(default_factory=list, description="相似案例列表")
    total_found: int = Field(0, description="找到的案例总数")
    recommendation: str = Field("", description="推荐说明")
    retrieval_stats: Dict[str, Any] = Field(default_factory=dict, description="检索统计信息")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="应用的过滤条件")
    retrieval_method: str = Field("", description="检索方法（vector/backend_api/fallback）")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")


class FindSimilarTrainingCasesTool(BaseMCPTool):
    """
    查找相似训练案例工具
    
    基于用户查询和特征，从历史会话中查找相似的成功案例。
    利用Few-Shot质量评分机制，推荐高质量的训练案例。
    
    核心功能：
    1. 基于三轨评分筛选高质量案例 @requirements 4.3
    2. 支持训练效果标签过滤 @requirements 4.4
    3. 包含用户反馈文本 @requirements 4.5
    4. 实现降级策略 @requirements 4.6
    """
    
    def __init__(self, backend_client=None, vector_store=None):
        """
        初始化工具
        
        Args:
            backend_client: 后端客户端（用于查询历史会话和降级搜索）
            vector_store: 向量存储（用于语义相似度搜索）
        """
        # 调用父类初始化
        super().__init__(
            neo4j_client=None,
            qdrant_client=None,
            three_layer_engine=None
        )
        
        self.backend_client = backend_client
        self.vector_store = vector_store
        
        # 初始化Few-Shot检索器
        self.few_shot_retriever = None
        self._init_few_shot_retriever()
        
        # 降级状态追踪
        self._retriever_available = self.few_shot_retriever is not None
        self._last_retriever_check = datetime.now()
        self._retriever_check_interval = timedelta(minutes=5)
    
    def _init_few_shot_retriever(self):
        """初始化Few-Shot检索器"""
        try:
            from ....framework.retrieval.enhanced_few_shot_retriever import EnhancedFewShotRetriever
            self.few_shot_retriever = EnhancedFewShotRetriever(
                vector_store=self.vector_store,
                backend_client=self.backend_client
            )
            logger.info("✅ Few-Shot检索器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ Few-Shot检索器初始化失败: {e}")
            self.few_shot_retriever = None
    
    def get_name(self) -> str:
        """获取工具名称"""
        return "find_similar_training_cases"
    
    def get_description(self) -> str:
        """获取工具描述"""
        return "查找相似的训练案例，基于质量评分和用户特征推荐成功案例"
    
    def get_category(self) -> str:
        """获取工具分类"""
        return "learning"
    
    def get_complexity(self) -> str:
        """获取工具复杂度"""
        return "medium"
    
    def requires_user_profile(self) -> bool:
        """是否需要用户档案"""
        return True
    
    def get_input_schema(self) -> type[BaseModel]:
        """获取输入Schema"""
        return FindSimilarTrainingCasesInput
    
    def get_output_schema(self) -> type[BaseModel]:
        """获取输出Schema"""
        return FindSimilarTrainingCasesOutput
    
    def get_metadata(self) -> ToolMetadata:
        """获取工具元数据"""
        return ToolMetadata(
            name=self.get_name(),
            description=self.get_description(),
            category=self.get_category(),
            complexity=self.get_complexity(),
            estimated_duration_ms=500.0,  # 预估500ms
            requires_user_profile=self.requires_user_profile(),
            dependencies=[]  # 无外部依赖
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具：查找相似训练案例
        
        Args:
            input_data: 输入数据，包含：
                - query (str): 用户查询
                - user_profile (dict): 用户档案
                - training_goal (str, optional): 训练目标
                - min_quality_score (float, optional): 最低质量评分（默认4.0）
                - training_effect_filter (str, optional): 训练效果过滤（excellent/good/fair/poor）
                - top_k (int, optional): 返回案例数量（默认5）
                - only_fewshot_eligible (bool, optional): 只返回符合Few-Shot条件的（默认True）
                - include_user_feedback (bool, optional): 是否包含用户反馈（默认True）
        
        Returns:
            Dict包含：
                - success (bool): 是否成功
                - similar_cases (list): 相似案例列表
                - total_found (int): 找到的案例总数
                - recommendation (str): 推荐说明
                - retrieval_method (str): 检索方法
        """
        try:
            # 1. 提取参数
            query = input_data.get("query", "")
            user_profile = input_data.get("user_profile", {})
            training_goal = input_data.get("training_goal")
            min_quality_score = input_data.get("min_quality_score", 4.0)
            training_effect_filter = input_data.get("training_effect_filter")
            top_k = input_data.get("top_k", 5)
            only_fewshot_eligible = input_data.get("only_fewshot_eligible", True)
            include_user_feedback = input_data.get("include_user_feedback", True)
            
            if not query:
                return {
                    "success": False,
                    "error": "查询不能为空",
                    "similar_cases": [],
                    "total_found": 0,
                    "retrieval_method": "none"
                }
            
            logger.info(f"🔍 查找相似训练案例: query='{query}', goal={training_goal}, effect_filter={training_effect_filter}")
            
            # 2. 尝试使用Few-Shot检索器（带降级策略）
            similar_examples = []
            retrieval_stats = {}
            retrieval_method = "none"
            
            # 检查检索器是否可用（定期重试）
            if not self._retriever_available:
                self._check_retriever_availability()
            
            if self._retriever_available and self.few_shot_retriever:
                try:
                    similar_examples, retrieval_stats = await self.few_shot_retriever.retrieve_with_quality_filter(
                        query=query,
                        user_id=user_profile.get("user_id"),
                        query_complexity=None,  # 自动判断
                        top_k=top_k * 2  # 多检索一些，后续再过滤
                    )
                    retrieval_method = "vector"
                    logger.info(f"✅ 向量检索成功，找到 {len(similar_examples)} 个候选案例")
                except Exception as e:
                    logger.warning(f"⚠️ 向量检索失败，降级到后端API: {e}")
                    self._retriever_available = False
                    similar_examples = await self._fallback_search(
                        query=query,
                        user_profile=user_profile,
                        top_k=top_k * 2,
                        only_fewshot_eligible=only_fewshot_eligible
                    )
                    retrieval_method = "backend_api"
            else:
                # 降级：直接从后端API搜索 @requirements 4.6
                similar_examples = await self._fallback_search(
                    query=query,
                    user_profile=user_profile,
                    top_k=top_k * 2,
                    only_fewshot_eligible=only_fewshot_eligible
                )
                retrieval_method = "fallback"
            
            # 3. 应用额外过滤条件（三轨评分筛选）@requirements 4.3
            filtered_cases = self._apply_filters(
                examples=similar_examples,
                min_quality_score=min_quality_score,
                training_effect_filter=training_effect_filter,
                training_goal=training_goal,
                user_profile=user_profile,
                only_fewshot_eligible=only_fewshot_eligible
            )
            
            # 4. 限制返回数量
            final_cases = filtered_cases[:top_k]
            
            # 5. 格式化结果（包含用户反馈）@requirements 4.5
            formatted_cases = self._format_cases(final_cases, include_user_feedback)
            
            # 6. 生成推荐说明
            recommendation = self._generate_recommendation(
                cases=final_cases,
                query=query,
                training_goal=training_goal
            )
            
            logger.info(
                f"✅ 找到{len(final_cases)}个相似训练案例 "
                f"(过滤前: {len(similar_examples)}, 方法: {retrieval_method})"
            )
            
            return {
                "success": True,
                "similar_cases": formatted_cases,
                "total_found": len(final_cases),
                "recommendation": recommendation,
                "retrieval_stats": retrieval_stats if isinstance(retrieval_stats, dict) else {},
                "filters_applied": {
                    "min_quality_score": min_quality_score,
                    "training_effect_filter": training_effect_filter,
                    "training_goal": training_goal,
                    "only_fewshot_eligible": only_fewshot_eligible
                },
                "retrieval_method": retrieval_method
            }
            
        except Exception as e:
            logger.error(f"❌ 查找相似训练案例失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "similar_cases": [],
                "total_found": 0,
                "retrieval_method": "error"
            }
    
    def _check_retriever_availability(self):
        """
        检查检索器是否可用（定期重试）
        @requirements 4.6
        """
        now = datetime.now()
        if now - self._last_retriever_check > self._retriever_check_interval:
            self._last_retriever_check = now
            self._init_few_shot_retriever()
            self._retriever_available = self.few_shot_retriever is not None
            if self._retriever_available:
                logger.info("✅ Few-Shot检索器恢复可用")
    
    async def _fallback_search(
        self,
        query: str,
        user_profile: Dict[str, Any],
        top_k: int,
        only_fewshot_eligible: bool = True
    ) -> List[Any]:
        """
        降级搜索：直接从后端API搜索相似对话
        
        @requirements 4.6 - 检索器不可用时降级到后端API
        
        Args:
            query: 查询文本
            user_profile: 用户档案
            top_k: 返回数量
            only_fewshot_eligible: 只返回符合Few-Shot条件的
        
        Returns:
            List[FewShotExample]: 相似案例列表（模拟格式）
        """
        try:
            if not self.backend_client:
                logger.warning("⚠️ 后端客户端未初始化，无法执行降级搜索")
                return []
            
            logger.info(f"🔄 执行降级搜索: query='{query[:50]}...', only_eligible={only_fewshot_eligible}")
            
            # 调用后端API搜索相似对话
            result = await self.backend_client.search_similar_conversations(
                query=query,
                user_id=user_profile.get("user_id"),
                limit=top_k,
                min_rating=4.0,
                only_fewshot_eligible=only_fewshot_eligible
            )
            
            conversations = result.get("conversations", [])
            
            # 转换为FewShotExample格式
            from ....framework.retrieval.enhanced_few_shot_retriever import FewShotExample
            
            examples = []
            for conv in conversations:
                try:
                    # 提取三轨评分详情
                    three_track_scores = None
                    if conv.get("ux_clarity") is not None:
                        ux_scores = [
                            conv.get("ux_clarity", 0),
                            conv.get("ux_practicality", 0),
                            conv.get("ux_detail", 0),
                            conv.get("ux_friendliness", 0),
                            conv.get("ux_satisfaction", 0)
                        ]
                        ux_avg = sum(s for s in ux_scores if s) / max(len([s for s in ux_scores if s]), 1)
                        
                        pers_scores = [
                            conv.get("profile_utilization_rate", 0),
                            conv.get("goal_alignment", 0),
                            conv.get("uniqueness", 0),
                            conv.get("dynamic_adjustment", 0)
                        ]
                        # 转换为5分制
                        pers_avg = sum(s for s in pers_scores if s) / max(len([s for s in pers_scores if s]), 1) / 20
                        
                        three_track_scores = {
                            "user_experience_avg": ux_avg,
                            "personalization_avg": pers_avg,
                            "expert_avg": conv.get("expert_avg"),
                            "safety_score": conv.get("safety_score")
                        }
                    
                    example = FewShotExample(
                        query=conv.get("user_query", ""),
                        response=conv.get("llm_response", ""),
                        user_rating=float(conv.get("reward", conv.get("user_rating", 0))),
                        quality_score=float(conv.get("quality_score", conv.get("overall_score", 0))),
                        similarity=float(conv.get("similarity", 0.5)),
                        tools_used=conv.get("tools_used", []),
                        model_used=conv.get("model_used", ""),
                        timestamp=datetime.fromisoformat(conv.get("created_at", datetime.now().isoformat()).replace("Z", "+00:00")),
                        session_id=conv.get("session_id", ""),
                        metadata={
                            **conv.get("metadata", {}),
                            "three_track_scores": three_track_scores,
                            "personalization_grade": conv.get("personalization_grade"),
                            "profile_utilization_rate": conv.get("profile_utilization_rate")
                        },
                        training_effect=conv.get("training_effect"),
                        user_feedback=conv.get("user_feedback", conv.get("feedback_text"))
                    )
                    examples.append(example)
                except Exception as e:
                    logger.debug(f"跳过无效对话: {e}")
                    continue
            
            logger.info(f"✅ 降级搜索完成，找到 {len(examples)} 个案例")
            return examples
            
        except Exception as e:
            logger.error(f"❌ 降级搜索失败: {e}")
            return []
    
    def _apply_filters(
        self,
        examples: List[Any],
        min_quality_score: float,
        training_effect_filter: Optional[str],
        training_goal: Optional[str],
        user_profile: Dict[str, Any],
        only_fewshot_eligible: bool = True
    ) -> List[Any]:
        """
        应用额外的过滤条件（基于三轨评分筛选）
        
        @requirements 4.3 - 检索时过滤低评分案例
        @requirements 4.4 - 训练效果标签支持
        
        Args:
            examples: 候选案例列表
            min_quality_score: 最低质量评分
            training_effect_filter: 训练效果过滤
            training_goal: 训练目标
            user_profile: 用户档案
            only_fewshot_eligible: 只返回符合Few-Shot条件的
        
        Returns:
            List[FewShotExample]: 过滤后的案例列表
        """
        filtered = []
        
        for example in examples:
            # 1. 质量评分过滤
            if example.quality_score < min_quality_score:
                continue
            
            # 2. Few-Shot资格过滤（基于三轨评分）@requirements 4.3
            if only_fewshot_eligible:
                # 检查三轨评分是否达标
                metadata = example.metadata or {}
                three_track_scores = metadata.get("three_track_scores", {})
                
                if three_track_scores:
                    ux_avg = three_track_scores.get("user_experience_avg")
                    pers_avg = three_track_scores.get("personalization_avg")
                    safety_score = three_track_scores.get("safety_score")
                    
                    # 用户体验评分检查
                    if ux_avg is not None and ux_avg < 4.0:
                        continue
                    
                    # 个性化感知评分检查
                    if pers_avg is not None and pers_avg < 4.0:
                        continue
                    
                    # 安全性一票否决
                    if safety_score is not None and safety_score < 3:
                        continue
            
            # 3. 训练效果过滤 @requirements 4.4
            if training_effect_filter:
                if not example.training_effect:
                    # 如果没有训练效果标签，根据质量评分推断
                    if UNIFIED_TYPES_AVAILABLE:
                        inferred_effect = get_training_effect_from_score(example.quality_score)
                    else:
                        inferred_effect = self._infer_training_effect(example.quality_score)
                    
                    # 检查推断的效果是否符合过滤条件
                    effect_order = ["excellent", "good", "fair", "poor"]
                    filter_index = effect_order.index(training_effect_filter) if training_effect_filter in effect_order else 3
                    inferred_index = effect_order.index(inferred_effect) if inferred_effect in effect_order else 3
                    
                    if inferred_index > filter_index:
                        continue
                else:
                    # 有训练效果标签，直接比较
                    effect_order = ["excellent", "good", "fair", "poor"]
                    filter_index = effect_order.index(training_effect_filter) if training_effect_filter in effect_order else 3
                    example_index = effect_order.index(example.training_effect) if example.training_effect in effect_order else 3
                    
                    if example_index > filter_index:
                        continue
            
            # 4. 训练目标匹配（从metadata中提取）
            if training_goal:
                metadata = example.metadata or {}
                case_goal = metadata.get("training_goal")
                if case_goal and case_goal.lower() != training_goal.lower():
                    # 目标不匹配，但如果是高质量案例，仍然保留
                    if example.quality_score < 4.5:
                        continue
            
            # 5. 用户特征相似性匹配（可选增强）
            if user_profile:
                # 可以添加更复杂的用户特征匹配逻辑
                # 例如：训练水平、年龄、性别等
                pass
            
            filtered.append(example)
        
        return filtered
    
    def _infer_training_effect(self, quality_score: float) -> str:
        """
        根据质量评分推断训练效果标签
        
        Args:
            quality_score: 质量评分 (0-5)
        
        Returns:
            训练效果标签
        """
        if quality_score >= 4.5:
            return "excellent"
        elif quality_score >= 4.0:
            return "good"
        elif quality_score >= 3.0:
            return "fair"
        return "poor"
    
    def _format_cases(self, cases: List[Any], include_user_feedback: bool = True) -> List[Dict[str, Any]]:
        """
        格式化案例为返回格式
        
        @requirements 4.5 - 用户反馈文本存储
        
        Args:
            cases: 案例列表
            include_user_feedback: 是否包含用户反馈
        
        Returns:
            List[Dict]: 格式化后的案例列表
        """
        formatted = []
        
        for i, case in enumerate(cases, 1):
            # 提取三轨评分详情
            metadata = case.metadata or {}
            three_track_scores = metadata.get("three_track_scores", {})
            
            formatted_case = {
                "rank": i,
                "query": case.query,
                "response_summary": case.response[:200] + "..." if len(case.response) > 200 else case.response,
                "full_response": case.response,
                "quality_score": case.quality_score,
                "user_rating": case.user_rating,
                "similarity": case.similarity,
                "training_effect": case.training_effect or self._infer_training_effect(case.quality_score),
                "tools_used": case.tools_used,
                "model_used": case.model_used,
                "timestamp": case.timestamp.isoformat() if hasattr(case.timestamp, 'isoformat') else str(case.timestamp),
                "session_id": case.session_id,
                # 三轨评分详情
                "three_track_scores": three_track_scores if three_track_scores else None,
                "personalization_grade": metadata.get("personalization_grade"),
                "profile_utilization_rate": metadata.get("profile_utilization_rate"),
                # 元数据（排除已提取的字段）
                "metadata": {k: v for k, v in metadata.items() 
                           if k not in ["three_track_scores", "personalization_grade", "profile_utilization_rate"]}
            }
            
            # 包含用户反馈 @requirements 4.5
            if include_user_feedback:
                formatted_case["user_feedback"] = case.user_feedback
            
            formatted.append(formatted_case)
        
        return formatted
    
    def _generate_recommendation(
        self,
        cases: List[Any],
        query: str,
        training_goal: Optional[str]
    ) -> str:
        """
        生成推荐说明
        
        Args:
            cases: 案例列表
            query: 用户查询
            training_goal: 训练目标
        
        Returns:
            str: 推荐说明
        """
        if not cases:
            return "未找到相似的训练案例。建议咨询专业教练获取个性化指导。"
        
        # 计算平均质量评分
        avg_quality = sum(case.quality_score for case in cases) / len(cases)
        
        # 统计训练效果
        effect_counts = {}
        for case in cases:
            effect = case.training_effect or self._infer_training_effect(case.quality_score)
            effect_counts[effect] = effect_counts.get(effect, 0) + 1
        
        # 统计个性化等级
        grade_counts = {}
        for case in cases:
            metadata = case.metadata or {}
            grade = metadata.get("personalization_grade")
            if grade:
                grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # 生成推荐文本
        recommendation = f"找到{len(cases)}个相似的训练案例，平均质量评分{avg_quality:.1f}/5.0。\n\n"
        
        if effect_counts:
            recommendation += "📊 训练效果分布：\n"
            effect_labels = {
                "excellent": "优秀",
                "good": "良好",
                "fair": "一般",
                "poor": "较差"
            }
            for effect, count in sorted(effect_counts.items(), key=lambda x: x[1], reverse=True):
                label = effect_labels.get(effect, effect)
                recommendation += f"  • {label}: {count}个案例\n"
        
        if grade_counts:
            recommendation += "\n🎯 个性化等级分布：\n"
            for grade, count in sorted(grade_counts.items()):
                recommendation += f"  • {grade}级: {count}个案例\n"
        
        # 添加用户反馈统计
        feedback_count = sum(1 for case in cases if case.user_feedback)
        if feedback_count > 0:
            recommendation += f"\n💬 {feedback_count}个案例包含用户反馈，可供参考。\n"
        
        recommendation += "\n⚠️ 这些案例可以作为您训练计划的参考，但请根据自身情况调整。"
        
        return recommendation


# 工具元数据
TOOL_METADATA = {
    "name": "find_similar_training_cases",
    "description": "查找相似的训练案例，基于三轨评分和用户特征推荐成功案例",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "用户查询（如：'增肌训练计划'）"
            },
            "user_profile": {
                "type": "object",
                "description": "用户档案"
            },
            "training_goal": {
                "type": "string",
                "description": "训练目标（可选，如：'增肌'、'减脂'、'力量'）"
            },
            "min_quality_score": {
                "type": "number",
                "description": "最低质量评分（默认4.0）"
            },
            "training_effect_filter": {
                "type": "string",
                "enum": ["excellent", "good", "fair", "poor"],
                "description": "训练效果过滤（可选）"
            },
            "top_k": {
                "type": "integer",
                "description": "返回案例数量（默认5）"
            },
            "only_fewshot_eligible": {
                "type": "boolean",
                "description": "只返回符合Few-Shot条件的案例（默认True）"
            },
            "include_user_feedback": {
                "type": "boolean",
                "description": "是否包含用户反馈文本（默认True）"
            }
        },
        "required": ["query", "user_profile"]
    }
}


# 导出
__all__ = ["FindSimilarTrainingCasesTool", "TOOL_METADATA"]
