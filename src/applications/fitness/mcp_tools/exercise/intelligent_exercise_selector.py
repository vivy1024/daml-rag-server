"""
智能动作选择器 MCP工具

基于三层检索引擎的个性化动作推荐系统
参考TypeScript实现的业务逻辑和评分算法

功能特性：
- 使用三层检索引擎（Layer1向量检索 + Layer2图谱过滤 + Layer3规则验证）
- 基于Neo4j 34字段Exercise数据进行精准查询
- 支持肌群、器械、难度、目标、损伤史等条件过滤
- 使用SUITABLE_FOR_LEVEL关系进行精准难度筛选（v8.61.0新增）
- 使用HAS_MECHANIC关系筛选复合/单关节动作（v8.61.0新增）
- 返回完整的动作信息和安全建议
- 计算适配度评分和安全评分
- 支持中国健身房器械别名映射 - Requirements: 4.1, 4.2, 4.3
- 标准化三层检索调用 - Requirements: 17.1-17.6
- 版本管理 - Requirements: 12.1-12.5

作者: BUILD_BODY Team
版本: v2.1.0
日期: 2026-01-06
更新: 添加SUITABLE_FOR_LEVEL和HAS_MECHANIC关系支持
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from ..base_tool import BaseMCPTool, VersionInfo, ChangelogEntry
from ...services.equipment_alias_mapper import get_equipment_alias_mapper

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举类型定义（从权威来源导入）
# =============================================================================

from ...types.enums import TrainingGoal, DifficultyLevel


class MechanicType(str, Enum):
    """动作机制类型（与Neo4j MechanicType节点对应）"""
    COMPOUND = "compound"      # 复合动作
    ISOLATION = "isolation"    # 单关节动作


class SessionFocus(str, Enum):
    """训练重点"""
    COMPOUND = "compound"
    ISOLATION = "isolation"
    BALANCED = "balanced"


class SafetyLevel(str, Enum):
    """安全等级"""
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"


# =============================================================================
# 输入Schema定义
# =============================================================================

class IntelligentExerciseSelectorInput(BaseModel):
    """智能动作选择器输入Schema"""
    
    user_id: str = Field(..., description="用户ID，用于获取个人化条件")
    muscle_group: str = Field(..., description="目标肌群（如：胸、背、腿、肩、手臂、核心、臀部、小腿）")
    training_goal: TrainingGoal = Field(..., description="训练目标")
    difficulty_level: DifficultyLevel = Field(..., description="难度等级（novice/beginner/intermediate/advanced）")
    available_equipment: List[str] = Field(..., description="可用器械列表")
    injury_history: Optional[List[str]] = Field(None, description="损伤历史（可选）")
    exercise_preferences: Optional[List[str]] = Field(None, description="运动偏好（可选）")
    disliked_exercises: Optional[List[str]] = Field(None, description="不喜欢的动作（可选）")
    session_focus: Optional[SessionFocus] = Field(None, description="训练重点（可选）")
    
    # 新增参数 - Requirements 4.1, 4.2
    rehabilitation_phase: Optional[str] = Field(None, description="康复阶段（可选），用于动力链过滤")
    force_type: Optional[str] = Field(None, description="力类型过滤（可选）：push/pull/hold")
    postural_issues: Optional[List[str]] = Field(None, description="体态问题（可选），用于体态矫正过滤")
    
    # v8.61.0新增参数
    mechanic_type: Optional[MechanicType] = Field(None, description="动作机制类型（可选）：compound/isolation")


# =============================================================================
# 输出Schema定义
# =============================================================================

class ExerciseRecommendation(BaseModel):
    """单个动作推荐"""
    
    # 基础信息
    exercise_id: str
    name_zh: str
    name_en: str
    category: str
    difficulty: str
    safety_level: str
    
    # 肌肉信息（基于Neo4j关系）
    primary_muscles: List[str]
    secondary_muscles: List[str]
    muscle_groups: List[str]
    
    # 训练参数（基于31字段数据）
    equipment_zh: List[str]
    movement_pattern: Optional[str] = None
    force_type: Optional[str] = None
    mechanics: Optional[str] = None
    rep_range: Optional[str] = None
    set_range: Optional[str] = None
    rest_period: Optional[str] = None
    
    # 安全信息
    safety_warning_signs: List[str]
    contraindications_zh: List[str]
    injury_risk_factors: List[str]
    
    # 指导信息
    instructions_zh: Optional[str] = None
    common_mistakes_zh: List[str]
    progression_options: List[str]
    
    # 评分
    suitability_score: float
    safety_score: float
    reasoning: str


class IntelligentExerciseSelectorOutput(BaseModel):
    """智能动作选择器输出Schema"""
    
    success: bool
    tool_name: str
    query_params: Dict[str, Any]
    recommendations: List[ExerciseRecommendation]
    reasoning: str
    safety_alerts: List[str]
    total_found: int
    execution_time_ms: float
    confidence_score: float
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# 智能动作选择器类
# =============================================================================

class IntelligentExerciseSelector(BaseMCPTool):
    """
    智能动作选择器
    
    使用三层检索引擎进行个性化动作推荐：
    - Layer1: Qdrant向量检索（语义匹配候选动作）
    - Layer2: Neo4j图谱过滤（TARGETS/CONTRAINDICATED_FOR关系）
    - Layer3: Python规则验证（安全规则、用户限制）
    
    版本历史:
    - v2.0.0 (2026-01-06): 标准化三层检索调用，添加版本管理
    - v1.1.0 (2025-12-26): 添加康复阶段、力类型、体态问题过滤
    - v1.0.0 (2025-12-20): 初始版本
    """
    
    # 版本信息 - Requirements 12.1
    _version = VersionInfo(2, 0, 0)
    
    # 变更日志 - Requirements 12.2
    _changelog = [
        ChangelogEntry(
            version="2.0.0",
            date="2026-01-06",
            changes=[
                "标准化三层检索调用方法 (Requirements 17.1-17.6)",
                "添加版本管理功能 (Requirements 12.1-12.5)",
                "优化执行结果中的版本信息记录"
            ],
            breaking_changes=[]
        ),
        ChangelogEntry(
            version="1.1.0",
            date="2025-12-26",
            changes=[
                "添加 rehabilitation_phase 参数支持动力链过滤",
                "添加 force_type 参数支持力类型过滤",
                "添加 postural_issues 参数支持体态问题过滤"
            ],
            breaking_changes=[]
        ),
        ChangelogEntry(
            version="1.0.0",
            date="2025-12-20",
            changes=[
                "初始版本",
                "基于三层检索引擎的个性化动作推荐",
                "支持肌群、器械、难度、目标、损伤史等条件过滤"
            ],
            breaking_changes=[]
        )
    ]
    
    def get_name(self) -> str:
        return "intelligent_exercise_selector"
    
    def get_description(self) -> str:
        return "智能动作选择器 - 基于三层检索引擎的个性化推荐，支持肌群、器械、难度、目标、损伤史等条件过滤"
    
    def get_category(self) -> str:
        return "exercise"
    
    def get_input_schema(self) -> type[BaseModel]:
        return IntelligentExerciseSelectorInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return IntelligentExerciseSelectorOutput
    
    def get_complexity(self) -> str:
        return "complex"
    
    def get_estimated_duration(self) -> float:
        return 1500.0  # 1.5秒
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["neo4j", "qdrant", "three_layer_engine"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行智能动作选择
        
        流程：
        1. 获取用户档案（可选）
        2. 构建查询文本
        3. 调用三层检索引擎（使用标准化方法）
        4. 计算适配度和安全评分
        5. 生成推荐理由和安全提醒
        6. 返回排序后的推荐列表
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: 获取用户档案（优先从DAG注入的input_data获取）
            user_profile = input_data.get("user_profile") or await self._get_user_profile(input_data.get("user_id"))
            
            # Step 2: 构建查询文本
            query_text = self._build_query_text(input_data, user_profile)
            
            # Step 3: 调用三层检索引擎
            retrieval_result = await self._query_exercises_via_three_layer(
                query_text=query_text,
                input_data=input_data,
                user_profile=user_profile
            )
            
            # Step 4: 计算评分和排序
            recommendations = self._calculate_recommendations(
                retrieval_result,
                input_data,
                user_profile
            )
            
            # Step 5: 生成推荐理由和安全提醒
            reasoning = self._generate_reasoning(input_data, user_profile)
            safety_alerts = self._generate_safety_alerts(recommendations, user_profile)
            
            # Step 6: 返回结果
            execution_time_ms = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "tool_name": self.get_name(),
                "query_params": {
                    "muscle_group": input_data["muscle_group"],
                    "training_goal": input_data["training_goal"],
                    "difficulty_level": input_data["difficulty_level"],
                    "available_equipment": input_data["available_equipment"]
                },
                "recommendations": [r.model_dump() for r in recommendations[:10]],  # Top 10
                "reasoning": reasoning,
                "safety_alerts": safety_alerts,
                "total_found": len(recommendations),
                "execution_time_ms": execution_time_ms,
                "confidence_score": 92.0,
                "metadata": {
                    "query_text": query_text,
                    "user_profile_used": bool(user_profile)
                }
            }
            
        except Exception as e:
            self.logger.error(f"智能动作选择失败: {e}", exc_info=True)
            raise
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户档案（可选）
        
        TODO: 集成UserProfileClient
        """
        # 暂时返回空字典，后续集成UserProfileClient
        return {}
    
    def _build_query_text(
        self,
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """
        构建查询文本
        
        结合用户输入和档案信息生成自然语言查询
        
        注意：必须将枚举值转换为中文描述，否则向量检索会失败
        """
        parts = []
        
        # 难度等级映射（枚举值 -> 中文描述）
        difficulty_map = {
            "novice": "零基础",
            "beginner": "初级",
            "intermediate": "中级",
            "advanced": "高级",
            # 兼容枚举对象的字符串表示
            "DifficultyLevel.NOVICE": "零基础",
            "DifficultyLevel.BEGINNER": "初级",
            "DifficultyLevel.INTERMEDIATE": "中级",
            "DifficultyLevel.ADVANCED": "高级",
        }
        
        # 训练目标映射（枚举值 -> 中文描述）
        goal_map = {
            "strength": "力量",
            "hypertrophy": "增肌",
            "endurance": "耐力",
            "general_fitness": "综合健身",
            "fat_loss": "减脂塑形",
            "posture_correction": "体态矫正",
            "functional": "功能性",
            # 兼容枚举对象的字符串表示
            "TrainingGoal.STRENGTH": "力量",
            "TrainingGoal.HYPERTROPHY": "增肌",
            "TrainingGoal.ENDURANCE": "耐力",
            "TrainingGoal.GENERAL_FITNESS": "综合健身",
            "TrainingGoal.FAT_LOSS": "减脂塑形",
            "TrainingGoal.POSTURE_CORRECTION": "体态矫正",
            "TrainingGoal.FUNCTIONAL": "功能性",
        }
        
        # 获取难度等级的中文描述
        difficulty_raw = str(input_data['difficulty_level'])
        difficulty_zh = difficulty_map.get(difficulty_raw, difficulty_map.get(difficulty_raw.lower(), "中级"))
        
        # 获取训练目标的中文描述
        goal_raw = str(input_data['training_goal'])
        goal_zh = goal_map.get(goal_raw, goal_map.get(goal_raw.lower(), "综合健身"))
        
        # 基础查询（使用中文描述）
        parts.append(f"推荐适合{difficulty_zh}训练者的")
        parts.append(f"{input_data['muscle_group']}肌群")
        parts.append(f"{goal_zh}训练动作")
        
        # 器械条件
        if input_data.get("available_equipment"):
            equipment_str = "、".join(input_data["available_equipment"])
            parts.append(f"可用器械：{equipment_str}")
        
        # 损伤史
        if input_data.get("injury_history"):
            injury_str = "、".join(input_data["injury_history"])
            parts.append(f"需避免：{injury_str}")
        
        # 训练重点
        if input_data.get("session_focus"):
            focus_map = {
                "compound": "复合动作",
                "isolation": "孤立动作",
                "balanced": "平衡训练"
            }
            focus_text = focus_map.get(input_data["session_focus"], "")
            if focus_text:
                parts.append(f"重点：{focus_text}")
        
        return "，".join(parts)
    
    async def _query_exercises_via_three_layer(
        self,
        query_text: str,
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        通过三层检索引擎查询动作
        
        调用TrueThreeLayerEngine.execute_three_layer_query()
        支持新增的过滤参数：
        - rehabilitation_phase: 康复阶段（动力链过滤）
        - force_type: 力类型过滤
        - postural_issues: 体态问题过滤
        - mechanic_type: 动作机制类型过滤（v8.61.0新增）
        
        v8.61.0新增：使用SUITABLE_FOR_LEVEL和HAS_MECHANIC关系进行精准筛选
        """
        try:
            # 构建过滤条件
            filters = {
                "muscle_group": input_data["muscle_group"],
                "difficulty_level": input_data["difficulty_level"],
                "available_equipment": input_data["available_equipment"],
                "injury_history": input_data.get("injury_history", [])
            }
            
            # 新增过滤参数 - Requirements 4.1, 4.2
            if input_data.get("rehabilitation_phase"):
                filters["rehabilitation_phase"] = input_data["rehabilitation_phase"]
            
            if input_data.get("force_type"):
                filters["force_type"] = input_data["force_type"]
            
            if input_data.get("postural_issues"):
                filters["postural_issues"] = input_data["postural_issues"]
            
            # v8.61.0新增：动作机制类型过滤
            if input_data.get("mechanic_type"):
                filters["mechanic_type"] = input_data["mechanic_type"]
            
            # 调用三层检索引擎
            result = await self.three_layer_engine.execute_three_layer_query(
                query=query_text,
                domain="fitness_exercises",
                user_id=input_data.get("user_id"),
                user_profile=user_profile,
                filters=filters,
                top_k=50,  # Layer 1召回更多候选
                safety_check=True
            )
            
            # v8.61.0新增：使用Neo4j关系进行精准筛选
            filtered_results = await self._filter_by_neo4j_relations(
                result.final_results,
                input_data
            )
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"三层检索查询失败: {e}", exc_info=True)
            return []
    
    async def _filter_by_neo4j_relations(
        self,
        results: List[Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        使用Neo4j关系进行精准筛选（v8.61.0新增）
        
        利用以下关系：
        - SUITABLE_FOR_LEVEL: 筛选适合用户水平的动作
        - HAS_MECHANIC: 筛选复合/单关节动作
        """
        if not results:
            return results
        
        exercise_ids = [r.get("id") or r.get("exercise_id") for r in results if r.get("id") or r.get("exercise_id")]
        if not exercise_ids:
            return results
        
        difficulty_level = input_data.get("difficulty_level", "intermediate")
        mechanic_type = input_data.get("mechanic_type")
        session_focus = input_data.get("session_focus")
        
        # 构建Neo4j查询
        query_parts = ["MATCH (e:Exercise) WHERE e.id IN $exercise_ids"]
        params = {"exercise_ids": exercise_ids}
        
        # 使用SUITABLE_FOR_LEVEL关系筛选
        if difficulty_level:
            query_parts.append("""
            OPTIONAL MATCH (e)-[:SUITABLE_FOR_LEVEL]->(level:TrainingLevel {name: $difficulty_level})
            """)
            params["difficulty_level"] = difficulty_level
        
        # 使用HAS_MECHANIC关系筛选
        if mechanic_type:
            query_parts.append("""
            OPTIONAL MATCH (e)-[:HAS_MECHANIC]->(mech:MechanicType {name: $mechanic_type})
            """)
            params["mechanic_type"] = mechanic_type
        elif session_focus in ["compound", "isolation"]:
            # 如果指定了训练重点，也使用HAS_MECHANIC关系
            query_parts.append("""
            OPTIONAL MATCH (e)-[:HAS_MECHANIC]->(mech:MechanicType {name: $session_focus})
            """)
            params["session_focus"] = session_focus
        
        query_parts.append("""
        RETURN e.id as exercise_id,
               level IS NOT NULL as level_match,
               mech IS NOT NULL as mechanic_match
        """)
        
        query = "\n".join(query_parts)
        
        try:
            neo4j_results = await self.neo4j_client.execute_query(query, params)
            
            # 构建匹配映射
            match_map = {}
            for r in neo4j_results:
                exercise_id = r.get("exercise_id")
                if exercise_id:
                    match_map[exercise_id] = {
                        "level_match": r.get("level_match", False),
                        "mechanic_match": r.get("mechanic_match", False)
                    }
            
            # 根据匹配结果调整排序
            def sort_key(result):
                exercise_id = result.get("id") or result.get("exercise_id")
                match_info = match_map.get(exercise_id, {})
                score = 0
                if match_info.get("level_match"):
                    score += 2  # 水平匹配加2分
                if match_info.get("mechanic_match"):
                    score += 1  # 机制匹配加1分
                return -score  # 负数使得高分排前面
            
            results.sort(key=sort_key)
            return results
            
        except Exception as e:
            self.logger.warning(f"Neo4j关系筛选失败，返回原始结果: {e}")
            return results
    
    def _calculate_recommendations(
        self,
        results: List[Dict[str, Any]],
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> List[ExerciseRecommendation]:
        """
        计算推荐评分
        
        参考TypeScript的calculateSuitabilityScore()和calculateSafetyScore()
        """
        recommendations = []
        
        for result in results:
            # 计算适配度评分
            suitability_score = self._calculate_suitability_score(
                result, input_data, user_profile
            )
            
            # 计算安全评分
            safety_score = self._calculate_safety_score(
                result, input_data, user_profile
            )
            
            # 生成推荐理由
            reasoning = self._generate_exercise_reasoning(
                result, input_data, suitability_score, safety_score
            )
            
            # 构建推荐对象 - 处理None值，提供默认值
            name_en = result.get("name_en", result.get("exercise_name_en"))
            if name_en is None:
                name_en = ""  # 默认空字符串
            
            equipment_zh = result.get("equipment_zh", result.get("equipment"))
            if equipment_zh is None:
                equipment_zh = []  # 默认空列表
            elif isinstance(equipment_zh, str):
                equipment_zh = [equipment_zh]  # 字符串转列表
            
            recommendation = ExerciseRecommendation(
                exercise_id=result.get("exercise_id") or result.get("id") or "",
                name_zh=result.get("name_zh") or "",
                name_en=name_en,
                category=result.get("category") or "",
                difficulty=result.get("difficulty_zh") or result.get("difficulty_en") or "",
                safety_level=result.get("safety_level") or "MEDIUM_RISK",
                primary_muscles=result.get("muscles_primary_zh") or result.get("primary_muscles") or [],
                secondary_muscles=result.get("muscles_secondary_zh") or result.get("secondary_muscles") or [],
                muscle_groups=result.get("all_muscles_zh") or result.get("muscle_groups") or [],
                equipment_zh=equipment_zh,
                movement_pattern=result.get("mechanic_zh") or result.get("movement_pattern"),
                force_type=result.get("force_zh") or result.get("force_type"),
                mechanics=result.get("mechanic_zh") or result.get("mechanics"),
                rep_range=result.get("rep_range"),
                set_range=result.get("set_range"),
                rest_period=result.get("rest_period"),
                safety_warning_signs=result.get("safety_warning_signs") or [],
                contraindications_zh=result.get("contraindications_zh") or [],
                injury_risk_factors=result.get("injury_risk_factors") or [],
                instructions_zh=result.get("description_zh") or result.get("instructions_zh"),
                common_mistakes_zh=result.get("common_mistakes_zh") or [],
                progression_options=result.get("progression_options") or [],
                suitability_score=suitability_score,
                safety_score=safety_score,
                reasoning=reasoning
            )
            
            recommendations.append(recommendation)
        
        # 按综合评分排序
        recommendations.sort(
            key=lambda x: (x.suitability_score + x.safety_score) / 2,
            reverse=True
        )
        
        return recommendations
    
    def _calculate_suitability_score(
        self,
        exercise: Dict[str, Any],
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> float:
        """
        计算适配度评分
        
        参考TypeScript实现的评分算法
        支持中国本地化扩展目标 - Requirements 3.1, 3.2, 3.3
        支持中国健身房器械别名映射 - Requirements 4.1, 4.2, 4.3
        字段名已与统一数据结构对齐（v2.1.0）
        """
        score = 50.0  # 基础分
        
        # 基于训练目标调整 - 使用统一字段名
        training_goal = input_data["training_goal"]
        force_type = exercise.get("force_zh") or exercise.get("force_en") or ""
        name_zh = exercise.get("name_zh") or ""
        mechanics = exercise.get("mechanic_zh") or exercise.get("mechanic_en") or ""
        category = exercise.get("category") or ""
        
        if training_goal == "strength":
            if "推" in force_type or "力量" in name_zh:
                score += 20
        elif training_goal == "hypertrophy":
            score += 15
        elif training_goal == "endurance":
            score += 10
        # 中国本地化扩展目标 - Requirements 3.1, 3.2, 3.3
        elif training_goal == "fat_loss":
            # 减脂塑形：优先高代谢动作 - Requirements 3.1
            if "复合" in mechanics or "compound" in mechanics.lower():
                score += 20  # 复合动作消耗更多热量
            elif "有氧" in category or "cardio" in category.lower():
                score += 15
            else:
                score += 10
        elif training_goal == "posture_correction":
            # 体态矫正：优先稳定性和核心动作 - Requirements 3.2
            if "核心" in name_zh or "稳定" in name_zh or "平衡" in name_zh:
                score += 20
            elif "拉" in force_type:  # 拉类动作有助于改善圆肩
                score += 15
            else:
                score += 10
        elif training_goal == "functional":
            # 功能性训练：优先多关节复合动作 - Requirements 3.3
            if "复合" in mechanics or "compound" in mechanics.lower():
                score += 20
            elif "爆发" in name_zh or "跳" in name_zh:
                score += 15
            else:
                score += 10
        
        # 基于器械可用性 - 使用器械别名映射 Requirements 4.1, 4.2, 4.3
        equipment_mapper = get_equipment_alias_mapper()
        
        # 将用户输入的中文器械名称映射到英文
        available_equipment_chinese = input_data["available_equipment"]
        available_equipment_english = set(
            equipment_mapper.map_list_to_english(available_equipment_chinese)
        )
        # 同时保留中文名称用于直接匹配
        available_equipment_all = available_equipment_english | set(available_equipment_chinese)
        
        exercise_equipment = exercise.get("equipment_zh") or exercise.get("equipment") or []
        if isinstance(exercise_equipment, str):
            exercise_equipment = [exercise_equipment]
        
        # 将动作器械也映射到英文
        exercise_equipment_english = set(
            equipment_mapper.map_list_to_english(exercise_equipment)
        ) if exercise_equipment else set()
        exercise_equipment_all = exercise_equipment_english | set(exercise_equipment) if exercise_equipment else set()
        
        # 检查器械匹配（支持中英文混合匹配）
        if exercise_equipment_all.issubset(available_equipment_all):
            score += 20
        elif exercise_equipment_all & available_equipment_all:  # 部分匹配
            score += 10
        elif not exercise_equipment:  # 无器械要求（自重训练）
            score += 15
        
        # 基于用户偏好
        if user_profile and user_profile.get("exercise_preferences"):
            preferences = user_profile["exercise_preferences"]
            movement_pattern = exercise.get("movement_pattern", exercise.get("movement_pattern_zh", ""))
            if movement_pattern in preferences:
                score += 10
        
        # 避免用户不喜欢的动作
        disliked = input_data.get("disliked_exercises") or []
        exercise_id = exercise.get("exercise_id", exercise.get("id", ""))
        if disliked and exercise_id in disliked:
            score -= 30
        
        return min(100.0, max(0.0, score))
    
    def _calculate_safety_score(
        self,
        exercise: Dict[str, Any],
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> float:
        """
        计算安全评分
        
        参考TypeScript实现的评分算法
        字段名已与统一数据结构对齐（v2.1.0）
        """
        score = 100.0  # 基础分
        
        # 基于安全等级
        safety_level = exercise.get("safety_level", "MEDIUM_RISK")
        if safety_level == "HIGH_RISK":
            score -= 40
        elif safety_level == "MEDIUM_RISK":
            score -= 20
        
        # 基于用户损伤史
        injury_history = input_data.get("injury_history", [])
        contraindications = exercise.get("contraindications_zh", [])
        
        if injury_history and contraindications:
            # 检查是否有匹配的禁忌症
            matching_contraindications = len(set(injury_history) & set(contraindications))
            score -= matching_contraindications * 10
        
        # 基于难度等级（新手应避免高难度）
        if input_data["difficulty_level"] == "beginner":
            # 使用统一字段名：difficulty_zh（中文）或 difficulty_en（英文）
            difficulty_zh = exercise.get("difficulty_zh") or ""
            difficulty_en = exercise.get("difficulty_en") or ""
            
            # 检查中文难度
            if difficulty_zh and ("高级" in difficulty_zh or "进阶" in difficulty_zh):
                score -= 20
            # 检查英文难度
            elif difficulty_en and "advanced" in difficulty_en.lower():
                score -= 20
        
        return min(100.0, max(0.0, score))
    
    def _generate_exercise_reasoning(
        self,
        exercise: Dict[str, Any],
        input_data: Dict[str, Any],
        suitability_score: float,
        safety_score: float
    ) -> str:
        """生成单个动作的推荐理由"""
        reasons = []
        
        # 肌群匹配
        reasons.append(f"针对{input_data['muscle_group']}肌群")
        
        # 难度匹配
        reasons.append(f"适合{input_data['difficulty_level']}难度")
        
        # 安全性
        safety_level = exercise.get("safety_level", "MEDIUM_RISK")
        if safety_level == "LOW_RISK":
            reasons.append("安全性高")
        elif safety_level == "HIGH_RISK":
            reasons.append("需要专业指导")
        
        # 评分
        avg_score = (suitability_score + safety_score) / 2
        if avg_score >= 80:
            reasons.append("强烈推荐")
        elif avg_score >= 60:
            reasons.append("推荐")
        
        return "；".join(reasons)
    
    def _generate_reasoning(
        self,
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """生成整体推荐理由"""
        reasons = []
        
        reasons.append(f"针对{input_data['muscle_group']}肌群进行训练")
        reasons.append(f"满足{input_data['training_goal']}训练目标")
        reasons.append(f"适合{input_data['difficulty_level']}难度等级")
        
        if user_profile and user_profile.get("training_level"):
            reasons.append(f"匹配用户训练水平：{user_profile['training_level']}")
        
        if input_data.get("injury_history"):
            reasons.append("已考虑用户损伤史，避免高风险动作")
        
        return "；".join(reasons)
    
    def _generate_safety_alerts(
        self,
        recommendations: List[ExerciseRecommendation],
        user_profile: Dict[str, Any]
    ) -> List[str]:
        """生成安全提醒"""
        alerts = []
        
        # 基于推荐结果生成提醒
        high_risk_count = sum(
            1 for r in recommendations if r.safety_level == "HIGH_RISK"
        )
        if high_risk_count > 0:
            alerts.append(
                f"注意：推荐列表中包含{high_risk_count}个高风险动作，"
                "建议在专业人士指导下进行"
            )
        
        # 基于用户档案生成提醒
        if user_profile and user_profile.get("injury_history"):
            alerts.append("请密切关注训练过程中的身体反应，如有不适立即停止")
        
        if user_profile and user_profile.get("training_level") == "beginner":
            alerts.append("新手建议从轻重量开始，重视动作质量而非训练强度")
        
        return alerts
