"""
动作替代品查找器 - MCP工具

基于动作特性和用户条件智能查找替代动作
提供多维度匹配和个性化推荐
支持中国健身房器械别名映射 - Requirements: 4.1, 4.2, 4.3
使用USES_GRIP关系进行握法匹配（v8.61.0新增）

作者: BUILD_BODY Team
版本: v2.3.0
参考TypeScript实现
更新: 2026-01-06 - 添加USES_GRIP关系支持
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import time

from ..base_tool import BaseMCPTool
from ...services.equipment_alias_mapper import get_equipment_alias_mapper


# ===========================================================================
# Schema定义
# ===========================================================================

class AlternativeConstraints(BaseModel):
    """替代条件"""
    available_equipment: Optional[List[str]] = Field(None, description="可用器械")
    injury_limitations: Optional[List[str]] = Field(None, description="损伤限制")
    skill_level: Optional[Literal["beginner", "intermediate", "advanced"]] = Field(None, description="技能水平")
    space_limitations: Optional[List[str]] = Field(None, description="空间限制")


class ExerciseAlternativeFinderInput(BaseModel):
    """输入Schema"""
    user_id: str = Field(..., description="用户ID")
    original_exercise_id: str = Field(..., description="原动作ID")
    reason: Literal["injury", "equipment_unavailable", "difficulty_too_high", "preference_change", "variety"] = Field(
        ..., description="寻找替代原因"
    )
    constraints: Optional[AlternativeConstraints] = Field(None, description="替代条件")


class AlternativeExercise(BaseModel):
    """单个替代动作"""
    exercise_id: str
    name_zh: str
    name_en: str
    similarity_score: float
    match_reasons: List[str]
    adjustments_needed: List[str]
    difficulty_level: str
    equipment_needed: List[str]
    target_muscles: List[str]


class ExerciseAlternativeFinderOutput(BaseModel):
    """输出Schema"""
    success: bool
    tool_name: str
    alternatives: List[AlternativeExercise]
    selection_rationale: str
    usage_guidelines: List[str]
    progression_path: List[str]
    execution_time_ms: float
    confidence_score: Optional[float] = None


# ===========================================================================
# 工具实现
# ===========================================================================

class ExerciseAlternativeFinder(BaseMCPTool):
    """动作替代品查找器"""
    
    def get_name(self) -> str:
        return "exercise_alternative_finder"
    
    def get_description(self) -> str:
        return "动作替代品查找器 - 基于动作特性和用户条件智能查找替代动作，支持损伤、器械、难度等多种替代场景"
    
    def get_category(self) -> str:
        return "exercise"
    
    def get_input_schema(self) -> type[BaseModel]:
        return ExerciseAlternativeFinderInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return ExerciseAlternativeFinderOutput
    
    def get_complexity(self) -> str:
        return "medium"
    
    def get_estimated_duration(self) -> float:
        return 800.0  # 0.8秒
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["neo4j", "user_profile_mcp"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行动作替代品查找
        
        流程：
        1. 获取原动作信息
        2. 根据原因和约束条件查找替代动作
        3. 计算相似度评分
        4. 生成匹配原因和调整建议
        5. 返回排序后的替代方案
        """
        start_time = time.time()
        
        try:
            user_id = input_data.get("user_id")
            original_exercise_id = input_data.get("original_exercise_id")
            reason = input_data.get("reason")
            constraints = input_data.get("constraints", {})
            
            # 1. 获取原动作信息
            original_exercise = await self._get_exercise_info(original_exercise_id)
            
            if not original_exercise:
                return {
                    "success": False,
                    "tool_name": self.get_name(),
                    "alternatives": [],
                    "selection_rationale": f"未找到原动作: {original_exercise_id}",
                    "usage_guidelines": ["请检查动作ID是否正确"],
                    "progression_path": [],
                    "execution_time_ms": (time.time() - start_time) * 1000,
                    "confidence_score": 0
                }
            
            # 2. 查找替代动作
            alternatives = await self._find_alternatives(
                original_exercise,
                reason,
                constraints
            )
            
            # 3. 生成选择依据
            selection_rationale = self._generate_selection_rationale(reason, constraints)
            
            # 4. 生成使用指南
            usage_guidelines = self._generate_usage_guidelines(reason, constraints)
            
            # 5. 生成进阶路径
            progression_path = self._generate_progression_path(original_exercise_id, alternatives)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            self.logger.info(
                f"✅ 动作替代品查找完成 - 原动作: {original_exercise_id}, "
                f"找到 {len(alternatives)} 个替代方案 ({execution_time_ms:.2f}ms)"
            )
            
            return {
                "success": True,
                "tool_name": self.get_name(),
                "alternatives": alternatives,
                "selection_rationale": selection_rationale,
                "usage_guidelines": usage_guidelines,
                "progression_path": progression_path,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 85
            }
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"❌ 动作替代品查找执行失败: {e}", exc_info=True)
            
            return {
                "success": False,
                "tool_name": self.get_name(),
                "alternatives": [],
                "selection_rationale": "查找过程中发生错误",
                "usage_guidelines": ["请检查输入参数"],
                "progression_path": [],
                "execution_time_ms": execution_time_ms,
                "confidence_score": 0
            }
    
    async def _get_exercise_info(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """
        获取原动作信息（v8.61.0增强 - 使用USES_GRIP关系）
        
        注意：由于数据库中TARGETS关系缺失，使用primary_muscle_zh字段作为目标肌群
        v8.61.0新增：使用USES_GRIP关系获取握法信息
        """
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        OPTIONAL MATCH (e)-[:USES_GRIP]->(g:GripType)
        RETURN e, collect(DISTINCT g.name) as grip_types
        """
        
        try:
            # 将exercise_id转换为整数
            exercise_id_int = int(exercise_id) if isinstance(exercise_id, str) else exercise_id
            results = await self.neo4j_client.execute_query(query, {"exercise_id": exercise_id_int})
            if results:
                result = results[0]
                exercise = dict(result["e"])
                # 使用primary_muscle_zh字段作为目标肌群
                primary_muscle = exercise.get("primary_muscle_zh", "")
                exercise["target_muscles"] = [primary_muscle] if primary_muscle else []
                # v8.61.0新增：从USES_GRIP关系获取握法
                grip_types = result.get("grip_types", [])
                exercise["grips"] = [g for g in grip_types if g]  # 过滤None值
                return exercise
            return None
        except Exception as e:
            self.logger.error(f"获取动作信息失败: {e}")
            return None

    
    async def _find_alternatives(
        self,
        original_exercise: Dict[str, Any],
        reason: str,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        查找替代动作
        
        使用三层检索：
        - Layer1: 向量检索（语义匹配）
        - Layer2: Neo4j图谱过滤（关系查询）
        - Layer3: Python规则验证（安全保障）
        """
        # 1. 分析原动作特性
        original_characteristics = self._analyze_exercise_characteristics(original_exercise)
        
        # 2. 构建查询文本（用于向量检索）
        query_text = self._build_query_text(original_exercise, reason, constraints)
        
        # 3. 使用三层检索查找候选动作
        candidates = await self._query_via_three_layer(
            query_text,
            original_characteristics,
            reason,
            constraints
        )
        
        # 4. 计算相似度评分
        scored_candidates = []
        for candidate in candidates:
            similarity_score = self._calculate_similarity(
                original_characteristics,
                candidate
            )
            
            if similarity_score > 0.3:  # 相似度阈值（降低以适应数据库字段）
                scored_candidates.append({
                    **candidate,
                    "similarity_score": round(similarity_score, 2)
                })
        
        # 5. 排序并取前5个
        scored_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_candidates = scored_candidates[:5]
        
        # 6. 生成匹配原因和调整建议
        alternatives = []
        for candidate in top_candidates:
            # 使用统一字段名
            difficulty = candidate.get("difficulty_zh") or candidate.get("difficulty_en") or "intermediate"
            equipment = candidate.get("equipment_zh") or []
            if isinstance(equipment, str):
                equipment = [equipment]
            
            alternatives.append({
                "exercise_id": candidate.get("id") or "",
                "name_zh": candidate.get("name_zh") or "",
                "name_en": candidate.get("name_en") or "",
                "similarity_score": candidate["similarity_score"],
                "match_reasons": self._generate_match_reasons(
                    original_characteristics,
                    candidate
                ),
                "adjustments_needed": self._generate_adjustments(
                    original_characteristics,
                    candidate,
                    constraints
                ),
                "difficulty_level": difficulty,
                "equipment_needed": equipment,
                "target_muscles": candidate.get("target_muscles") or []
            })
        
        return alternatives
    
    def _analyze_exercise_characteristics(self, exercise: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析动作特性
        字段名已与统一数据结构对齐（v2.3.0）
        """
        return {
            "id": exercise.get("id"),
            "movement_pattern": exercise.get("mechanic_zh") or exercise.get("mechanic_en") or "",
            "target_muscles": exercise.get("target_muscles") or [],
            "equipment_type": exercise.get("equipment_zh") or [],
            "difficulty_level": exercise.get("difficulty_zh") or exercise.get("difficulty_en") or "intermediate",
            "force_type": exercise.get("force_zh") or exercise.get("force_en") or "",
            "mechanic": exercise.get("mechanic_zh") or exercise.get("mechanic_en") or "",
            "grips": exercise.get("grips_zh") or []  # v8.61.0新增：握法信息
        }
    
    def _build_query_text(
        self,
        original_exercise: Dict[str, Any],
        reason: str,
        constraints: Dict[str, Any]
    ) -> str:
        """
        构建查询文本（用于向量检索）
        字段名已与统一数据结构对齐（v2.3.0）
        """
        parts = []
        
        # 基础描述
        name_zh = original_exercise.get("name_zh") or ""
        parts.append(f"寻找与{name_zh}相似的替代动作")
        
        # 目标肌群
        target_muscles = original_exercise.get("target_muscles") or []
        if target_muscles:
            muscles_str = "、".join(target_muscles)
            parts.append(f"目标肌群：{muscles_str}")
        
        # 运动模式 - 使用统一字段名 mechanic_zh
        movement_pattern = original_exercise.get("mechanic_zh") or original_exercise.get("mechanic_en") or ""
        if movement_pattern:
            parts.append(f"运动模式：{movement_pattern}")
        
        # 根据原因添加约束
        if reason == "injury" and constraints.get("injury_limitations"):
            injury_str = "、".join(constraints["injury_limitations"])
            parts.append(f"需避免：{injury_str}")
        
        if reason == "equipment_unavailable" and constraints.get("available_equipment"):
            equipment_str = "、".join(constraints["available_equipment"])
            parts.append(f"可用器械：{equipment_str}")
        
        if reason == "difficulty_too_high":
            parts.append("需要更简单的动作")
        
        return "，".join(parts)
    
    async def _query_via_three_layer(
        self,
        query_text: str,
        original_characteristics: Dict[str, Any],
        reason: str,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """通过三层检索查询替代动作"""
        try:
            # 如果有三层检索引擎，使用它
            if hasattr(self, 'three_layer_engine') and self.three_layer_engine:
                result = await self.three_layer_engine.retrieve(
                    query_text=query_text,
                    top_k=20,
                    filters={
                        "reason": reason,
                        "constraints": constraints
                    }
                )
                return result.get("exercises", [])
            else:
                # 降级方案：直接从Neo4j查询
                return await self._query_from_neo4j(
                    original_characteristics,
                    reason,
                    constraints
                )
        except Exception as e:
            self.logger.warning(f"三层检索失败，使用降级方案: {e}")
            return await self._query_from_neo4j(
                original_characteristics,
                reason,
                constraints
            )
    
    async def _query_from_neo4j(
        self,
        original_characteristics: Dict[str, Any],
        reason: str,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从Neo4j直接查询（改进版 - 优先使用VARIATION_OF关系）
        
        Requirements: 4.4 - 优先使用VARIATION_OF关系查找替代动作
        
        查询策略：
        1. 首先查询VARIATION_OF关系（直接变式）
        2. 如果结果不足，再使用相似度匹配
        3. 对于器械限制和损伤限制，不放宽条件（安全优先）
        """
        # 步骤1: 优先查询VARIATION_OF关系 - Requirements 4.4
        variation_results = await self._query_by_variation_of(
            original_characteristics,
            reason,
            constraints
        )
        
        if len(variation_results) >= 3:
            self.logger.info(f"✅ 通过VARIATION_OF关系找到{len(variation_results)}个替代动作")
            return variation_results
        
        self.logger.info(f"VARIATION_OF关系仅返回{len(variation_results)}个结果，继续相似度匹配...")
        
        # 步骤2: 严格条件查询
        strict_results = await self._query_strict(original_characteristics, reason, constraints)
        
        # 合并结果（VARIATION_OF优先）
        all_results = variation_results + [
            r for r in strict_results 
            if r.get("id") not in [v.get("id") for v in variation_results]
        ]
        
        if len(all_results) >= 3:
            return all_results
        
        # 对于器械限制和损伤限制，不放宽条件（安全优先）
        if reason in ["equipment_unavailable", "injury"]:
            self.logger.warning(f"器械/损伤限制场景仅返回{len(all_results)}个结果，不放宽条件（安全优先）")
            return all_results
        
        self.logger.info(f"严格查询仅返回{len(all_results)}个结果，尝试放宽条件...")
        
        # 步骤3: 放宽到同力学特性
        mechanic_results = await self._query_by_mechanic(original_characteristics, reason, constraints)
        
        # 合并结果
        all_results = all_results + [
            r for r in mechanic_results 
            if r.get("id") not in [v.get("id") for v in all_results]
        ]
        
        if len(all_results) >= 3:
            return all_results
        
        self.logger.info(f"力学特性查询仅返回{len(all_results)}个结果，进一步放宽...")
        
        # 步骤4: 放宽到同力量类型
        force_results = await self._query_by_force(original_characteristics, reason, constraints)
        
        # 合并结果
        all_results = all_results + [
            r for r in force_results 
            if r.get("id") not in [v.get("id") for v in all_results]
        ]
        
        return all_results
    
    async def _query_by_variation_of(
        self,
        original_characteristics: Dict[str, Any],
        reason: str,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        通过VARIATION_OF关系查询替代动作
        
        Requirements: 4.4 - 优先使用VARIATION_OF关系
        
        查询逻辑：
        1. 查找原动作的所有变式（VARIATION_OF关系）
        2. 应用约束条件过滤
        3. 返回符合条件的变式动作
        """
        original_id = original_characteristics.get("id")
        if not original_id:
            return []
        
        where_clauses = []
        params = {"original_id": original_id}
        
        # 根据原因添加过滤条件
        if reason == "equipment_unavailable" and constraints.get("available_equipment"):
            # 使用器械别名映射
            equipment_mapper = get_equipment_alias_mapper()
            available_equipment_chinese = constraints["available_equipment"]
            available_equipment_all = list(set(
                available_equipment_chinese + 
                equipment_mapper.map_list_to_english(available_equipment_chinese)
            ))
            
            where_clauses.append("ANY(eq IN v.equipment_zh WHERE eq IN $available_equipment)")
            params["available_equipment"] = available_equipment_all
        
        if reason == "difficulty_too_high":
            difficulty_map = {"高级": ["中级", "初级", "零基础"], "中级": ["初级", "零基础"], "初级": ["零基础"], "零基础": []}
            easier_levels = difficulty_map.get(original_characteristics.get("difficulty_level", "中级"), ["初级", "零基础"])
            where_clauses.append("v.difficulty_zh IN $easier_levels")
            params["easier_levels"] = easier_levels
        
        if constraints.get("skill_level") == "beginner":
            where_clauses.append("v.difficulty_zh IN ['零基础', '初级']")
        
        where_clause = " AND " + " AND ".join(where_clauses) if where_clauses else ""
        
        # 查询VARIATION_OF关系（双向）
        query = f"""
        MATCH (e:Exercise {{id: $original_id}})
        MATCH (e)-[:VARIATION_OF]-(v:Exercise)
        WHERE v.id <> $original_id{where_clause}
        RETURN v
        LIMIT 10
        """
        
        try:
            results = await self.neo4j_client.execute_query(query, params)
            exercises = []
            for result in results:
                exercise = dict(result["v"])
                # 使用primary_muscle_zh作为目标肌群
                primary_muscle = exercise.get("primary_muscle_zh", "")
                exercise["target_muscles"] = [primary_muscle] if primary_muscle else []
                # 标记为VARIATION_OF来源
                exercise["source"] = "VARIATION_OF"
                exercises.append(exercise)
            
            self.logger.info(f"✅ 通过VARIATION_OF关系找到{len(exercises)}个变式动作")
            return exercises
        except Exception as e:
            self.logger.error(f"VARIATION_OF关系查询失败: {e}")
            return []
    
    async def _query_strict(
        self,
        original_characteristics: Dict[str, Any],
        reason: str,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        严格条件查询
        
        注意：由于TARGETS关系缺失，使用primary_muscle_zh字段进行肌群匹配
        支持中国健身房器械别名映射 - Requirements: 4.1, 4.2, 4.3
        """
        where_clauses = []
        params = {}
        
        # 基础条件：同肌群（使用primary_muscle_zh字段）
        target_muscles = original_characteristics.get("target_muscles", [])
        if target_muscles and target_muscles[0]:  # 确保有有效的肌群
            where_clauses.append("e.primary_muscle_zh = $primary_muscle")
            params["primary_muscle"] = target_muscles[0]
        
        # 根据原因添加过滤条件
        if reason == "equipment_unavailable" and constraints.get("available_equipment"):
            # 使用器械别名映射将中文器械名称转换为英文
            equipment_mapper = get_equipment_alias_mapper()
            available_equipment_chinese = constraints["available_equipment"]
            # 同时保留中文和英文名称用于匹配
            available_equipment_all = list(set(
                available_equipment_chinese + 
                equipment_mapper.map_list_to_english(available_equipment_chinese)
            ))
            
            # equipment_zh是数组，需要检查数组中的任何元素是否在可用器械列表中
            where_clauses.append("ANY(eq IN e.equipment_zh WHERE eq IN $available_equipment)")
            params["available_equipment"] = available_equipment_all
        
        if reason == "difficulty_too_high":
            difficulty_map = {"高级": ["中级", "初级", "零基础"], "中级": ["初级", "零基础"], "初级": ["零基础"], "零基础": []}
            easier_levels = difficulty_map.get(original_characteristics.get("difficulty_level", "中级"), ["初级", "零基础"])
            where_clauses.append("e.difficulty_zh IN $easier_levels")
            params["easier_levels"] = easier_levels
        
        if constraints.get("skill_level") == "beginner":
            where_clauses.append("e.difficulty_zh IN ['零基础', '初级']")
        
        # 排除原动作
        original_id = original_characteristics.get("id")
        if original_id:
            where_clauses.append("e.id <> $original_id")
            params["original_id"] = original_id
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
        MATCH (e:Exercise)
        WHERE {where_clause}
        RETURN e
        LIMIT 20
        """
        
        try:
            results = await self.neo4j_client.execute_query(query, params)
            exercises = []
            for result in results:
                exercise = dict(result["e"])
                # 使用primary_muscle_zh作为目标肌群
                primary_muscle = exercise.get("primary_muscle_zh", "")
                exercise["target_muscles"] = [primary_muscle] if primary_muscle else []
                exercises.append(exercise)
            return exercises
        except Exception as e:
            self.logger.error(f"严格查询失败: {e}")
            return []
    
    async def _query_by_mechanic(
        self,
        original_characteristics: Dict[str, Any],
        reason: str,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        基于力学特性查询（更宽松）
        
        注意：由于TARGETS关系缺失，使用primary_muscle_zh字段
        """
        where_clauses = []
        params = {}
        
        # 同力学特性（使用统一字段名mechanic_zh）
        mechanic = original_characteristics.get("mechanic") or original_characteristics.get("mechanic_zh")
        if mechanic:
            where_clauses.append("e.mechanic_zh = $mechanic")
            params["mechanic"] = mechanic
        
        # 添加器械或难度条件（使用统一字段名）
        if reason == "equipment_unavailable" and constraints.get("available_equipment"):
            where_clauses.append("e.equipment_zh IN $available_equipment")
            params["available_equipment"] = constraints["available_equipment"]
        elif reason == "difficulty_too_high":
            where_clauses.append("e.difficulty_zh IN ['零基础', '初级', '中级']")
        
        # 排除原动作
        original_id = original_characteristics.get("id")
        if original_id:
            where_clauses.append("e.id <> $original_id")
            params["original_id"] = original_id
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
        MATCH (e:Exercise)
        WHERE {where_clause}
        RETURN e
        LIMIT 20
        """
        
        try:
            results = await self.neo4j_client.execute_query(query, params)
            exercises = []
            for result in results:
                exercise = dict(result["e"])
                # 使用primary_muscle_zh作为目标肌群
                primary_muscle = exercise.get("primary_muscle_zh", "")
                exercise["target_muscles"] = [primary_muscle] if primary_muscle else []
                exercises.append(exercise)
            return exercises
        except Exception as e:
            self.logger.error(f"力学特性查询失败: {e}")
            return []
    
    async def _query_by_force(
        self,
        original_characteristics: Dict[str, Any],
        reason: str,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        基于力量类型查询（最宽松）
        
        注意：由于TARGETS关系缺失，使用primary_muscle_zh字段
        """
        where_clauses = []
        params = {}
        
        # 同力量类型（使用统一字段名force_zh）
        force_type = original_characteristics.get("force_type") or original_characteristics.get("force_zh")
        if force_type:
            where_clauses.append("e.force_zh = $force_type")
            params["force_type"] = force_type
        
        # 排除原动作
        original_id = original_characteristics.get("id")
        if original_id:
            where_clauses.append("e.id <> $original_id")
            params["original_id"] = original_id
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
        MATCH (e:Exercise)
        WHERE {where_clause}
        RETURN e
        LIMIT 20
        """
        
        try:
            results = await self.neo4j_client.execute_query(query, params)
            exercises = []
            for result in results:
                exercise = dict(result["e"])
                # 使用primary_muscle_zh作为目标肌群
                primary_muscle = exercise.get("primary_muscle_zh", "")
                exercise["target_muscles"] = [primary_muscle] if primary_muscle else []
                exercises.append(exercise)
            return exercises
        except Exception as e:
            self.logger.error(f"力量类型查询失败: {e}")
            return []

    
    def _calculate_similarity(
        self,
        original: Dict[str, Any],
        candidate: Dict[str, Any]
    ) -> float:
        """
        计算相似度评分（v8.61.0增强版 - 添加握法匹配）
        字段名已与统一数据结构对齐（v2.3.0）
        
        权重分配（基于musclewiki数据特点）:
        - 主要肌群匹配: 35%（最重要）
        - 力学特性匹配: 20%（单关节vs多关节）
        - 力量类型匹配: 20%（推力vs拉力）
        - 器械类型匹配: 10%（器械相似性）
        - 握法匹配: 10%（v8.61.0新增，使用USES_GRIP关系）
        - 难度等级接近: 5%（难度相近）
        
        参考: exercise_alternative_finder_improvement_plan.md 方案1
        """
        score = 0.0
        
        # 1. 主要肌群匹配 (35%)
        muscle_overlap = self._calculate_overlap(
            original.get("target_muscles") or [],
            candidate.get("target_muscles") or []
        )
        score += muscle_overlap * 0.35
        
        # 2. 力学特性匹配 (20%) - 使用统一字段名
        orig_mechanic = original.get("mechanic") or ""
        cand_mechanic = candidate.get("mechanic_zh") or candidate.get("mechanic_en") or ""
        if orig_mechanic == cand_mechanic:
            score += 0.20
        
        # 3. 力量类型匹配 (20%) - 使用统一字段名
        orig_force = original.get("force_type") or ""
        cand_force = candidate.get("force_zh") or candidate.get("force_en") or ""
        if orig_force == cand_force:
            score += 0.20
        
        # 4. 器械类型匹配 (10%)
        orig_equipment = self._normalize_equipment(original.get("equipment_type"))
        cand_equipment = self._normalize_equipment(candidate.get("equipment_zh"))
        
        if orig_equipment and cand_equipment:
            equipment_overlap = len(orig_equipment & cand_equipment) / len(orig_equipment | cand_equipment)
            score += equipment_overlap * 0.10
        
        # 5. 握法匹配 (10%) - v8.61.0新增，使用USES_GRIP关系数据
        orig_grips = self._normalize_grips(original.get("grips") or [])
        cand_grips = self._normalize_grips(candidate.get("grips_zh") or [])
        
        if orig_grips and cand_grips:
            grip_overlap = len(orig_grips & cand_grips) / len(orig_grips | cand_grips)
            score += grip_overlap * 0.10
        elif not orig_grips and not cand_grips:
            # 两者都没有握法要求，视为匹配
            score += 0.10
        
        # 6. 难度等级接近度 (5%) - 使用统一字段名
        difficulty_map = {"新手": 1, "beginner": 1, "初级": 1, "中级": 2, "intermediate": 2, "高级": 3, "advanced": 3}
        orig_diff = difficulty_map.get(original.get("difficulty_level") or "中级", 2)
        cand_diff_zh = candidate.get("difficulty_zh") or ""
        cand_diff_en = candidate.get("difficulty_en") or ""
        cand_diff = difficulty_map.get(cand_diff_zh, difficulty_map.get(cand_diff_en.lower() if cand_diff_en else "", 2))
        
        # 难度相差不超过1级
        if abs(orig_diff - cand_diff) <= 1:
            score += 0.05
        
        return score
    
    def _normalize_grips(self, grips) -> set:
        """标准化握法字段（v8.61.0新增）"""
        if isinstance(grips, list):
            return set(grips)
        elif isinstance(grips, str):
            return {grips}
        else:
            return set()
    
    def _normalize_equipment(self, equipment) -> set:
        """标准化器械字段"""
        if isinstance(equipment, list):
            return set(equipment)
        elif isinstance(equipment, str):
            return {equipment}
        else:
            return set()
    
    def _calculate_overlap(self, set1: List[str], set2: List[str]) -> float:
        """计算集合重叠度（Jaccard相似度）"""
        if not set1 or not set2:
            return 0.0
        
        set1_set = set(set1)
        set2_set = set(set2)
        
        intersection = set1_set & set2_set
        union = set1_set | set2_set
        
        return len(intersection) / len(union) if union else 0.0
    
    def _generate_match_reasons(
        self,
        original: Dict[str, Any],
        candidate: Dict[str, Any]
    ) -> List[str]:
        """生成匹配原因"""
        reasons = []
        
        # 目标肌群重叠
        muscle_overlap = self._calculate_overlap(
            original.get("target_muscles", []),
            candidate.get("target_muscles", [])
        )
        if muscle_overlap > 0.7:
            reasons.append("目标肌群高度重叠")
        elif muscle_overlap > 0.4:
            reasons.append("目标肌群部分重叠")
        
        # 运动模式相同 - 使用mechanic字段
        if original.get("movement_pattern") == candidate.get("mechanic"):
            reasons.append("运动模式相同")
        
        # 器械需求相似
        equipment_overlap = self._calculate_overlap(
            original.get("equipment_type", []),
            candidate.get("equipment_zh", [])
        )
        if equipment_overlap > 0.5:
            reasons.append("器械需求相似")
        
        # 力学特性相同
        if original.get("mechanic") == candidate.get("mechanic"):
            reasons.append("力学特性相同")
        
        if not reasons:
            reasons.append("基于综合特性匹配")
        
        return reasons
    
    def _generate_adjustments(
        self,
        original: Dict[str, Any],
        candidate: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> List[str]:
        """生成调整建议"""
        adjustments = []
        
        # 技能水平调整
        skill_level = constraints.get("skill_level")
        # 使用统一字段名：difficulty_zh / difficulty_en
        candidate_difficulty = candidate.get("difficulty_zh") or candidate.get("difficulty_en") or "intermediate"
        
        if skill_level == "beginner" and candidate_difficulty == "advanced":
            adjustments.append("建议降低训练强度")
        
        # 损伤保护
        if constraints.get("injury_limitations"):
            adjustments.append("注意保护受伤部位")
        
        # 器械替代
        available_equipment = constraints.get("available_equipment", [])
        candidate_equipment = candidate.get("equipment_zh", [])
        
        if available_equipment and candidate_equipment:
            if not any(eq in available_equipment for eq in candidate_equipment):
                adjustments.append("使用可用的替代器械")
        
        # 通用建议
        adjustments.append("充分热身")
        adjustments.append("关注动作质量")
        
        return adjustments
    
    def _generate_selection_rationale(
        self,
        reason: str,
        constraints: Dict[str, Any]
    ) -> str:
        """生成选择依据"""
        rationale_map = {
            "injury": "基于医学安全考虑，优先选择低风险替代动作",
            "equipment_unavailable": "基于可用器械约束，匹配器械需求相似的动作",
            "difficulty_too_high": "基于技能水平，选择适合当前能力的动作",
            "preference_change": "基于个人偏好，保持相似训练效果的同时提供新鲜感",
            "variety": "基于多样化训练需求，提供不同刺激方式的动作选择"
        }
        
        rationale = rationale_map.get(reason, "基于多项因素综合考虑")
        
        skill_level = constraints.get("skill_level")
        if skill_level:
            rationale += f"，考虑用户当前技能水平为{skill_level}"
        
        return rationale
    
    def _generate_usage_guidelines(
        self,
        reason: str,
        constraints: Dict[str, Any]
    ) -> List[str]:
        """生成使用指南"""
        guidelines = []
        
        guidelines.append("循序渐进，不要急于求成")
        guidelines.append("关注动作质量而非重量")
        guidelines.append("定期评估替代效果")
        
        if reason == "injury":
            guidelines.append("如有疼痛立即停止")
            guidelines.append("遵循医疗专业人员建议")
        
        if constraints.get("injury_limitations"):
            guidelines.append("特别保护受伤部位")
        
        guidelines.append("记录训练感受和效果")
        
        return guidelines
    
    def _generate_progression_path(
        self,
        original_exercise_id: str,
        alternatives: List[Dict[str, Any]]
    ) -> List[str]:
        """生成进阶路径"""
        path = []
        
        if alternatives:
            path.append(f"第1阶段: 使用 {alternatives[0]['name_zh']} 熟悉动作模式")
            
            if len(alternatives) > 1:
                path.append(f"第2阶段: 过渡到 {alternatives[1]['name_zh']} 增加挑战")
            
            path.append(f"第3阶段: 尝试回到原动作 {original_exercise_id}")
            path.append("长期: 周期性轮换使用，保持训练多样性")
        
        return path
