"""
损伤风险评估器 MCP工具

完全基于用户档案和Neo4j数据
参考TypeScript的injury-risk-assessor实现

功能特性：
- 基于用户档案评估个人损伤风险因素
- 基于训练计划分析动作组合风险
- 提供个性化预防建议和训练调整方案
- 支持风险容忍度设置和预防计划生成

作者: BUILD_BODY Team
版本: v1.0.0
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timedelta
import logging

from ...mcp_tools.base_tool import BaseMCPTool
from src.utils.neo4j_result_handler import Neo4jResultHandler

logger = logging.getLogger(__name__)


# =============================================================================
# 输入Schema定义
# =============================================================================

class InjuryRiskAssessorInput(BaseModel):
    """损伤风险评估器输入"""
    user_id: str = Field(..., description="用户ID，用于获取个人风险档案")
    planned_exercises: List[str] = Field(..., description="计划执行的动作ID列表")
    training_intensity: Literal["low", "moderate", "high"] = Field(..., description="训练强度")
    session_duration_minutes: int = Field(..., ge=15, le=180, description="训练时长（分钟）")
    include_prevention_plan: bool = Field(True, description="是否包含预防计划")
    risk_tolerance_level: Literal["low", "moderate", "high"] = Field("moderate", description="风险容忍水平")
    previous_injuries: Optional[List[str]] = Field(None, description="历史损伤（可选）")
    current_pain_areas: Optional[List[str]] = Field(None, description="当前疼痛部位（可选）")


# =============================================================================
# 输出类型定义
# =============================================================================

class RiskFactor(BaseModel):
    """风险因素"""
    category: str
    factor: str
    risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    score: float
    description: str
    modifiable: bool


class ExerciseRecommendations(BaseModel):
    """动作建议"""
    can_perform: bool
    modifications: Optional[List[str]] = None
    precautions: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None


class ExerciseRiskProfile(BaseModel):
    """动作风险档案"""
    exercise_id: str
    exercise_name_zh: str
    exercise_name_en: str
    category: str
    inherent_risk: float
    user_specific_risk: float
    combined_risk_score: float
    risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    risk_factors: List[RiskFactor]
    recommendations: ExerciseRecommendations


class BodyPartRisk(BaseModel):
    """身体部位风险"""
    body_part: str
    risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    risk_score: float
    involved_exercises: List[str]
    primary_concerns: List[str]
    prevention_focus: List[str]


class PreventionPlan(BaseModel):
    """预防计划"""
    immediate_actions: List[str]
    training_modifications: List[str]
    monitoring_protocol: List[str]
    recovery_strategies: List[str]
    when_to_seek_help: List[str]


class InjuryRiskAssessorOutput(BaseModel):
    """损伤风险评估器输出"""
    success: bool
    tool_name: str
    user_id: str
    
    # 总体风险评估
    overall_risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    overall_risk_score: float
    risk_summary: str
    
    # 个人风险因素
    personal_risk_factors: List[RiskFactor]
    
    # 动作风险分析
    exercise_risk_profiles: List[ExerciseRiskProfile]
    
    # 身体部位风险
    body_part_risks: List[BodyPartRisk]
    
    # 预防计划
    prevention_plan: Optional[PreventionPlan] = None
    
    # 建议
    recommendations: List[str]
    
    execution_time_ms: float
    confidence_score: float


# =============================================================================
# 损伤风险评估器类
# =============================================================================

class InjuryRiskAssessor(BaseMCPTool):
    """损伤风险评估器"""
    
    def get_name(self) -> str:
        return "injury_risk_assessor"
    
    def get_description(self) -> str:
        return "损伤风险评估器 - 基于用户档案和Neo4j数据的个性化风险评估"
    
    def get_category(self) -> str:
        return "safety"
    
    def get_input_schema(self) -> type[BaseModel]:
        return InjuryRiskAssessorInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return InjuryRiskAssessorOutput
    
    def get_complexity(self) -> str:
        return "complex"
    
    def get_estimated_duration(self) -> float:
        return 2000.0
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["neo4j", "user_profile_mcp"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行损伤风险评估
        
        流程：
        1. 获取用户档案（获取风险相关数据）
        2. 分析个人风险因素
        3. 获取动作信息（从Neo4j）
        4. 评估每个动作的风险
        5. 分析身体部位风险
        6. 生成预防计划（如果需要）
        7. 生成总体评估和建议
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: 获取用户档案
            user_profile = await self._get_user_profile(input_data.get("user_id"))
            
            # Step 2: 分析个人风险因素
            personal_risk_factors = await self._analyze_personal_risk_factors(
                input_data, user_profile
            )
            
            # Step 3: 获取动作信息（从Neo4j）
            exercise_info_map = await self._get_exercises_info(
                input_data["planned_exercises"]
            )
            
            # Step 4: 评估每个动作的风险
            exercise_risk_profiles = await self._assess_exercise_risks(
                input_data,
                exercise_info_map,
                user_profile
            )
            
            # Step 5: 分析身体部位风险
            body_part_risks = self._analyze_body_part_risks(
                exercise_risk_profiles, user_profile
            )
            
            # Step 6: 生成预防计划（如果需要）
            prevention_plan = None
            if input_data.get("include_prevention_plan", True):
                prevention_plan = self._generate_prevention_plan(
                    personal_risk_factors,
                    exercise_risk_profiles,
                    body_part_risks
                )
            
            # Step 7: 生成总体评估和建议
            overall_assessment = self._generate_overall_assessment(
                personal_risk_factors,
                exercise_risk_profiles,
                body_part_risks
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": "injury_risk_assessor",
                "user_id": input_data["user_id"],
                "overall_risk_level": overall_assessment["risk_level"],
                "overall_risk_score": overall_assessment["risk_score"],
                "risk_summary": overall_assessment["summary"],
                "personal_risk_factors": [f.model_dump() for f in personal_risk_factors],
                "exercise_risk_profiles": [p.model_dump() for p in exercise_risk_profiles],
                "body_part_risks": [r.model_dump() for r in body_part_risks],
                "prevention_plan": prevention_plan.model_dump() if prevention_plan else None,
                "recommendations": overall_assessment["recommendations"],
                "execution_time_ms": execution_time_ms,
                "confidence_score": 90.0
            }
            
            self.logger.info(
                f"✅ 损伤风险评估完成: 用户{input_data['user_id']}, "
                f"总体风险{overall_assessment['risk_level']}, "
                f"评分{overall_assessment['risk_score']:.1f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 损伤风险评估失败: {e}", exc_info=True)
            raise
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户档案（可选）"""
        # TODO: 如果有UserProfileClient，调用它
        # 目前返回空字典
        return {}
    
    async def _analyze_personal_risk_factors(
        self,
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> List[RiskFactor]:
        """分析个人风险因素"""
        risk_factors = []
        
        # 基于年龄的风险
        if user_profile.get("demographic_profile", {}).get("age"):
            age = user_profile["demographic_profile"]["age"]
            if age >= 60:
                risk_factors.append(RiskFactor(
                    category="年龄",
                    factor="高龄训练者",
                    risk_level="HIGH",
                    score=7.0,
                    description="年龄增长导致恢复能力下降，损伤风险增加",
                    modifiable=False
                ))
            elif age >= 40:
                risk_factors.append(RiskFactor(
                    category="年龄",
                    factor="中年训练者",
                    risk_level="MODERATE",
                    score=5.0,
                    description="需要更多热身和恢复时间",
                    modifiable=True
                ))
        
        # 基于损伤历史的风险
        if user_profile.get("health_profile", {}).get("injury_history"):
            six_months_ago = datetime.now() - timedelta(days=180)
            recent_injuries = [
                injury for injury in user_profile["health_profile"]["injury_history"]
                if datetime.fromisoformat(injury.get("date", "2000-01-01")) > six_months_ago
            ]
            
            for injury in recent_injuries:
                risk_factors.append(RiskFactor(
                    category="损伤历史",
                    factor=injury.get("type", "未知损伤"),
                    risk_level="HIGH",
                    score=8.0,
                    description=f"{injury.get('type', '损伤')}可能影响当前训练，需要特别小心",
                    modifiable=True
                ))
        
        # 基于当前症状的风险
        current_pain_areas = input_data.get("current_pain_areas") or \
                           user_profile.get("health_profile", {}).get("current_symptoms", [])
        if current_pain_areas:
            risk_factors.append(RiskFactor(
                category="当前状态",
                factor="存在疼痛或不适",
                risk_level="CRITICAL",
                score=9.0,
                description="当前疼痛可能加剧，建议暂停训练并寻求医疗建议",
                modifiable=False
            ))
        
        # 基于训练水平的风险
        training_level = user_profile.get("fitness_profile", {}).get("training_level")
        if training_level == "beginner":
            risk_factors.append(RiskFactor(
                category="训练经验",
                factor="新手训练者",
                risk_level="MODERATE",
                score=5.0,
                description="技术不熟练可能导致错误动作模式",
                modifiable=True
            ))
        
        # 基于风险容忍度调整
        if input_data.get("risk_tolerance_level") == "low":
            for factor in risk_factors:
                factor.score = min(10.0, factor.score + 1.0)
                if factor.risk_level == "LOW":
                    factor.risk_level = "MODERATE"
                elif factor.risk_level == "MODERATE":
                    factor.risk_level = "HIGH"
        
        return risk_factors

    
    async def _get_exercises_info(
        self,
        exercise_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        获取动作信息（从Neo4j）
        
        使用Neo4jResultHandler处理查询结果，解决：
        1. 'list' object has no attribute 'records' 错误
        2. injury_risk_factors属性不存在的情况
        3. 空结果时返回默认低风险评估
        
        Args:
            exercise_ids: 动作ID列表
            
        Returns:
            动作信息字典，key为exercise_id
        """
        exercise_map = {}
        
        # 如果没有动作ID，直接返回空字典
        if not exercise_ids:
            self.logger.warning("没有提供动作ID，返回空结果")
            return exercise_map
        
        query = """
        MATCH (e:Exercise)
        WHERE e.id IN $exercise_ids
        RETURN e.id as exercise_id,
               e.name_zh,
               e.name_en,
               e.category,
               e.difficulty_zh,
               e.safety_level,
               e.injury_risk_factors,
               e.primary_muscle_zh
        """
        
        try:
            result = await self.neo4j_client.execute_query(query, {"exercise_ids": exercise_ids})
            
            # 使用Neo4jResultHandler统一处理结果
            records = Neo4jResultHandler.to_records(result)
            
            if not records:
                self.logger.warning(f"Neo4j查询返回空结果，动作ID: {exercise_ids}")
                # 为每个动作ID返回默认低风险评估
                for exercise_id in exercise_ids:
                    exercise_map[exercise_id] = self._get_default_exercise_info(exercise_id)
                return exercise_map
            
            for record in records:
                exercise_id = Neo4jResultHandler.get_property(record, "exercise_id")
                if not exercise_id:
                    continue
                    
                # 安全获取所有属性，处理属性不存在的情况
                exercise_map[exercise_id] = {
                    "exercise_id": exercise_id,
                    "name_zh": Neo4jResultHandler.get_property(record, "name_zh", "未知动作"),
                    "name_en": Neo4jResultHandler.get_property(record, "name_en", "Unknown"),
                    "category": Neo4jResultHandler.get_property(record, "category", "未分类"),
                    "difficulty": Neo4jResultHandler.get_property(record, "difficulty", "中级"),
                    "safety_level": Neo4jResultHandler.get_property(record, "safety_level", "MEDIUM_RISK"),
                    # 特别处理injury_risk_factors，确保返回列表
                    "injury_risk_factors": Neo4jResultHandler.safe_list(
                        Neo4jResultHandler.get_property(record, "injury_risk_factors"),
                        default=[]
                    ),
                    "primary_muscle_zh": Neo4jResultHandler.safe_list(
                        Neo4jResultHandler.get_property(record, "primary_muscle_zh"),
                        default=[]
                    )
                }
            
            # 检查是否有未找到的动作ID，为其添加默认信息
            for exercise_id in exercise_ids:
                if exercise_id not in exercise_map:
                    self.logger.warning(f"动作ID {exercise_id} 在Neo4j中未找到，使用默认值")
                    exercise_map[exercise_id] = self._get_default_exercise_info(exercise_id)
            
            self.logger.info(f"成功获取 {len(exercise_map)} 个动作信息")
            return exercise_map
            
        except Exception as e:
            self.logger.error(f"Neo4j查询动作信息失败: {e}", exc_info=True)
            # 发生异常时，为所有动作ID返回默认低风险评估
            for exercise_id in exercise_ids:
                exercise_map[exercise_id] = self._get_default_exercise_info(exercise_id)
            return exercise_map
    
    def _get_default_exercise_info(self, exercise_id: str) -> Dict[str, Any]:
        """
        获取默认的动作信息（低风险评估）
        
        当Neo4j查询失败或返回空结果时使用
        
        Args:
            exercise_id: 动作ID
            
        Returns:
            默认的动作信息字典
        """
        return {
            "exercise_id": exercise_id,
            "name_zh": "未知动作",
            "name_en": "Unknown Exercise",
            "category": "未分类",
            "difficulty": "中级",
            "safety_level": "LOW_RISK",  # 默认低风险
            "injury_risk_factors": [],
            "primary_muscle_zh": []
        }
    
    async def _assess_exercise_risks(
        self,
        input_data: Dict[str, Any],
        exercise_info_map: Dict[str, Dict[str, Any]],
        user_profile: Dict[str, Any]
    ) -> List[ExerciseRiskProfile]:
        """评估动作风险"""
        profiles = []
        
        for exercise_id in input_data["planned_exercises"]:
            exercise_info = exercise_info_map.get(exercise_id)
            
            if not exercise_info:
                # 未找到动作信息
                profiles.append(ExerciseRiskProfile(
                    exercise_id=exercise_id,
                    exercise_name_zh="Unknown",
                    exercise_name_en="Unknown",
                    category="Unknown",
                    inherent_risk=5.0,
                    user_specific_risk=5.0,
                    combined_risk_score=5.0,
                    risk_level="MODERATE",
                    risk_factors=[RiskFactor(
                        category="数据",
                        factor="未找到动作信息",
                        risk_level="MODERATE",
                        score=5.0,
                        description="无法评估风险，建议确认动作ID",
                        modifiable=True
                    )],
                    recommendations=ExerciseRecommendations(
                        can_perform=True,
                        modifications=["确认动作信息"],
                        precautions=[],
                        alternatives=[]
                    )
                ))
                continue
            
            # 评估固有风险
            inherent_risk = self._assess_inherent_risk(exercise_info)
            
            # 评估用户特定风险
            user_specific_risk = self._assess_user_specific_risk(
                exercise_info, user_profile, input_data
            )
            
            # 计算综合风险评分
            combined_risk_score = (inherent_risk + user_specific_risk) / 2
            
            risk_level = self._map_score_to_risk_level(combined_risk_score)
            
            # 分析风险因素（包含禁忌关系查询）
            risk_factors = await self._analyze_exercise_risk_factors(
                exercise_info, user_profile, input_data
            )
            
            # 生成建议
            recommendations = self._generate_exercise_risk_recommendations(
                exercise_info,
                combined_risk_score,
                risk_level,
                user_profile
            )
            
            profiles.append(ExerciseRiskProfile(
                exercise_id=exercise_id,
                exercise_name_zh=exercise_info["name_zh"],
                exercise_name_en=exercise_info["name_en"],
                category=exercise_info["category"],
                inherent_risk=inherent_risk,
                user_specific_risk=user_specific_risk,
                combined_risk_score=combined_risk_score,
                risk_level=risk_level,
                risk_factors=risk_factors,
                recommendations=recommendations
            ))
        
        return profiles
    
    def _assess_inherent_risk(self, exercise_info: Dict[str, Any]) -> float:
        """评估固有风险"""
        risk = 3.0  # 基础风险
        
        # 基于安全等级
        safety_level = exercise_info.get("safety_level", "MEDIUM_RISK")
        if safety_level == "HIGH_RISK":
            risk += 4.0
        elif safety_level == "MEDIUM_RISK":
            risk += 2.0
        
        # 基于难度 - 使用统一字段名
        difficulty = exercise_info.get("difficulty_zh") or exercise_info.get("difficulty_en") or "中级"
        if difficulty == "高级":
            risk += 2.0
        elif difficulty == "中级":
            risk += 1.0
        
        # 基于动作类别
        category = exercise_info.get("category", "")
        if "复合动作" in category:
            risk += 1.0
        
        return min(10.0, risk)
    
    def _assess_user_specific_risk(
        self,
        exercise_info: Dict[str, Any],
        user_profile: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> float:
        """评估用户特定风险"""
        risk = 2.0  # 基础风险
        
        # 基于损伤历史
        injury_history = user_profile.get("health_profile", {}).get("injury_history", [])
        if injury_history:
            injury_risk_factors = exercise_info.get("injury_risk_factors", [])
            relevant_injuries = [
                injury for injury in injury_history
                if any(
                    factor in injury.get("type", "") or injury.get("type", "") in factor
                    for factor in injury_risk_factors
                )
            ]
            risk += len(relevant_injuries) * 2.0
        
        # 基于训练强度
        training_intensity = input_data.get("training_intensity", "moderate")
        if training_intensity == "high":
            risk += 2.0
        elif training_intensity == "moderate":
            risk += 1.0
        
        # 基于训练时长
        session_duration = input_data.get("session_duration_minutes", 60)
        if session_duration > 90:
            risk += 1.0
        
        return min(10.0, risk)
    
    async def _analyze_exercise_risk_factors(
        self,
        exercise_info: Dict[str, Any],
        user_profile: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> List[RiskFactor]:
        """分析动作风险因素（包含CONTRAINDICATED_FOR关系）"""
        factors = []
        
        # 基于动作固有风险因素
        injury_risk_factors = exercise_info.get("injury_risk_factors", [])
        for factor in injury_risk_factors:
            factors.append(RiskFactor(
                category="动作特性",
                factor=factor,
                risk_level="MODERATE",
                score=5.0,
                description=f"{exercise_info['name_zh']}的固有风险因素",
                modifiable=False
            ))
        
        # 查询CONTRAINDICATED_FOR关系（基于用户损伤历史）
        injury_history = user_profile.get("health_profile", {}).get("injury_history", [])
        current_pain = input_data.get("current_pain_areas", [])
        previous_injuries = input_data.get("previous_injuries", [])
        
        # 合并所有损伤信息
        all_injuries = set()
        for injury in injury_history:
            all_injuries.add(injury.get("type", ""))
        all_injuries.update(current_pain or [])
        all_injuries.update(previous_injuries or [])
        all_injuries.discard("")
        
        if all_injuries:
            # 查询禁忌关系
            contraindications = await self._query_contraindications(
                exercise_info.get("exercise_id"),
                list(all_injuries)
            )
            
            # 根据severity字段生成风险因素
            for contra in contraindications:
                severity = contra.get("severity", "relative")
                injury_name = contra.get("injury_name_zh", "损伤")
                reason = contra.get("reason", "基于医学指导")
                
                if severity == "absolute":
                    factors.append(RiskFactor(
                        category="绝对禁忌",
                        factor=f"{injury_name}",
                        risk_level="CRITICAL",
                        score=10.0,
                        description=f"⛔ 绝对禁忌：{reason}",
                        modifiable=False
                    ))
                elif severity == "relative":
                    factors.append(RiskFactor(
                        category="相对禁忌",
                        factor=f"{injury_name}",
                        risk_level="HIGH",
                        score=7.0,
                        description=f"⚠️ 相对禁忌：{reason}",
                        modifiable=True
                    ))
                elif severity == "caution":
                    factors.append(RiskFactor(
                        category="谨慎使用",
                        factor=f"{injury_name}",
                        risk_level="MODERATE",
                        score=5.0,
                        description=f"💡 谨慎使用：{reason}",
                        modifiable=True
                    ))
        
        # 基于用户档案的一般风险因素
        for injury in injury_history:
            # 如果没有在禁忌关系中找到，添加通用风险因素
            if not any(f.factor == injury.get("type", "") for f in factors):
                factors.append(RiskFactor(
                    category="个人历史",
                    factor=injury.get("type", "未知损伤"),
                    risk_level="HIGH",
                    score=7.0,
                    description=f"用户有{injury.get('type', '损伤')}历史，需要特别关注",
                    modifiable=True
                ))
        
        return factors
    
    async def _query_contraindications(
        self,
        exercise_id: str,
        injury_types: List[str]
    ) -> List[Dict[str, Any]]:
        """
        查询动作的禁忌关系
        
        使用Neo4jResultHandler处理查询结果
        
        Args:
            exercise_id: 动作ID
            injury_types: 损伤类型列表
            
        Returns:
            禁忌关系列表
        """
        if not exercise_id or not injury_types:
            return []
        
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        OPTIONAL MATCH (e)-[r:CONTRAINDICATED_FOR]->(inj:InjuryType)
        WHERE inj.name_zh IN $injury_types
           OR inj.name_en IN $injury_types
           OR inj.category_zh IN $injury_types
        
        RETURN
          inj.name_zh as injury_name_zh,
          inj.name_en as injury_name_en,
          r.severity as severity,
          r.reason as reason
        """
        
        try:
            result = await self.neo4j_client.execute_query(query, {
                "exercise_id": exercise_id,
                "injury_types": injury_types
            })
            
            # 使用Neo4jResultHandler统一处理结果
            records = Neo4jResultHandler.to_records(result)
            
            contraindications = []
            for record in records:
                injury_name_zh = Neo4jResultHandler.get_property(record, "injury_name_zh")
                if injury_name_zh:
                    contraindications.append({
                        "injury_name_zh": injury_name_zh,
                        "injury_name_en": Neo4jResultHandler.get_property(record, "injury_name_en", ""),
                        "severity": Neo4jResultHandler.get_property(record, "severity", "relative"),
                        "reason": Neo4jResultHandler.get_property(record, "reason", "基于医学指导")
                    })
            
            return contraindications
            
        except Exception as e:
            self.logger.warning(f"查询禁忌关系失败: {e}")
            return []
    
    def _map_score_to_risk_level(self, score: float) -> Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]:
        """映射评分到风险等级"""
        if score >= 8.0:
            return "CRITICAL"
        elif score >= 6.0:
            return "HIGH"
        elif score >= 4.0:
            return "MODERATE"
        else:
            return "LOW"
    
    def _generate_exercise_risk_recommendations(
        self,
        exercise_info: Dict[str, Any],
        risk_score: float,
        risk_level: str,
        user_profile: Dict[str, Any]
    ) -> ExerciseRecommendations:
        """生成动作风险建议"""
        recommendations = ExerciseRecommendations(
            can_perform=risk_level != "CRITICAL",
            modifications=[],
            precautions=[],
            alternatives=[]
        )
        
        if risk_level == "CRITICAL":
            recommendations.precautions = ["建议避免执行此动作"]
            recommendations.alternatives = ["寻求专业医疗建议"]
            return recommendations
        
        if risk_level == "HIGH":
            recommendations.modifications = [
                "降低训练重量和强度",
                "增加热身时间"
            ]
            recommendations.precautions = ["在专业人士指导下进行"]
        
        if risk_level == "MODERATE":
            recommendations.precautions = [
                "注意动作质量和控制",
                "密切监控身体反应"
            ]
        
        return recommendations
    
    def _analyze_body_part_risks(
        self,
        exercise_profiles: List[ExerciseRiskProfile],
        user_profile: Dict[str, Any]
    ) -> List[BodyPartRisk]:
        """分析身体部位风险"""
        body_part_risk_map: Dict[str, Dict[str, Any]] = {}
        
        for profile in exercise_profiles:
            # 从动作推断涉及的身体部位
            body_parts = self._infer_body_parts_from_exercise(
                profile.category, profile.exercise_name_zh
            )
            
            for body_part in body_parts:
                if body_part not in body_part_risk_map:
                    body_part_risk_map[body_part] = {
                        "body_part": body_part,
                        "risk_level": "LOW",
                        "risk_score": 0.0,
                        "involved_exercises": [],
                        "primary_concerns": [],
                        "prevention_focus": []
                    }
                
                existing = body_part_risk_map[body_part]
                existing["involved_exercises"].append(profile.exercise_name_zh)
                existing["risk_score"] += profile.combined_risk_score / len(body_parts)
        
        # 转换为BodyPartRisk列表
        body_part_risks = []
        for body_part, risk_data in body_part_risk_map.items():
            avg_score = risk_data["risk_score"] / len(risk_data["involved_exercises"])
            risk_level = self._map_score_to_risk_level(avg_score)
            prevention_focus = self._generate_prevention_focus(body_part, avg_score)
            
            body_part_risks.append(BodyPartRisk(
                body_part=body_part,
                risk_level=risk_level,
                risk_score=round(avg_score, 1),
                involved_exercises=risk_data["involved_exercises"],
                primary_concerns=[],
                prevention_focus=prevention_focus
            ))
        
        return body_part_risks
    
    def _infer_body_parts_from_exercise(
        self,
        category: str,
        exercise_name: str
    ) -> List[str]:
        """从动作推断涉及的身体部位"""
        body_part_map = {
            "胸": ["胸部", "肩部", "三头肌"],
            "背": ["背部", "肩部", "二头肌"],
            "腿": ["腿部", "臀部", "核心"],
            "肩": ["肩部", "上背部"],
            "手臂": ["手臂", "肩部"],
            "核心": ["核心", "腰部"]
        }
        
        for key, body_parts in body_part_map.items():
            if key in category or key in exercise_name:
                return body_parts
        
        return ["全身"]
    
    def _generate_prevention_focus(
        self,
        body_part: str,
        risk_score: float
    ) -> List[str]:
        """生成预防重点"""
        focus = []
        
        if risk_score >= 6.0:
            focus.extend([
                "充分热身和拉伸",
                "使用适当重量",
                "保持正确姿势"
            ])
        elif risk_score >= 4.0:
            focus.extend([
                "注意动作质量",
                "循序渐进"
            ])
        
        return focus
    
    def _generate_prevention_plan(
        self,
        personal_risk_factors: List[RiskFactor],
        exercise_profiles: List[ExerciseRiskProfile],
        body_part_risks: List[BodyPartRisk]
    ) -> PreventionPlan:
        """生成预防计划"""
        plan = PreventionPlan(
            immediate_actions=[],
            training_modifications=[],
            monitoring_protocol=[],
            recovery_strategies=[],
            when_to_seek_help=[]
        )
        
        # 基于个人风险因素生成行动
        for factor in personal_risk_factors:
            if factor.category == "当前状态" and factor.risk_level == "CRITICAL":
                plan.immediate_actions.append("立即停止训练，寻求医疗建议")
            elif factor.modifiable:
                plan.training_modifications.append(f"针对{factor.factor}进行调整")
        
        # 基于动作风险生成预防措施
        high_risk_exercises = [
            p for p in exercise_profiles
            if p.risk_level in ["HIGH", "CRITICAL"]
        ]
        if high_risk_exercises:
            plan.immediate_actions.append("对高风险动作采取额外预防措施")
            plan.monitoring_protocol.append("训练过程中持续监控身体反应")
        
        # 基于身体部位风险生成恢复策略
        for risk in body_part_risks:
            if risk.risk_level in ["HIGH", "CRITICAL"]:
                plan.recovery_strategies.append(f"{risk.body_part}需要额外关注和恢复")
        
        # 添加通用建议
        plan.monitoring_protocol.append("记录训练过程中的不适感受")
        plan.recovery_strategies.append("保证充足睡眠和营养")
        plan.when_to_seek_help.append("出现持续疼痛或功能受限")
        
        return plan
    
    def _generate_overall_assessment(
        self,
        personal_risk_factors: List[RiskFactor],
        exercise_profiles: List[ExerciseRiskProfile],
        body_part_risks: List[BodyPartRisk]
    ) -> Dict[str, Any]:
        """生成总体评估"""
        # 计算总体风险评分
        personal_risk_score = (
            sum(f.score for f in personal_risk_factors) / max(1, len(personal_risk_factors))
            if personal_risk_factors else 0.0
        )
        
        exercise_risk_score = (
            sum(p.combined_risk_score for p in exercise_profiles) / max(1, len(exercise_profiles))
            if exercise_profiles else 0.0
        )
        
        body_part_risk_score = (
            sum(r.risk_score for r in body_part_risks) / max(1, len(body_part_risks))
            if body_part_risks else 0.0
        )
        
        overall_score = (personal_risk_score + exercise_risk_score + body_part_risk_score) / 3
        overall_level = self._map_score_to_risk_level(overall_score)
        
        # 生成总结
        summary_parts = []
        if overall_level == "LOW":
            summary_parts.append("风险较低，可以安全进行训练")
        elif overall_level == "MODERATE":
            summary_parts.append("存在中等风险，需要注意训练安全")
        elif overall_level == "HIGH":
            summary_parts.append("风险较高，建议调整训练计划")
        else:
            summary_parts.append("风险很高，建议寻求专业医疗建议")
        
        # 生成建议
        recommendations = []
        if overall_level != "LOW":
            recommendations.extend([
                "充分热身是必须的",
                "密切监控身体反应"
            ])
        
        if any(p.risk_level == "HIGH" for p in exercise_profiles):
            recommendations.append("对高风险动作采取额外预防措施")
        
        if any(r.risk_level == "HIGH" for r in body_part_risks):
            recommendations.append("重点关注高风险身体部位的保护")
        
        return {
            "risk_level": overall_level,
            "risk_score": round(overall_score, 1),
            "summary": "；".join(summary_parts),
            "recommendations": recommendations
        }
