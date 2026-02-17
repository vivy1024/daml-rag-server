"""
禁忌症检查器 MCP工具

功能特性：
- 基于用户档案获取健康状况和损伤历史
- 基于Neo4j CONTRAINDICATED_FOR关系查询禁忌动作
- 提供详细的风险评估和安全建议
- 支持严格模式和推荐模式

作者: BUILD_BODY Team
版本: v2.0.0
基于: 用户档案MCP + Neo4j v4.0.0
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import time

from ..base_tool import BaseMCPTool


# =============================================================================
# 输入Schema定义
# =============================================================================

class ContraindicationsCheckerInput(BaseModel):
    """禁忌症检查器输入Schema"""
    user_id: str = Field(..., description="用户ID，用于获取健康状况")
    exercise_ids: List[str] = Field(..., description="要检查的动作ID列表")
    health_conditions: Optional[List[str]] = Field(None, description="额外健康状况（可选）")
    include_recommendations: bool = Field(True, description="是否包含安全建议")
    strict_mode: bool = Field(False, description="严格模式：更保守的安全阈值")
    
    # 新增参数 - Requirements 4.5
    injured_joints: Optional[List[str]] = Field(None, description="受伤关节列表（可选），用于INVOLVES_JOINT关系查询")
    postural_issues: Optional[List[str]] = Field(None, description="体态问题列表（可选），用于体态问题禁忌检查")


# =============================================================================
# 输出类型定义
# =============================================================================

class ContraindicationDetail(BaseModel):
    """单个禁忌症详情"""
    exercise_id: str
    exercise_name_zh: str
    exercise_name_en: str
    contraindication_type: str
    risk_level: Literal['LOW', 'MODERATE', 'HIGH', 'CRITICAL']
    reason: str
    severity_score: int
    body_part_affected: str
    medical_source: Optional[str] = None


class ExerciseRecommendations(BaseModel):
    """动作建议"""
    can_perform: bool
    modifications: List[str] = []
    alternatives: List[str] = []
    precautions: List[str] = []
    medical_consultation_needed: bool


class ExerciseContraindicationStatus(BaseModel):
    """动作禁忌症状态"""
    exercise_id: str
    exercise_name_zh: str
    exercise_name_en: str
    category: str
    difficulty: str
    safety_level: str
    
    # 禁忌状态
    has_contraindications: bool
    contraindications: List[ContraindicationDetail]
    total_risk_score: int
    max_risk_level: str
    
    # 建议
    recommendations: ExerciseRecommendations


class OverallAssessment(BaseModel):
    """总体评估"""
    risk_level: Literal['LOW', 'MODERATE', 'HIGH', 'CRITICAL']
    total_risk_score: int
    critical_issues: List[str]
    recommendations: List[str]


class ContraindicationsCheckerOutput(BaseModel):
    """禁忌症检查器输出Schema"""
    success: bool
    tool_name: str
    user_id: str
    checked_exercises: int
    exercises_with_contraindications: int
    high_risk_exercises: int
    
    # 详细结果
    exercise_results: List[ExerciseContraindicationStatus]
    
    # 总体评估
    overall_assessment: OverallAssessment
    
    # 医学建议
    medical_guidance: str
    
    execution_time_ms: float
    confidence_score: int


# =============================================================================
# 禁忌症检查器类
# =============================================================================

class ContraindicationsChecker(BaseMCPTool):
    """禁忌症检查器 - 基于用户档案MCP和Neo4j数据的医学安全检查"""
    
    def get_name(self) -> str:
        return "contraindications_checker"
    
    def get_description(self) -> str:
        return "禁忌症检查器 - 基于用户档案MCP和Neo4j数据的医学安全检查"
    
    def get_category(self) -> str:
        return "safety"
    
    def get_input_schema(self) -> type[BaseModel]:
        return ContraindicationsCheckerInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return ContraindicationsCheckerOutput
    
    def get_complexity(self) -> str:
        return "complex"
    
    def get_estimated_duration(self) -> float:
        return 1500.0  # 1.5秒
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["neo4j", "user_profile_mcp"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行禁忌症检查
        
        流程：
        1. 获取用户档案（获取健康状况和损伤历史）
        2. 构建健康状况列表
        3. 查询每个动作的禁忌症
        4. 生成总体评估
        5. 生成医学建议
        """
        start_time = time.time()
        
        try:
            # Step 1: 获取用户档案
            user_profile = await self._get_user_profile(input_data.get("user_id"))
            
            # Step 2: 构建健康状况列表
            health_conditions = self._build_health_conditions(input_data, user_profile)
            
            # Step 3: 查询每个动作的禁忌症
            exercise_results = await self._check_exercises_contraindications(
                input_data["exercise_ids"],
                health_conditions,
                input_data.get("strict_mode", False)
            )
            
            # Step 4: 生成总体评估
            overall_assessment = self._generate_overall_assessment(exercise_results, user_profile)
            
            # Step 5: 生成医学建议
            medical_guidance = self._generate_medical_guidance(overall_assessment, user_profile)
            
            # 统计数据
            checked_count = len(input_data["exercise_ids"])
            contraindications_count = sum(1 for r in exercise_results if r["has_contraindications"])
            high_risk_count = sum(
                1 for r in exercise_results 
                if r["max_risk_level"] in ["HIGH", "CRITICAL"]
            )
            
            result = {
                "success": True,
                "tool_name": "contraindications_checker",
                "user_id": input_data["user_id"],
                "checked_exercises": checked_count,
                "exercises_with_contraindications": contraindications_count,
                "high_risk_exercises": high_risk_count,
                "exercise_results": exercise_results,
                "overall_assessment": overall_assessment,
                "medical_guidance": medical_guidance,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "confidence_score": 95
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"禁忌症检查失败: {e}", exc_info=True)
            raise
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户档案"""
        # 方式1: 通过BaseMCPTool注入的backend_client
        if hasattr(self, 'backend_client') and self.backend_client:
            try:
                profile = await self.backend_client.get_user_profile(user_id)
                if profile:
                    return profile
            except Exception as e:
                self.logger.warning(f"Backend client获取用户档案失败: {e}")

        # 方式2: 通过user_profile_provider
        if hasattr(self, 'user_profile_provider') and self.user_profile_provider:
            try:
                profile = await self.user_profile_provider(user_id)
                if profile:
                    return profile
            except Exception as e:
                self.logger.warning(f"User profile provider获取用户档案失败: {e}")

        # Fallback: 返回空字典
        self.logger.info(f"无可用的用户档案获取方式，返回空档案: user_id={user_id}")
        return {}
    
    def _build_health_conditions(
        self, 
        input_data: Dict[str, Any], 
        user_profile: Dict[str, Any]
    ) -> List[str]:
        """
        构建健康状况列表（整合用户档案和输入）
        """
        conditions = set()
        
        # 从用户档案获取
        health_profile = user_profile.get("health_profile", {})
        
        # 慢性病
        chronic_conditions = health_profile.get("chronic_conditions", [])
        for condition in chronic_conditions:
            if isinstance(condition, dict):
                conditions.add(condition.get("name", ""))
                if condition.get("severity"):
                    conditions.add(f"{condition.get('name')}_{condition.get('severity')}")
            else:
                conditions.add(str(condition))
        
        # 损伤史
        injury_history = health_profile.get("injury_history", [])
        for injury in injury_history:
            if isinstance(injury, dict):
                conditions.add(injury.get("type", ""))
                if injury.get("body_part"):
                    conditions.add(f"{injury.get('type')}_{injury.get('body_part')}")
            else:
                conditions.add(str(injury))
        
        # 当前症状
        current_symptoms = health_profile.get("current_symptoms", [])
        for symptom in current_symptoms:
            conditions.add(str(symptom))
        
        # 从输入参数获取
        extra_conditions = input_data.get("health_conditions", [])
        if extra_conditions:
            for condition in extra_conditions:
                conditions.add(str(condition))
        
        # 移除空字符串
        conditions.discard("")
        
        return list(conditions)
    
    async def _check_exercises_contraindications(
        self,
        exercise_ids: List[str],
        health_conditions: List[str],
        strict_mode: bool
    ) -> List[Dict[str, Any]]:
        """检查动作的禁忌症"""
        results = []
        
        for exercise_id in exercise_ids:
            # 查询动作基本信息
            exercise_info = await self._get_exercise_info(exercise_id)
            
            if not exercise_info:
                # 未找到动作数据
                results.append({
                    "exercise_id": exercise_id,
                    "exercise_name_zh": "Unknown",
                    "exercise_name_en": "Unknown",
                    "category": "Unknown",
                    "difficulty": "Unknown",
                    "safety_level": "Unknown",
                    "has_contraindications": True,
                    "contraindications": [{
                        "exercise_id": exercise_id,
                        "exercise_name_zh": "Unknown",
                        "exercise_name_en": "Unknown",
                        "contraindication_type": "DATA_NOT_FOUND",
                        "risk_level": "HIGH",
                        "reason": "未找到动作数据",
                        "severity_score": 8,
                        "body_part_affected": "Unknown",
                        "medical_source": None
                    }],
                    "total_risk_score": 8,
                    "max_risk_level": "HIGH",
                    "recommendations": {
                        "can_perform": False,
                        "modifications": [],
                        "alternatives": [],
                        "precautions": ["请确认动作ID是否正确"],
                        "medical_consultation_needed": True
                    }
                })
                continue
            
            # 查询禁忌症关系
            contraindications = await self._get_exercise_contraindications(
                exercise_id, 
                health_conditions
            )
            
            # 填充动作名称
            for contra in contraindications:
                contra["exercise_name_zh"] = exercise_info.get("name_zh", "")
                contra["exercise_name_en"] = exercise_info.get("name_en", "")
            
            # 计算风险评分
            risk_assessment = self._assess_risk_level(contraindications, strict_mode)
            
            # 生成建议
            recommendations = self._generate_exercise_recommendations(
                exercise_info,
                contraindications,
                risk_assessment,
                health_conditions
            )
            
            results.append({
                "exercise_id": exercise_id,
                "exercise_name_zh": exercise_info.get("name_zh", ""),
                "exercise_name_en": exercise_info.get("name_en", ""),
                "category": exercise_info.get("category", ""),
                "difficulty": exercise_info.get("difficulty_zh") or exercise_info.get("difficulty_en") or "",
                "safety_level": exercise_info.get("safety_level", ""),
                "has_contraindications": len(contraindications) > 0,
                "contraindications": contraindications,
                "total_risk_score": risk_assessment["total_score"],
                "max_risk_level": risk_assessment["max_level"],
                "recommendations": recommendations
            })
        
        return results
    
    async def _get_exercise_info(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """获取动作基本信息"""
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        RETURN e.id as exercise_id,
               e.name_zh,
               e.name_en,
               e.category,
               e.difficulty_zh,
               e.safety_level,
               e.primary_muscle_zh
        """
        
        result = await self.neo4j_client.query(query, {"exercise_id": exercise_id})
        
        if result and len(result) > 0:
            return dict(result[0])
        return None
    
    async def _get_exercise_contraindications(
        self,
        exercise_id: str,
        health_conditions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        获取动作的禁忌症
        
        Requirements: 4.5 - 添加INVOLVES_JOINT关系查询和体态问题禁忌检查
        
        查询逻辑：
        1. 基于CONTRAINDICATED_FOR关系查询损伤禁忌
        2. 基于INVOLVES_JOINT关系查询关节禁忌
        3. 基于AGGRAVATES关系查询体态问题禁忌
        """
        contraindications = []
        
        # 1. 查询损伤禁忌（CONTRAINDICATED_FOR关系）
        injury_contraindications = await self._query_injury_contraindications(
            exercise_id,
            health_conditions
        )
        contraindications.extend(injury_contraindications)
        
        # 2. 查询关节禁忌（INVOLVES_JOINT关系）- Requirements 4.5
        joint_contraindications = await self._query_joint_contraindications(
            exercise_id,
            health_conditions
        )
        contraindications.extend(joint_contraindications)
        
        # 3. 查询体态问题禁忌（AGGRAVATES关系）- Requirements 4.5
        postural_contraindications = await self._query_postural_contraindications(
            exercise_id,
            health_conditions
        )
        contraindications.extend(postural_contraindications)
        
        return contraindications
    
    async def _query_injury_contraindications(
        self,
        exercise_id: str,
        health_conditions: List[str]
    ) -> List[Dict[str, Any]]:
        """查询损伤禁忌（CONTRAINDICATED_FOR关系）"""
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        OPTIONAL MATCH (e)-[r:CONTRAINDICATED_FOR]->(injury:InjuryType)
        WHERE injury.name_zh IN $health_conditions
           OR injury.name_en IN $health_conditions
           OR injury.category_zh IN $health_conditions
        
        RETURN
          injury.name_zh as injury_name_zh,
          injury.name_en as injury_name_en,
          injury.category_zh as category_zh,
          r.risk_level as risk_level,
          r.severity as severity,
          r.reason as reason,
          r.severity_score as severity_score,
          injury.affected_body_parts as body_parts,
          injury.medical_source as medical_source
        ORDER BY r.severity_score DESC
        """
        
        result = await self.neo4j_client.query(query, {
            "exercise_id": exercise_id,
            "health_conditions": health_conditions
        })
        
        contraindications = []
        for row in result:
            # 跳过空结果
            if row.get("injury_name_zh") is None:
                continue
            
            body_parts = row.get("body_parts", [])
            if isinstance(body_parts, list):
                body_part_str = ", ".join(body_parts)
            else:
                body_part_str = str(body_parts) if body_parts else "Unknown"
            
            # 获取severity字段（absolute/relative/caution）
            severity = row.get("severity", "relative")
            
            contraindications.append({
                "exercise_id": exercise_id,
                "exercise_name_zh": "",  # 将在上层填充
                "exercise_name_en": "",  # 将在上层填充
                "contraindication_type": row.get("category_zh") or "损伤禁忌",
                "risk_level": self._map_risk_level(row.get("risk_level")),
                "severity": severity,
                "reason": row.get("reason") or "基于医学指导",
                "severity_score": int(row.get("severity_score") or 5),
                "body_part_affected": body_part_str,
                "medical_source": row.get("medical_source")
            })
        
        return contraindications
    
    async def _query_joint_contraindications(
        self,
        exercise_id: str,
        health_conditions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        查询关节禁忌（INVOLVES_JOINT关系）
        
        Requirements: 4.5 - 添加INVOLVES_JOINT关系查询排除危险动作
        
        逻辑：
        1. 从health_conditions中提取关节相关的条件
        2. 查询动作涉及的关节（INVOLVES_JOINT关系）
        3. 如果动作涉及受伤关节，标记为禁忌
        """
        # 提取关节相关的健康状况
        joint_keywords = ["关节", "膝", "肩", "肘", "腕", "踝", "髋", "脊柱", "颈椎", "腰椎"]
        injured_joints = [
            cond for cond in health_conditions
            if any(keyword in cond for keyword in joint_keywords)
        ]
        
        if not injured_joints:
            return []
        
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        OPTIONAL MATCH (e)-[r:INVOLVES_JOINT]->(joint:Joint)
        WHERE joint.name_zh IN $injured_joints
           OR joint.name_en IN $injured_joints
        
        RETURN
          joint.name_zh as joint_name_zh,
          joint.name_en as joint_name_en,
          r.stress_level as stress_level,
          r.movement_type as movement_type
        """
        
        result = await self.neo4j_client.query(query, {
            "exercise_id": exercise_id,
            "injured_joints": injured_joints
        })
        
        contraindications = []
        for row in result:
            # 跳过空结果
            if row.get("joint_name_zh") is None:
                continue
            
            stress_level = row.get("stress_level", "medium")
            
            # 根据压力等级确定风险等级
            if stress_level == "high":
                risk_level = "HIGH"
                severity_score = 7
                severity = "relative"
            elif stress_level == "medium":
                risk_level = "MODERATE"
                severity_score = 5
                severity = "caution"
            else:
                risk_level = "LOW"
                severity_score = 3
                severity = "caution"
            
            contraindications.append({
                "exercise_id": exercise_id,
                "exercise_name_zh": "",  # 将在上层填充
                "exercise_name_en": "",  # 将在上层填充
                "contraindication_type": "关节禁忌",
                "risk_level": risk_level,
                "severity": severity,
                "reason": f"动作涉及受伤关节：{row.get('joint_name_zh')}（压力等级：{stress_level}）",
                "severity_score": severity_score,
                "body_part_affected": row.get("joint_name_zh", "Unknown"),
                "medical_source": None
            })
        
        return contraindications
    
    async def _query_postural_contraindications(
        self,
        exercise_id: str,
        health_conditions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        查询体态问题禁忌（AGGRAVATES关系）
        
        Requirements: 4.5 - 添加体态问题禁忌检查
        
        逻辑：
        1. 从health_conditions中提取体态问题
        2. 查询动作是否会加重体态问题（AGGRAVATES关系）
        3. 如果会加重，标记为禁忌
        """
        # 提取体态问题相关的健康状况
        postural_keywords = [
            "骨盆前倾", "骨盆后倾", "圆肩", "头前伸", "驼背", 
            "脊柱侧弯", "膝内翻", "膝外翻", "扁平足", "高弓足",
            "胸椎后凸", "腰椎前凸", "平背"
        ]
        postural_issues = [
            cond for cond in health_conditions
            if any(keyword in cond for keyword in postural_keywords)
        ]
        
        if not postural_issues:
            return []
        
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        OPTIONAL MATCH (e)-[r:AGGRAVATES]->(posture:PosturalIssue)
        WHERE posture.name_zh IN $postural_issues
           OR posture.name_en IN $postural_issues
        
        RETURN
          posture.name_zh as posture_name_zh,
          posture.name_en as posture_name_en,
          posture.description_zh as description,
          r.reason as reason
        """
        
        result = await self.neo4j_client.query(query, {
            "exercise_id": exercise_id,
            "postural_issues": postural_issues
        })
        
        contraindications = []
        for row in result:
            # 跳过空结果
            if row.get("posture_name_zh") is None:
                continue
            
            contraindications.append({
                "exercise_id": exercise_id,
                "exercise_name_zh": "",  # 将在上层填充
                "exercise_name_en": "",  # 将在上层填充
                "contraindication_type": "体态问题禁忌",
                "risk_level": "MODERATE",
                "severity": "caution",
                "reason": row.get("reason") or f"可能加重体态问题：{row.get('posture_name_zh')}",
                "severity_score": 5,
                "body_part_affected": row.get("posture_name_zh", "Unknown"),
                "medical_source": None
            })
        
        return contraindications
    
    def _assess_risk_level(
        self,
        contraindications: List[Dict[str, Any]],
        strict_mode: bool
    ) -> Dict[str, Any]:
        """评估风险等级"""
        if not contraindications:
            return {
                "total_score": 0,
                "max_level": "LOW",
                "level": "LOW"
            }
        
        severity_scores = [c["severity_score"] for c in contraindications]
        max_score = max(severity_scores)
        total_score = sum(severity_scores)
        
        # 确定最大风险等级
        if max_score >= 8:
            max_level = "CRITICAL"
        elif max_score >= 6:
            max_level = "HIGH"
        elif max_score >= 4:
            max_level = "MODERATE"
        else:
            max_level = "LOW"
        
        # 严格模式下调整风险等级
        if strict_mode and max_level != "LOW":
            levels = ["LOW", "MODERATE", "HIGH", "CRITICAL"]
            current_index = levels.index(max_level)
            if current_index < len(levels) - 1:
                max_level = levels[current_index + 1]
        
        return {
            "total_score": total_score,
            "max_level": max_level,
            "level": max_level
        }
    
    def _generate_exercise_recommendations(
        self,
        exercise_info: Dict[str, Any],
        contraindications: List[Dict[str, Any]],
        risk_assessment: Dict[str, Any],
        health_conditions: List[str]
    ) -> Dict[str, Any]:
        """生成动作建议（基于severity字段）"""
        max_level = risk_assessment["max_level"]
        
        # 检查是否有绝对禁忌
        has_absolute = any(c.get("severity") == "absolute" for c in contraindications)
        has_relative = any(c.get("severity") == "relative" for c in contraindications)
        has_caution = any(c.get("severity") == "caution" for c in contraindications)
        
        # 绝对禁忌：完全不能执行
        can_perform = not has_absolute and max_level != "CRITICAL"
        
        recommendations = {
            "can_perform": can_perform,
            "modifications": [],
            "alternatives": [],
            "precautions": [],
            "medical_consultation_needed": has_absolute or max_level in ["HIGH", "CRITICAL"]
        }
        
        # 绝对禁忌的建议
        if has_absolute:
            absolute_injuries = [c.get("contraindication_type", "损伤") for c in contraindications if c.get("severity") == "absolute"]
            recommendations["precautions"].append(f"⛔ 绝对禁忌：由于{', '.join(absolute_injuries)}，必须完全避免此动作")
            recommendations["alternatives"].append("寻找完全不涉及受伤部位的替代动作")
            recommendations["alternatives"].append("咨询医疗专业人员获取个性化建议")
            return recommendations
        
        # 相对禁忌的建议
        if has_relative:
            relative_injuries = [c.get("contraindication_type", "损伤") for c in contraindications if c.get("severity") == "relative"]
            recommendations["precautions"].append(f"⚠️ 相对禁忌：由于{', '.join(relative_injuries)}，需要在专业指导下谨慎进行")
            recommendations["modifications"].extend([
                "大幅降低训练重量（50%以下）",
                "减少动作幅度至无痛范围",
                "延长休息时间，密切监控身体反应"
            ])
            recommendations["precautions"].append("如有任何疼痛或不适，立即停止")
        
        # 谨慎使用的建议
        if has_caution:
            caution_reasons = [c.get("reason", "需要特别注意") for c in contraindications if c.get("severity") == "caution"]
            recommendations["precautions"].append(f"💡 谨慎使用：{caution_reasons[0] if caution_reasons else '需要特别注意'}")
            recommendations["modifications"].extend([
                "适当降低训练强度",
                "充分热身和拉伸",
                "注意动作质量和控制"
            ])
        
        # 基于风险等级添加通用建议
        if max_level == "CRITICAL":
            recommendations["precautions"].extend([
                "⛔ 避免执行此动作，风险等级极高",
                "必须咨询医疗专业人员后再决定是否进行"
            ])
            recommendations["modifications"].append("寻找低风险替代动作")
        elif max_level == "HIGH":
            recommendations["precautions"].extend([
                "需要在专业人士指导下进行",
                "充分热身，严格控制训练强度"
            ])
            recommendations["modifications"].append("降低训练重量和频率")
        
        if max_level == "MODERATE":
            recommendations["precautions"].append("注意训练过程中的身体反应")
            recommendations["modifications"].append("适当调整动作幅度")
        
        # 基于禁忌症类型添加特定建议
        for contra in contraindications:
            contra_type = contra.get("contraindication_type", "")
            reason = contra.get("reason", "")
            
            if "肩" in contra_type or "肩" in reason:
                recommendations["precautions"].append("避免肩关节外展超过90度")
            if "膝" in contra_type or "膝" in reason:
                recommendations["precautions"].append("避免膝关节屈曲超过90度")
            if "腰" in contra_type or "腰" in reason or "脊柱" in reason:
                recommendations["precautions"].append("保持脊柱中立位，避免前屈和旋转")
            if "心脏" in contra_type:
                recommendations["precautions"].append("监控心率，避免憋气")
            if "关节" in contra_type:
                recommendations["precautions"].append("充分活动关节，避免过度扭转")
        
        return recommendations
    
    def _generate_overall_assessment(
        self,
        exercise_results: List[Dict[str, Any]],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成总体评估"""
        total_risk_score = sum(r["total_risk_score"] for r in exercise_results)
        
        critical_issues = [
            f"{r['exercise_name_zh']}存在严重禁忌症"
            for r in exercise_results
            if r["max_risk_level"] == "CRITICAL"
        ]
        
        # 确定总体风险等级
        if total_risk_score >= 20 or critical_issues:
            risk_level = "HIGH"
        elif total_risk_score >= 10:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"
        
        # 生成建议
        recommendations = []
        if risk_level == "HIGH":
            recommendations.extend([
                "建议在进行训练前咨询医疗专业人士",
                "优先选择低风险动作"
            ])
        elif risk_level == "MODERATE":
            recommendations.extend([
                "注意训练安全，密切监控身体反应",
                "适当调整训练强度和频率"
            ])
        else:
            recommendations.append("可以进行正常训练，注意动作质量")
        
        return {
            "risk_level": risk_level,
            "total_risk_score": total_risk_score,
            "critical_issues": critical_issues,
            "recommendations": recommendations
        }
    
    def _generate_medical_guidance(
        self,
        overall_assessment: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """生成医学建议"""
        guidance = []
        
        risk_level = overall_assessment["risk_level"]
        
        if risk_level == "HIGH":
            guidance.extend([
                "强烈建议在医疗专业人士指导下进行训练",
                "定期进行健康检查，监测训练反应"
            ])
        elif risk_level == "MODERATE":
            guidance.extend([
                "建议适度训练，密切关注身体信号",
                "如有不适及时调整或暂停训练"
            ])
        else:
            guidance.append("可以进行常规训练，保持健康生活方式")
        
        # 如果有慢性病
        health_profile = user_profile.get("health_profile", {})
        chronic_conditions = health_profile.get("chronic_conditions", [])
        if chronic_conditions:
            guidance.append("请严格遵循医生给出的运动建议")
        
        return "；".join(guidance)
    
    def _map_risk_level(self, level: Optional[str]) -> str:
        """映射风险等级"""
        if not level:
            return "LOW"
        
        upper_level = str(level).upper()
        if "CRITICAL" in upper_level:
            return "CRITICAL"
        if "HIGH" in upper_level:
            return "HIGH"
        if "MODERATE" in upper_level:
            return "MODERATE"
        return "LOW"
