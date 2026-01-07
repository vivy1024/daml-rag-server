# -*- coding: utf-8 -*-
"""
三轨评分服务模块

在DAML-RAG工作流最后一步执行三轨评分：
1. 自动计算个性化感知评分
2. 检查Few-Shot准入资格
3. 高评分对话自动导入Few-Shot库

版本: v1.0.0
日期: 2025-12-31

Requirements: 3.7, 3.8
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PersonalizationGrade(str, Enum):
    """个性化等级"""
    S = "S"  # 90-100%
    A = "A"  # 75-89%
    B = "B"  # 60-74%
    C = "C"  # 40-59%
    D = "D"  # 0-39%


@dataclass
class PersonalizationScores:
    """个性化感知评分"""
    profile_utilization_rate: float = 0.0  # 档案利用率 0-100%
    goal_alignment: float = 0.0            # 目标对齐度 0-100%
    uniqueness: float = 0.0                # 独特性 0-100%
    dynamic_adjustment: float = 0.0        # 动态调整 0-100%
    
    @property
    def average(self) -> float:
        """计算平均分"""
        return (self.profile_utilization_rate + self.goal_alignment + 
                self.uniqueness + self.dynamic_adjustment) / 4
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'profile_utilization_rate': self.profile_utilization_rate,
            'goal_alignment': self.goal_alignment,
            'uniqueness': self.uniqueness,
            'dynamic_adjustment': self.dynamic_adjustment,
            'average': self.average
        }


@dataclass
class ThreeTrackRatingResult:
    """三轨评分结果"""
    session_id: str
    personalization: PersonalizationScores
    personalization_grade: PersonalizationGrade
    fewshot_eligible: bool
    eligibility_reason: str
    overall_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'personalization': self.personalization.to_dict(),
            'personalization_grade': self.personalization_grade.value,
            'fewshot_eligible': self.fewshot_eligible,
            'eligibility_reason': self.eligibility_reason,
            'overall_score': self.overall_score
        }


class ThreeTrackRatingService:
    """
    三轨评分服务
    
    在DAML-RAG工作流最后一步执行：
    1. 自动计算个性化感知评分
    2. 检查Few-Shot准入资格
    3. 高评分对话自动导入Few-Shot库
    """
    
    # 个性化等级阈值
    GRADE_THRESHOLDS = {
        PersonalizationGrade.S: 90,
        PersonalizationGrade.A: 75,
        PersonalizationGrade.B: 60,
        PersonalizationGrade.C: 40,
        PersonalizationGrade.D: 0
    }
    
    # Few-Shot准入阈值
    FEWSHOT_THRESHOLD = 4.0  # 三轨高分阈值
    COLD_START_THRESHOLD = 3.5  # 冷启动期阈值
    COLD_START_SESSION_COUNT = 3  # 冷启动期对话数量
    
    def __init__(self, backend_client=None, qdrant_client=None):
        """
        初始化服务
        
        Args:
            backend_client: 后端API客户端
            qdrant_client: Qdrant向量库客户端
        """
        self.backend_client = backend_client
        self.qdrant_client = qdrant_client
    
    def calculate_personalization_scores(
        self,
        user_profile: Optional[Dict[str, Any]],
        tools_used: List[str],
        metadata: Dict[str, Any],
        response_length: int = 0
    ) -> PersonalizationScores:
        """
        计算个性化感知评分
        
        Args:
            user_profile: 用户档案
            tools_used: 使用的工具列表
            metadata: 元数据
            response_length: 回复长度
            
        Returns:
            PersonalizationScores: 个性化感知评分
        """
        scores = PersonalizationScores()
        
        # 1. 计算档案利用率
        scores.profile_utilization_rate = self._calculate_profile_utilization(
            user_profile, tools_used, metadata
        )
        
        # 2. 计算目标对齐度
        scores.goal_alignment = self._calculate_goal_alignment(
            user_profile, metadata
        )
        
        # 3. 计算独特性
        scores.uniqueness = self._calculate_uniqueness(
            tools_used, response_length
        )
        
        # 4. 计算动态调整
        scores.dynamic_adjustment = self._calculate_dynamic_adjustment(
            metadata
        )
        
        return scores
    
    def _calculate_profile_utilization(
        self,
        user_profile: Optional[Dict[str, Any]],
        tools_used: List[str],
        metadata: Dict[str, Any]
    ) -> float:
        """计算档案利用率"""
        score = 0.0
        
        # 检查是否有用户档案
        if not user_profile:
            return 0.0
        
        # 基础分：有用户档案就给30分
        score += 30
        
        # 检查是否使用了个性化工具（这些工具会使用用户档案）
        profile_related_tools = [
            'intelligent_exercise_selector',  # 根据用户能力选择动作
            'contraindications_checker',      # 根据用户伤病检查禁忌
            'injury_risk_assessor',           # 根据用户情况评估风险
            'professional_program_designer',  # 根据用户目标设计计划
            'periodized_program_designer',    # 根据用户水平设计周期化
            'safe_exercise_modifier',         # 根据用户限制修改动作
            'tdee_calculator',                # 根据用户数据计算TDEE
        ]
        for tool in profile_related_tools:
            if tool in tools_used:
                score += 8  # 每个工具8分，最多56分
        
        # 检查档案字段使用情况（用户档案的实际结构）
        profile_fields = {
            'basic_info': 5,        # 基本信息
            'fitness_goals': 10,    # 健身目标
            'health_profile': 10,   # 健康档案
            'fitness_config': 10,   # 健身配置
            'strength_levels': 5,   # 力量水平
            'training_system': 5,   # 训练系统
            'available_equipment': 5,  # 可用器械
            'injuries': 10,         # 伤病信息
            'contraindications': 10, # 禁忌症
        }
        
        for field, points in profile_fields.items():
            value = user_profile.get(field)
            if value and (isinstance(value, dict) and len(value) > 0 or 
                         isinstance(value, list) and len(value) > 0 or
                         isinstance(value, str) and len(value) > 0):
                score += points
        
        return min(score, 100.0)
    
    def _calculate_goal_alignment(
        self,
        user_profile: Optional[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> float:
        """计算目标对齐度"""
        score = 40.0  # 基础分
        
        # 检查是否有用户目标
        if user_profile:
            fitness_goals = user_profile.get('fitness_goals', {})
            if isinstance(fitness_goals, dict):
                if fitness_goals.get('primary_goal'):
                    score += 20
                if fitness_goals.get('secondary_goals'):
                    score += 10
            
            # 检查健身配置中的目标
            fitness_config = user_profile.get('fitness_config', {})
            if isinstance(fitness_config, dict):
                if fitness_config.get('training_goal'):
                    score += 15
                if fitness_config.get('preferred_split_type'):
                    score += 10
        
        # 检查DAG模板是否匹配用户意图
        dag_template = metadata.get('dag_template_id', '')
        if dag_template in ['complete_training_plan', 'comprehensive_fitness', 'periodized_training']:
            score += 5
        
        return min(score, 100.0)
    
    def _calculate_uniqueness(
        self,
        tools_used: List[str],
        response_length: int
    ) -> float:
        """计算独特性"""
        score = 30.0  # 基础分
        
        # 检查是否使用了个性化工具
        personalization_tools = [
            'intelligent_exercise_selector',
            'contraindications_checker',
            'injury_risk_assessor',
            'safe_exercise_modifier',
            'professional_program_designer',
            'periodized_program_designer',
            'muscle_group_volume_calculator',
            'training_split_designer',
        ]
        
        tools_count = 0
        for tool in personalization_tools:
            if tool in tools_used:
                tools_count += 1
                score += 8  # 每个工具8分
        
        # 检查回复长度（更长的回复通常更个性化）
        if response_length > 2000:
            score += 15
        elif response_length > 1000:
            score += 10
        elif response_length > 500:
            score += 5
        
        return min(score, 100.0)
    
    def _calculate_dynamic_adjustment(
        self,
        metadata: Dict[str, Any]
    ) -> float:
        """计算动态调整"""
        score = 40.0  # 基础分
        
        # 检查是否有上下文引用
        if metadata.get('context_used'):
            score += 15
        
        # 检查是否是多轮对话
        conversation_turn = metadata.get('conversation_turn', 1)
        if conversation_turn > 1:
            score += min(conversation_turn * 5, 20)  # 最多20分
        
        # 检查Few-Shot数量（使用了历史案例）
        few_shot_count = metadata.get('few_shot_count', 0)
        if few_shot_count > 0:
            score += min(few_shot_count * 5, 15)  # 最多15分
        
        # 检查复杂度级别（复杂查询需要更多调整）
        complexity = metadata.get('complexity_level', 'simple')
        if complexity in ['complex', 'high']:
            score += 10
        elif complexity == 'medium':
            score += 5
        
        return min(score, 100.0)
    
    def calculate_personalization_grade(
        self,
        profile_utilization_rate: float
    ) -> PersonalizationGrade:
        """
        计算个性化等级
        
        Args:
            profile_utilization_rate: 档案利用率
            
        Returns:
            PersonalizationGrade: 个性化等级
        """
        if profile_utilization_rate >= 90:
            return PersonalizationGrade.S
        elif profile_utilization_rate >= 75:
            return PersonalizationGrade.A
        elif profile_utilization_rate >= 60:
            return PersonalizationGrade.B
        elif profile_utilization_rate >= 40:
            return PersonalizationGrade.C
        else:
            return PersonalizationGrade.D
    
    def check_fewshot_eligibility(
        self,
        personalization_scores: PersonalizationScores,
        user_session_count: int = 0,
        user_experience_avg: Optional[float] = None,
        expert_safety_score: Optional[int] = None
    ) -> tuple[bool, str]:
        """
        检查Few-Shot准入资格
        
        **重要**：必须三轨评分都存在才能导入Few-Shot库
        - 个性化感知评分（系统自动计算）
        - 用户体验评分（用户手动评分）
        - 专家安全性评分（专家审核）
        
        Args:
            personalization_scores: 个性化感知评分
            user_session_count: 用户会话数量（用于冷启动判断）
            user_experience_avg: 用户体验平均分（必须，5分制）
            expert_safety_score: 专家安全性评分（必须，5分制）
            
        Returns:
            tuple[bool, str]: (是否合格, 原因)
        """
        # 0. 检查三轨评分是否完整
        # 用户评分和专家评分必须存在才能导入Few-Shot
        if user_experience_avg is None:
            return False, "缺少用户体验评分，暂不导入Few-Shot"
        
        if expert_safety_score is None:
            return False, "缺少专家安全性评分，暂不导入Few-Shot"
        
        # 1. 安全性一票否决
        if expert_safety_score < 3:
            return False, "安全性评分过低（<3），一票否决"
        
        # 2. 冷启动期保护
        is_cold_start = user_session_count <= self.COLD_START_SESSION_COUNT
        threshold = self.COLD_START_THRESHOLD if is_cold_start else self.FEWSHOT_THRESHOLD
        
        # 3. 检查个性化感知评分
        personalization_avg = personalization_scores.average / 20  # 转换为5分制
        if personalization_avg < threshold:
            return False, f"个性化感知评分不足（{personalization_avg:.2f} < {threshold}）"
        
        # 4. 检查用户体验评分
        if user_experience_avg < threshold:
            return False, f"用户体验评分不足（{user_experience_avg:.2f} < {threshold}）"
        
        # 5. 通过所有检查
        if is_cold_start:
            return True, f"三轨评分均达标（冷启动期阈值{threshold}）"
        else:
            return True, "三轨评分均达标"
    
    async def process_rating(
        self,
        session_id: str,
        user_id: str,
        user_query: str,
        llm_response: str,
        user_profile: Optional[Dict[str, Any]],
        tools_used: List[str],
        metadata: Dict[str, Any]
    ) -> ThreeTrackRatingResult:
        """
        处理三轨评分（工作流最后一步）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            user_query: 用户查询
            llm_response: LLM回复
            user_profile: 用户档案
            tools_used: 使用的工具列表
            metadata: 元数据
            
        Returns:
            ThreeTrackRatingResult: 三轨评分结果
        """
        logger.info(f"🎯 开始处理三轨评分: session_id={session_id}")
        
        # 1. 计算个性化感知评分
        personalization = self.calculate_personalization_scores(
            user_profile=user_profile,
            tools_used=tools_used,
            metadata=metadata,
            response_length=len(llm_response) if llm_response else 0
        )
        
        # 2. 计算个性化等级
        grade = self.calculate_personalization_grade(
            personalization.profile_utilization_rate
        )
        
        # 3. 获取用户会话数量（用于冷启动判断）
        user_session_count = await self._get_user_session_count(user_id)
        
        # 4. 检查Few-Shot准入资格
        eligible, reason = self.check_fewshot_eligibility(
            personalization_scores=personalization,
            user_session_count=user_session_count
        )
        
        # 5. 构建结果
        result = ThreeTrackRatingResult(
            session_id=session_id,
            personalization=personalization,
            personalization_grade=grade,
            fewshot_eligible=eligible,
            eligibility_reason=reason,
            overall_score=personalization.average / 20  # 转换为5分制
        )
        
        logger.info(
            f"✅ 三轨评分完成: session_id={session_id}, "
            f"grade={grade.value}, eligible={eligible}, reason={reason}"
        )
        
        # 6. 如果符合条件，自动导入Few-Shot库
        if eligible:
            await self._import_to_fewshot_pool(
                session_id=session_id,
                user_query=user_query,
                llm_response=llm_response,
                tools_used=tools_used,
                personalization=personalization,
                grade=grade
            )
        
        return result
    
    async def _get_user_session_count(self, user_id: str) -> int:
        """获取用户会话数量"""
        if not self.backend_client:
            return 0
        
        try:
            # 调用后端API获取用户会话数量
            # 这里简化处理，实际应该调用后端API
            return 0
        except Exception as e:
            logger.warning(f"获取用户会话数量失败: {e}")
            return 0
    
    async def _import_to_fewshot_pool(
        self,
        session_id: str,
        user_query: str,
        llm_response: str,
        tools_used: List[str],
        personalization: PersonalizationScores,
        grade: PersonalizationGrade
    ) -> bool:
        """
        将高评分对话导入Few-Shot库
        
        Args:
            session_id: 会话ID
            user_query: 用户查询
            llm_response: LLM回复
            tools_used: 使用的工具列表
            personalization: 个性化感知评分
            grade: 个性化等级
            
        Returns:
            bool: 是否导入成功
        """
        try:
            logger.info(f"📥 开始导入Few-Shot库: session_id={session_id}")
            
            # 1. 获取BGE模型生成向量
            from ....framework.models.model_cache_manager import ModelCacheManager
            model_cache = ModelCacheManager.get_instance()
            bge_model = model_cache.get_bge_model("BAAI/bge-m3")
            
            if bge_model is None:
                logger.warning("BGE模型未加载，跳过Few-Shot导入")
                return False
            
            # 2. 准备文本并生成向量
            conversation_text = f"用户问题: {user_query}\n\n专业回答: {llm_response}"
            embedding = bge_model.encode(conversation_text, normalize_embeddings=True)
            
            # 3. 获取Qdrant客户端
            if not self.qdrant_client:
                from ....framework.clients.qdrant_client import create_qdrant_client
                self.qdrant_client = create_qdrant_client()
            
            # 4. 构建Few-Shot数据点
            from qdrant_client.models import PointStruct
            import uuid
            
            point_id = str(uuid.uuid4())
            effect_label = self._get_effect_label(personalization.average)
            
            point = PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    'session_id': session_id,
                    'query': user_query,
                    'response': llm_response,
                    'tools_used': tools_used,
                    'personalization_score': personalization.average,
                    'personalization_grade': grade.value,
                    'profile_utilization_rate': personalization.profile_utilization_rate,
                    'goal_alignment': personalization.goal_alignment,
                    'uniqueness': personalization.uniqueness,
                    'dynamic_adjustment': personalization.dynamic_adjustment,
                    'effect_label': effect_label,
                    'source': 'three_track_rating',
                    'fewshot_eligible': True
                }
            )
            
            # 5. 存储到Qdrant
            collection_name = "fitness_fewshot_pool"
            
            # 检查集合是否存在，不存在则创建
            try:
                collections = self.qdrant_client.get_collections()
                collection_names = [c.name for c in collections.collections]
                
                if collection_name not in collection_names:
                    from qdrant_client.models import VectorParams, Distance
                    self.qdrant_client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=1024,  # BGE-M3 向量维度
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"✅ 创建Few-Shot集合: {collection_name}")
            except Exception as e:
                logger.warning(f"检查/创建集合失败: {e}")
            
            # 6. 插入向量点
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(
                f"✅ Few-Shot导入成功: session_id={session_id}, "
                f"point_id={point_id}, grade={grade.value}"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Few-Shot导入失败: session_id={session_id}, error={e}")
            return False
    
    def _get_effect_label(self, score: float) -> str:
        """根据评分获取效果标签"""
        if score >= 90:
            return 'excellent'
        elif score >= 75:
            return 'good'
        elif score >= 60:
            return 'fair'
        else:
            return 'poor'


# ============ 便捷函数 ============

def create_three_track_rating_service(
    backend_client=None,
    qdrant_client=None
) -> ThreeTrackRatingService:
    """创建三轨评分服务实例"""
    return ThreeTrackRatingService(
        backend_client=backend_client,
        qdrant_client=qdrant_client
    )


# ============ 导出 ============

__all__ = [
    'ThreeTrackRatingService',
    'ThreeTrackRatingResult',
    'PersonalizationScores',
    'PersonalizationGrade',
    'create_three_track_rating_service',
]
