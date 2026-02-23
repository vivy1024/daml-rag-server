"""
安全动作修饰器 MCP工具

完全基于用户档案和Neo4j数据
参考TypeScript版本的safe-exercise-modifier实现

功能特性：
- 基于用户档案和健康状况提供安全的动作修饰
- 基于Neo4j CONTRAINDICATED_FOR关系查询禁忌动作
- 使用HAS_KINETIC_CHAIN关系筛选康复友好动作（v8.61.0新增）
- 使用REHAB_PROGRESSION关系查询康复渐进路径（v8.61.0新增）
- 提供替代动作、修改版本、避免执行等多种方案
- 生成个性化安全协议和医学指导

作者: BUILD_BODY Team
版本: v1.2.0
基于: 用户档案 + Neo4j v7.0.0
更新: 2026-01-06 - 添加HAS_KINETIC_CHAIN和REHAB_PROGRESSION关系支持
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
import time
from datetime import datetime

from ..base_tool import BaseMCPTool
from src.framework.exceptions import ValidationError as ToolValidationError


# =============================================================================
# 枚举类型定义
# =============================================================================

class ModificationPurpose(str, Enum):
    """修饰目的"""
    INJURY_PREVENTION = "injury_prevention"
    BEGINNER_FRIENDLY = "beginner_friendly"
    REHABILITATION = "rehabilitation"
    AGE_APPROPRIATE = "age_appropriate"
    EQUIPMENT_LIMITED = "equipment_limited"


class ModificationPreference(str, Enum):
    """修改偏好"""
    SAFE_ONLY = "safe_only"
    MODERATE = "moderate"
    ADAPTIVE = "adaptive"


class ModificationType(str, Enum):
    """修改类型"""
    ALTERNATIVE = "alternative"
    MODIFIED_VERSION = "modified_version"
    AVOID = "avoid"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# 输入Schema定义
# =============================================================================

class SafeExerciseModifierInput(BaseModel):
    """安全动作修饰器输入"""
    user_id: str = Field(..., description="用户ID，用于获取个人化安全参数")
    exercise_id: str = Field(..., description="需要修饰的动作ID")
    modification_purpose: ModificationPurpose = Field(..., description="修饰目的")
    user_injuries: Optional[List[str]] = Field(None, description="用户损伤历史列表")
    safety_requirements: Optional[List[str]] = Field(None, description="特殊安全要求")
    available_equipment: Optional[List[str]] = Field(None, description="可用器械列表")
    modification_preference: ModificationPreference = Field(
        ModificationPreference.MODERATE,
        description="修改偏好"
    )


# =============================================================================
# 输出Schema定义
# =============================================================================

class ExerciseModification(BaseModel):
    """动作修改方案"""
    original_exercise_id: str
    original_name_zh: str
    modified_exercise_id: Optional[str]
    modified_name_zh: str
    modification_type: ModificationType
    safety_score_before: float
    safety_score_after: float
    modifications_applied: List[str]
    contraindications_avoided: List[str]
    safety_enhancements: List[str]
    instructions_zh: str
    warnings: List[str]


class ContraindicationDetail(BaseModel):
    """禁忌症详情"""
    injury_name: str
    category: str
    severity: float


class ContraindicationsAnalysis(BaseModel):
    """禁忌症分析"""
    has_contraindications: bool
    risk_level: RiskLevel
    contraindications_count: int
    max_severity: Optional[float] = None
    contraindications_details: Optional[List[ContraindicationDetail]] = None
    warnings: List[str]


class OriginalExerciseInfo(BaseModel):
    """原动作信息"""
    exercise_id: str
    name_zh: str
    name_en: str
    primary_muscle_zh: str
    contraindications_zh: List[str]
    safety_warning_signs_zh: List[str]


class SafeExerciseModifierOutput(BaseModel):
    """安全动作修饰器输出"""
    success: bool
    tool_name: str
    original_exercise: OriginalExerciseInfo
    modifications: List[ExerciseModification]
    medical_guidance: str
    contraindications_analysis: ContraindicationsAnalysis
    safety_recommendations: List[str]
    execution_time_ms: float
    confidence_score: float


# =============================================================================
# 安全动作修饰器类
# =============================================================================

class SafeExerciseModifier(BaseMCPTool):
    """安全动作修饰器"""

    def get_name(self) -> str:
        return "safe_exercise_modifier"

    def get_description(self) -> str:
        return "安全动作修饰器 - 基于用户档案和Neo4j数据的医学安全修饰"

    def get_category(self) -> str:
        return "safety"

    def get_input_schema(self) -> type[BaseModel]:
        return SafeExerciseModifierInput

    def get_output_schema(self) -> type[BaseModel]:
        return SafeExerciseModifierOutput

    def get_complexity(self) -> str:
        return "complex"

    def get_estimated_duration(self) -> float:
        return 1800.0

    def requires_user_profile(self) -> bool:
        return True

    def get_dependencies(self) -> List[str]:
        return ["neo4j", "user_profile"]

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行安全动作修饰

        流程：
        1. 验证参数
        2. 获取用户档案（用于安全过滤）
        3. 获取原动作信息
        4. 获取损伤类型信息
        5. 检查禁忌关系
        6. 生成修改方案
        7. 分析禁忌症
        8. 生成医学指导
        9. 生成安全建议
        """
        start_time = time.time()

        try:
            # Step 1: 验证参数
            self._validate_params(input_data)

            # Step 2: 获取用户档案（优先从DAG注入的input_data获取）
            user_profile = input_data.get("user_profile") or await self._get_user_profile(input_data.get("user_id"))

            # Step 3: 获取原动作信息
            original_exercise = await self._get_exercise_by_id(input_data["exercise_id"])
            if not original_exercise:
                raise ToolValidationError(f"未找到ID为 {input_data['exercise_id']} 的动作")

            # Step 4: 获取损伤类型信息
            injury_info = await self._get_injury_type_info(input_data, user_profile)

            # Step 5: 检查禁忌关系
            contraindications = await self._check_contraindications(
                input_data["exercise_id"],
                injury_info,
                user_profile
            )

            # Step 6: 生成修改方案
            modifications = await self._generate_modifications(
                original_exercise,
                injury_info,
                contraindications,
                input_data
            )

            # Step 7: 分析禁忌症
            contraindications_analysis = self._analyze_contraindications(
                original_exercise,
                contraindications
            )

            # Step 8: 生成医学指导
            medical_guidance = self._generate_medical_guidance(
                injury_info,
                modifications,
                contraindications_analysis
            )

            # Step 9: 生成安全建议
            safety_recommendations = self._generate_safety_recommendations(
                original_exercise,
                injury_info,
                modifications,
                user_profile
            )

            execution_time_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "tool_name": self.get_name(),
                "original_exercise": {
                    "exercise_id": original_exercise.get("exercise_id", input_data["exercise_id"]),
                    "name_zh": original_exercise.get("name_zh", ""),
                    "name_en": original_exercise.get("name_en", ""),
                    "primary_muscle_zh": original_exercise.get("primary_muscle_zh", ""),
                    "contraindications_zh": original_exercise.get("contraindications_zh", []),
                    "safety_warning_signs_zh": original_exercise.get("safety_warning_signs_zh", [])
                },
                "modifications": [mod.dict() for mod in modifications],
                "medical_guidance": medical_guidance,
                "contraindications_analysis": contraindications_analysis.dict(),
                "safety_recommendations": safety_recommendations,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 90.0
            }

        except Exception as e:
            self.logger.error(f"安全动作修饰失败: {e}", exc_info=True)
            raise

    def _validate_params(self, params: Dict[str, Any]) -> None:
        """验证参数"""
        if not params:
            raise ToolValidationError("参数不能为空")

        required_fields = ["exercise_id", "modification_purpose"]
        for field in required_fields:
            if field not in params:
                raise ToolValidationError(f"缺少必需参数: {field}")

        valid_purposes = [p.value for p in ModificationPurpose]
        if params["modification_purpose"] not in valid_purposes:
            raise ToolValidationError(
                f"modification_purpose必须是: {', '.join(valid_purposes)}"
            )

    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户档案（可选）"""
        # TODO: 如果有UserProfileClient，调用它
        # 目前返回空字典
        return {}

    async def _get_exercise_by_id(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取动作信息"""
        # 尝试将exercise_id转换为整数（Neo4j中ID可能是整数）
        try:
            exercise_id_int = int(exercise_id)
        except (ValueError, TypeError):
            exercise_id_int = exercise_id
        
        query = """
        MATCH (e:Exercise)
        WHERE e.id = $exercise_id OR e.id = $exercise_id_int
        RETURN e
        LIMIT 1
        """

        result = await self.neo4j_client.execute_query(
            query,
            {"exercise_id": exercise_id, "exercise_id_int": exercise_id_int}
        )

        if not result:
            return None

        # execute_query返回的是记录列表
        record = result[0]
        exercise_node = record.get("e")
        
        if not exercise_node:
            return None
        
        # 将Neo4j节点转换为字典
        if hasattr(exercise_node, '__dict__'):
            exercise_data = dict(exercise_node)
        elif hasattr(exercise_node, 'items'):
            exercise_data = dict(exercise_node.items())
        else:
            exercise_data = exercise_node

        return exercise_data

    async def _get_injury_type_info(
        self,
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """获取损伤类型信息"""
        injury_types = set()

        # 从输入参数获取
        if input_data.get("user_injuries"):
            for injury in input_data["user_injuries"]:
                injury_types.add(injury)

        # 从用户档案获取
        if user_profile.get("health_profile", {}).get("injury_history"):
            for injury in user_profile["health_profile"]["injury_history"]:
                if injury.get("body_part"):
                    injury_types.add(f"{injury.get('type', '')}_{injury['body_part']}")

        if user_profile.get("health_profile", {}).get("chronic_conditions"):
            for condition in user_profile["health_profile"]["chronic_conditions"]:
                injury_types.add(condition.get("name", ""))

        if not injury_types:
            return {
                "injury_type": input_data["modification_purpose"],
                "description": "用户提供的修饰目的",
                "affected_body_parts": [input_data["modification_purpose"]],
                "severity": "moderate"
            }

        # 查询Neo4j中的损伤类型信息
        query = """
        MATCH (inj:InjuryType)
        WHERE inj.name_zh IN $injury_types
           OR inj.name_en IN $injury_types
           OR inj.category_zh IN $injury_types
        RETURN inj
        ORDER BY inj.severity_level DESC
        LIMIT 5
        """

        result = await self.neo4j_client.execute_query(
            query,
            {"injury_types": list(injury_types)}
        )

        if result and result.get("records"):
            return result["records"][0].get("inj", {})

        return {
            "injury_type": list(injury_types)[0] if injury_types else "",
            "description": "用户档案中的损伤类型",
            "affected_body_parts": list(injury_types),
            "severity": "moderate"
        }

    async def _check_contraindications(
        self,
        exercise_id: str,
        injury_info: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查禁忌关系"""
        injury_types = set()

        # 添加损伤类型
        if injury_info.get("injury_type"):
            injury_types.add(injury_info["injury_type"])
        if injury_info.get("affected_body_parts"):
            for part in injury_info["affected_body_parts"]:
                injury_types.add(part)

        query = """
        MATCH (e:Exercise {id: $exercise_id})
        OPTIONAL MATCH (e)-[r:CONTRAINDICATED_FOR]->(inj:InjuryType)
        WHERE inj.name_zh IN $injury_types
           OR inj.name_en IN $injury_types
           OR inj.category_zh IN $injury_types

        OPTIONAL MATCH (e2:Exercise {id: $exercise_id})
        WHERE ANY(warning IN e2.safety_warning_signs WHERE warning CONTAINS $injury_type)

        RETURN DISTINCT
          inj.name_zh as injury_name_zh,
          inj.name_en as injury_name_en,
          inj.category_zh as category_zh,
          inj.severity_level as severity_level,
          inj.contraindications_zh as contraindications_zh,
          r.severity as severity,
          r.reason as reason,
          type(r) as relationship_type,
          e2.safety_warning_signs as relevant_warnings

        ORDER BY inj.severity_level DESC
        """

        result = await self.neo4j_client.execute_query(
            query,
            {
                "exercise_id": exercise_id,
                "injury_types": list(injury_types),
                "injury_type": injury_info.get("injury_type", "")
            }
        )

        return result.get("records", []) if result else []

    async def _generate_modifications(
        self,
        original_exercise: Dict[str, Any],
        injury_info: Dict[str, Any],
        contraindications: List[Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> List[ExerciseModification]:
        """
        生成修改方案
        
        v8.61.0增强：康复场景使用REHAB_PROGRESSION关系查询渐进路径
        """
        modifications = []
        modification_purpose = input_data.get("modification_purpose", "")
        is_rehabilitation = modification_purpose == ModificationPurpose.REHABILITATION.value

        # 方案0: 康复场景优先查询REHAB_PROGRESSION渐进路径（v8.61.0新增）
        if is_rehabilitation:
            rehab_progression = await self._get_rehab_progression(
                input_data["exercise_id"],
                injury_info
            )
            if rehab_progression:
                for prog in rehab_progression:
                    modifications.append(ExerciseModification(
                        original_exercise_id=original_exercise.get("exercise_id", input_data["exercise_id"]),
                        original_name_zh=original_exercise.get("name_zh", ""),
                        modified_exercise_id=prog.get("exercise_id"),
                        modified_name_zh=prog.get("name_zh", "康复渐进动作"),
                        modification_type=ModificationType.ALTERNATIVE,
                        safety_score_before=50.0,
                        safety_score_after=95.0,  # 康复渐进路径安全性最高
                        modifications_applied=[
                            f"康复阶段{prog.get('phase', '')}推荐动作",
                            "基于REHAB_PROGRESSION关系的科学渐进",
                            "适合当前康复阶段"
                        ],
                        contraindications_avoided=[
                            contra.get("injury_name_zh", "") for contra in contraindications
                        ],
                        safety_enhancements=[
                            "遵循康复渐进原则",
                            "从低负荷开始逐步增加",
                            "密切监控疼痛反应"
                        ],
                        instructions_zh=prog.get("instructions_zh", "按康复阶段要求执行"),
                        warnings=["康复期间请遵循医疗建议", "如有疼痛立即停止"]
                    ))

        # 方案1: 寻找安全的替代动作
        safe_alternatives = await self._find_safe_alternatives(
            original_exercise,
            injury_info,
            input_data
        )

        for alt in safe_alternatives:
            modifications.append(ExerciseModification(
                original_exercise_id=original_exercise.get("exercise_id", input_data["exercise_id"]),
                original_name_zh=original_exercise.get("name_zh", ""),
                modified_exercise_id=alt.get("exercise_id"),
                modified_name_zh=alt.get("name_zh", "安全替代动作"),
                modification_type=ModificationType.ALTERNATIVE,
                safety_score_before=50.0,
                safety_score_after=90.0,
                modifications_applied=[
                    "使用安全替代动作",
                    f"避免{injury_info.get('injury_type', '受伤部位')}受压",
                    "保持可控的运动范围"
                ],
                contraindications_avoided=[
                    contra.get("injury_name_zh", "") for contra in contraindications
                ],
                safety_enhancements=[
                    "选择低风险动作模式",
                    "使用辅助器械减少负荷",
                    "专注动作质量和控制"
                ],
                instructions_zh=alt.get("instructions_zh", "按标准动作执行，注意保护受伤部位"),
                warnings=alt.get("safety_warnings_zh", ["如有疼痛立即停止"])
            ))

        # 方案2: 修改原动作（如果可能）
        if input_data.get("modification_preference") != ModificationPreference.SAFE_ONLY.value:
            modified_version = await self._generate_modified_version(
                original_exercise,
                injury_info,
                contraindications,
                input_data
            )

            if modified_version:
                modifications.append(ExerciseModification(
                    original_exercise_id=original_exercise.get("exercise_id", input_data["exercise_id"]),
                    original_name_zh=original_exercise.get("name_zh", ""),
                    modified_exercise_id=original_exercise.get("exercise_id", input_data["exercise_id"]),
                    modified_name_zh=f"{original_exercise.get('name_zh', '动作')} (安全版)",
                    modification_type=ModificationType.MODIFIED_VERSION,
                    safety_score_before=50.0,
                    safety_score_after=75.0,
                    modifications_applied=modified_version.get("modifications", []),
                    contraindications_avoided=modified_version.get("contraindications_avoided", []),
                    safety_enhancements=modified_version.get("safety_enhancements", []),
                    instructions_zh=modified_version.get("instructions_zh", ""),
                    warnings=modified_version.get("warnings", [])
                ))

        # 方案3: 避免执行（高风险情况）
        avoidance = self._generate_avoidance_guidance(
            original_exercise,
            injury_info,
            contraindications
        )

        modifications.append(ExerciseModification(
            original_exercise_id=original_exercise.get("exercise_id", input_data["exercise_id"]),
            original_name_zh=original_exercise.get("name_zh", ""),
            modified_exercise_id=None,
            modified_name_zh="建议避免执行",
            modification_type=ModificationType.AVOID,
            safety_score_before=50.0,
            safety_score_after=0.0,
            modifications_applied=["完全避免执行原动作"],
            contraindications_avoided=avoidance.get("contraindications_avoided", []),
            safety_enhancements=["选择完全不涉及受伤部位的动作"],
            instructions_zh=avoidance.get("instructions_zh", ""),
            warnings=avoidance.get("warnings", ["高风险动作", "可能导致伤情恶化"])
        ))

        return modifications

    async def _get_rehab_progression(
        self,
        exercise_id: str,
        injury_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        获取康复渐进路径（v8.61.0新增）
        
        使用REHAB_PROGRESSION关系查询康复阶段的推荐动作
        """
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        OPTIONAL MATCH (e)-[r:REHAB_PROGRESSION]->(next:Exercise)
        OPTIONAL MATCH (prev:Exercise)-[r2:REHAB_PROGRESSION]->(e)
        
        WITH e, 
             collect(DISTINCT {
                 exercise_id: next.id,
                 name_zh: next.name_zh,
                 phase: r.phase,
                 instructions_zh: next.correct_steps_zh,
                 direction: 'next'
             }) as next_exercises,
             collect(DISTINCT {
                 exercise_id: prev.id,
                 name_zh: prev.name_zh,
                 phase: r2.phase,
                 instructions_zh: prev.correct_steps_zh,
                 direction: 'prev'
             }) as prev_exercises
        
        RETURN next_exercises, prev_exercises
        """
        
        try:
            # 将exercise_id转换为整数
            exercise_id_int = int(exercise_id) if isinstance(exercise_id, str) else exercise_id
            results = await self.neo4j_client.execute_query(query, {"exercise_id": exercise_id_int})
            
            if not results:
                return []
            
            result = results[0]
            progressions = []
            
            # 添加前置动作（更简单的康复动作）
            prev_exercises = result.get("prev_exercises", [])
            for ex in prev_exercises:
                if ex.get("exercise_id"):
                    ex["phase"] = "前置康复"
                    progressions.append(ex)
            
            # 添加后续动作（进阶康复动作）
            next_exercises = result.get("next_exercises", [])
            for ex in next_exercises:
                if ex.get("exercise_id"):
                    ex["phase"] = "进阶康复"
                    progressions.append(ex)
            
            self.logger.info(f"✅ 通过REHAB_PROGRESSION关系找到{len(progressions)}个康复渐进动作")
            return progressions
            
        except Exception as e:
            self.logger.warning(f"REHAB_PROGRESSION查询失败: {e}")
            return []

    async def _find_safe_alternatives(
        self,
        original_exercise: Dict[str, Any],
        injury_info: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        寻找安全替代动作
        
        v8.61.0增强：使用HAS_KINETIC_CHAIN关系筛选康复友好动作
        - 康复场景优先推荐闭链动作（closed_chain）
        - 闭链动作关节负荷更小，更适合康复训练
        """
        injury_type = injury_info.get("injury_type", "")
        modification_purpose = input_data.get("modification_purpose", "")
        
        # 判断是否为康复场景
        is_rehabilitation = modification_purpose == ModificationPurpose.REHABILITATION.value
        
        # 构建查询 - 康复场景优先闭链动作
        if is_rehabilitation:
            query = """
            MATCH (source:Exercise {id: $exercise_id})-[:TARGETS_PRIMARY]->(muscle:Muscle)
            
            // 查找同肌群的候选动作
            MATCH (candidate:Exercise)-[:TARGETS_PRIMARY]->(muscle2:Muscle)
            WHERE muscle2.name_zh = muscle.name_zh
              AND candidate.id <> $exercise_id
              AND NOT ANY(warning IN candidate.safety_warning_signs WHERE warning CONTAINS $injury_type)
            
            // 使用HAS_KINETIC_CHAIN关系筛选闭链动作
            OPTIONAL MATCH (candidate)-[:HAS_KINETIC_CHAIN]->(kc:KineticChain)
            
            RETURN DISTINCT
              candidate.id as exercise_id,
              candidate.name_zh,
              candidate.name_en,
              candidate.mechanic_zh,
              candidate.correct_steps_zh as instructions_zh,
              candidate.safety_warning_signs,
              size(candidate.safety_warning_signs) as safety_warning_count,
              kc.name as kinetic_chain,
              CASE 
                WHEN kc.name = 'closed_chain' THEN 0  // 闭链动作优先
                WHEN kc.name = 'mixed' THEN 1
                WHEN kc.name = 'open_chain' THEN 2
                ELSE 3
              END as kinetic_chain_priority
            
            ORDER BY kinetic_chain_priority ASC, safety_warning_count ASC
            LIMIT 5
            """
        else:
            # 非康复场景使用原有查询
            query = """
            MATCH (source:Exercise {id: $exercise_id})-[:TARGETS_PRIMARY]->(muscle:Muscle)

            MATCH (candidate:Exercise)-[:TARGETS_PRIMARY]->(muscle2:Muscle)
            WHERE muscle2.name_zh = muscle.name_zh
              AND candidate.id <> $exercise_id
              AND NOT ANY(warning IN candidate.safety_warning_signs WHERE warning CONTAINS $injury_type)

            RETURN DISTINCT
              candidate.id as exercise_id,
              candidate.name_zh,
              candidate.name_en,
              candidate.mechanic_zh,
              candidate.correct_steps_zh as instructions_zh,
              candidate.safety_warning_signs,
              size(candidate.safety_warning_signs) as safety_warning_count

            ORDER BY safety_warning_count ASC
            LIMIT 5
            """

        result = await self.neo4j_client.execute_query(
            query,
            {
                "exercise_id": original_exercise.get("exercise_id", input_data["exercise_id"]),
                "injury_type": injury_type
            }
        )

        return result.get("records", []) if result else []

    async def _generate_modified_version(
        self,
        original_exercise: Dict[str, Any],
        injury_info: Dict[str, Any],
        contraindications: List[Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """生成修改版本的原动作（基于severity字段）"""
        injury_type = injury_info.get("injury_type", "")

        # 检查是否有绝对禁忌
        has_absolute = any(contra.get("severity") == "absolute" for contra in contraindications)
        if has_absolute:
            return None  # 绝对禁忌，不建议修改原动作
        
        # 检查传统severity_level
        if any(contra.get("severity_level", 0) > 7 for contra in contraindications):
            return None  # 严重禁忌，不建议修改

        modifications = []
        contraindications_avoided = []
        safety_enhancements = []
        warnings = []

        # 基于修饰目的和受伤部位生成修改建议
        if input_data["modification_purpose"] == ModificationPurpose.BEGINNER_FRIENDLY.value:
            modifications.extend([
                "降低训练重量至50%",
                "减少动作幅度至舒适范围",
                "延长休息时间至3分钟",
                "专注技术学习而非重量"
            ])
            safety_enhancements.extend([
                "充分学习动作技术",
                "使用镜子进行自我纠正",
                "寻求专业指导"
            ])
            warnings.append("新手请在专业人士指导下进行")

        elif input_data["modification_purpose"] == ModificationPurpose.REHABILITATION.value:
            modifications.extend([
                "仅在无痛范围内活动",
                "使用弹力带或辅助器械",
                "减少训练频率至每周2次",
                "严格控制动作速度"
            ])
            safety_enhancements.extend([
                "遵循医生或治疗师指导",
                "定期评估康复进度",
                "使用冰敷或热敷"
            ])
            warnings.append("康复期间请严格遵循医疗建议")

        elif "肩" in injury_type:
            modifications.extend([
                "减少肩关节活动范围至无痛范围",
                "使用较轻重量或弹力带",
                "避免超过头顶的动作",
                "保持肩胛骨稳定"
            ])
            contraindications_avoided.append("肩关节过度外展")
            safety_enhancements.extend([
                "充分热身肩关节",
                "使用镜子和教练反馈",
                "监控疼痛感受"
            ])
            warnings.append("如有肩部疼痛立即停止")

        elif "腰" in injury_type:
            modifications.extend([
                "保持腰椎中立位",
                "减少脊柱屈曲角度",
                "使用腿部和臀部发力",
                "避免快速扭转动作"
            ])
            contraindications_avoided.append("腰椎过度负荷")
            safety_enhancements.extend([
                "使用腰带保护",
                "加强核心稳定性训练",
                "循序渐进增加负荷"
            ])
            warnings.append("严格遵守动作规范")

        else:
            # 通用修改建议
            modifications.extend([
                "减少运动幅度至舒适范围",
                "降低训练强度",
                "增加控制时间",
                "关注受伤部位感受"
            ])
            contraindications_avoided.append("直接压迫受伤部位")
            safety_enhancements.extend([
                "充分热身",
                "动作缓慢控制",
                "定期评估疼痛"
            ])
            warnings.append("密切监控身体反应")

        return {
            "modifications": modifications,
            "contraindications_avoided": contraindications_avoided,
            "safety_enhancements": safety_enhancements,
            "instructions_zh": f"修改版{original_exercise.get('name_zh', '')}: {'; '.join(modifications[:2])}",
            "warnings": warnings
        }

    def _generate_avoidance_guidance(
        self,
        original_exercise: Dict[str, Any],
        injury_info: Dict[str, Any],
        contraindications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成避免执行指导"""
        injury_type = injury_info.get("injury_type", "")

        return {
            "contraindications_avoided": [
                contra.get("injury_name_zh", "") for contra in contraindications
            ],
            "instructions_zh": (
                f"由于{injury_type}，建议完全避免执行{original_exercise.get('name_zh', '')}，"
                f"直至伤情完全恢复并在专业指导下进行"
            ),
            "warnings": [
                f"{original_exercise.get('name_zh', '')}可能加重{injury_type}伤情",
                "强行执行可能导致长期损伤",
                "建议寻求专业医疗建议"
            ]
        }

    def _analyze_contraindications(
        self,
        original_exercise: Dict[str, Any],
        contraindications: List[Dict[str, Any]]
    ) -> ContraindicationsAnalysis:
        """分析禁忌症（基于severity字段）"""
        if not contraindications:
            return ContraindicationsAnalysis(
                has_contraindications=False,
                risk_level=RiskLevel.LOW,
                contraindications_count=0,
                warnings=["未发现明显禁忌，但仍有受伤风险"]
            )

        # 检查severity字段（absolute/relative/caution）
        has_absolute = any(c.get("severity") == "absolute" for c in contraindications)
        has_relative = any(c.get("severity") == "relative" for c in contraindications)
        has_caution = any(c.get("severity") == "caution" for c in contraindications)
        
        # 根据severity确定风险等级
        if has_absolute:
            risk_level = RiskLevel.HIGH
            risk_description = "绝对禁忌"
        elif has_relative:
            risk_level = RiskLevel.MODERATE
            risk_description = "相对禁忌"
        elif has_caution:
            risk_level = RiskLevel.LOW
            risk_description = "谨慎使用"
        else:
            # 回退到传统severity_level
            severity_levels = [contra.get("severity_level", 5) for contra in contraindications]
            max_severity = max(severity_levels)
            if max_severity >= 8:
                risk_level = RiskLevel.HIGH
                risk_description = "高风险"
            elif max_severity >= 5:
                risk_level = RiskLevel.MODERATE
                risk_description = "中等风险"
            else:
                risk_level = RiskLevel.LOW
                risk_description = "低风险"

        # 获取最大severity_level（用于显示）
        severity_levels = [contra.get("severity_level", 5) for contra in contraindications]
        max_severity = max(severity_levels) if severity_levels else 5

        # 生成警告信息
        warnings = [
            f"存在{len(contraindications)}个禁忌关系",
            f"风险分级: {risk_description}",
        ]
        
        if has_absolute:
            absolute_injuries = [c.get("injury_name_zh", "损伤") for c in contraindications if c.get("severity") == "absolute"]
            warnings.append(f"⛔ 绝对禁忌: {', '.join(absolute_injuries)} - 必须完全避免")
        elif has_relative:
            relative_injuries = [c.get("injury_name_zh", "损伤") for c in contraindications if c.get("severity") == "relative"]
            warnings.append(f"⚠️ 相对禁忌: {', '.join(relative_injuries)} - 需要专业指导")
        elif has_caution:
            warnings.append("💡 谨慎使用 - 需要特别注意")
        
        warnings.append(f"建议级别: {'避免执行' if risk_level == RiskLevel.HIGH else '谨慎修改' if risk_level == RiskLevel.MODERATE else '适度调整'}")

        return ContraindicationsAnalysis(
            has_contraindications=True,
            risk_level=risk_level,
            contraindications_count=len(contraindications),
            max_severity=float(max_severity),
            contraindications_details=[
                ContraindicationDetail(
                    injury_name=contra.get("injury_name_zh", ""),
                    category=contra.get("category_zh", ""),
                    severity=float(contra.get("severity_level", 0))
                )
                for contra in contraindications
            ],
            warnings=warnings
        )

    def _generate_medical_guidance(
        self,
        injury_info: Dict[str, Any],
        modifications: List[ExerciseModification],
        contraindications_analysis: ContraindicationsAnalysis
    ) -> str:
        """生成医学指导（基于severity字段）"""
        injury_type = injury_info.get("injury_type", "未知损伤")
        risk_level = contraindications_analysis.risk_level
        warnings = contraindications_analysis.warnings

        guidance_parts = [
            f"基于{injury_type}的医学安全评估",
            f"风险等级: {risk_level.value}"
        ]

        # 根据warnings中的severity信息提供指导
        if any("绝对禁忌" in w for w in warnings):
            guidance_parts.extend([
                "⛔ 绝对禁忌：必须完全避免执行原动作",
                "这些动作会直接加重损伤，可能导致二次损伤",
                "请在专业医生或理疗师指导下选择完全不涉及受伤部位的替代动作",
                "建议进行医学评估，确认康复阶段后再考虑训练"
            ])
        elif any("相对禁忌" in w for w in warnings):
            guidance_parts.extend([
                "⚠️ 相对禁忌：需要在特定条件下谨慎进行",
                "必须在专业人士指导和监督下进行",
                "需要适当的技术和负荷控制",
                "取决于损伤严重程度和康复阶段",
                "建议降低训练强度和频率，密切监控受伤部位反应"
            ])
        elif any("谨慎使用" in w for w in warnings):
            guidance_parts.extend([
                "💡 谨慎使用：可以进行但需要特别注意",
                "需要适当的热身和准备",
                "需要密切监控身体反应",
                "建议降低负荷和强度",
                "注意动作质量和控制，定期评估康复进度"
            ])
        elif risk_level == RiskLevel.HIGH:
            guidance_parts.extend([
                "强烈建议避免执行原动作",
                "请在专业医生或理疗师指导下进行训练",
                "优先考虑完全不涉及受伤部位的替代动作"
            ])
        elif risk_level == RiskLevel.MODERATE:
            guidance_parts.extend([
                "建议谨慎修改动作或寻找替代方案",
                "降低训练强度和频率",
                "密切监控受伤部位反应"
            ])
        else:
            guidance_parts.extend([
                "可以进行适度调整",
                "注意动作质量和控制",
                "定期评估康复进度"
            ])

        guidance_parts.append("⚠️ 任何情况下，如出现疼痛应立即停止训练并寻求医疗建议")

        return " | ".join(guidance_parts)

    def _generate_safety_recommendations(
        self,
        original_exercise: Dict[str, Any],
        injury_info: Dict[str, Any],
        modifications: List[ExerciseModification],
        user_profile: Dict[str, Any]
    ) -> List[str]:
        """生成安全建议"""
        recommendations = [
            "在开始任何修改前咨询医疗专业人员",
            "充分热身，特别关注受伤部位",
            "使用比平时更轻的重量开始",
            "保持动作缓慢且完全可控",
            "训练过程中持续监控受伤部位感受",
            "如有疼痛立即停止训练",
            "定期评估康复进度并调整训练计划"
        ]

        # 基于修改类型添加特定建议
        for mod in modifications:
            if mod.modification_type == ModificationType.ALTERNATIVE:
                recommendations.extend([
                    f"选择{mod.modified_name_zh}作为替代动作",
                    "学习正确的替代动作技术",
                    "逐步增加替代动作的训练量"
                ])
            elif mod.modification_type == ModificationType.MODIFIED_VERSION:
                recommendations.extend([
                    f"严格遵守{mod.modified_name_zh}的修改要求",
                    "使用辅助器械确保安全",
                    "寻求专业教练指导"
                ])
            elif mod.modification_type == ModificationType.AVOID:
                recommendations.extend([
                    "完全避免执行原动作",
                    "寻找完全不涉及受伤部位的训练动作",
                    "专注于其他肌群的训练"
                ])

        # 基于受伤部位添加特定建议
        injury_type = injury_info.get("injury_type", "")
        if "肩" in injury_type:
            recommendations.extend([
                "特别注意肩关节稳定性",
                "加强肩胛骨周围肌群训练",
                "避免长时间重复动作"
            ])
        elif "腰" in injury_type:
            recommendations.extend([
                "强化核心稳定性训练",
                "学习正确的脊柱中立位",
                "避免突然的扭转或弯曲动作"
            ])

        # 基于用户档案添加建议
        if user_profile.get("fitness_profile", {}).get("training_level") == "beginner":
            recommendations.extend([
                "新手建议从最安全的替代动作开始",
                "重视动作技术学习而非训练强度"
            ])

        # 去重
        return list(set(recommendations))
