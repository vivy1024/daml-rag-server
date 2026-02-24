"""
肌群训练量计算器 MCP工具

基于Neo4j训练数据和科学训练理论（MEV/MAV/MRV）
参考TypeScript的muscle-group-volume-calculator实现

功能特性：
- 基于Renaissance Periodization理论的MEV/MAV/MRV数据
- 个性化训练量推荐（基于训练水平和恢复能力）
- 恢复时间计算（考虑肌群大小、训练强度、用户恢复能力）
- 过度训练风险检测
- 每周组数、每组次数、休息时间建议

作者: BUILD_BODY Team
版本: v1.0.0
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import logging

from ...mcp_tools.base_tool import BaseMCPTool
from ...utils.muscle_group_matcher import MuscleGroupMatcher, get_muscle_group_matcher

logger = logging.getLogger(__name__)


# =============================================================================
# 输入Schema定义
# =============================================================================

class MuscleGroupVolumeCalculatorInput(BaseModel):
    """肌群训练量计算器输入"""
    user_id: str = Field(..., description="用户ID，用于获取训练水平和恢复能力")
    muscle_group: str = Field(..., description="目标肌群（中文名称，如：胸大肌、背阔肌）")
    training_goal: Literal[
        # 基础训练目标
        "strength", "hypertrophy", "endurance", "general_fitness",
        # 中国本地化扩展目标 - Requirements 3.1, 3.2, 3.3
        "fat_loss",              # 减脂塑形 - Requirements 3.1
        "posture_correction",    # 体态矫正 - Requirements 3.2
        "functional"             # 功能性训练 - Requirements 3.3
    ] = Field(
        ..., description="训练目标（支持基础目标和中国本地化扩展目标）"
    )
    training_frequency_per_week: int = Field(
        ..., ge=1, le=7, description="每星期训练频率"
    )
    current_weekly_sets: Optional[int] = Field(
        None, ge=0, description="当前每周组数（用于分析是否过度训练）"
    )
    recovery_capacity: Optional[Literal["low", "moderate", "high"]] = Field(
        None, description="恢复能力（可选，从用户档案获取）"
    )


# =============================================================================
# 输出类型定义
# =============================================================================

class VolumeRecommendation(BaseModel):
    """训练量推荐"""
    recommended_weekly_sets: int
    sets_per_session: int
    reps_per_set_range: tuple[int, int]
    rest_period_seconds: int
    reasoning: str


class RecoveryGuidance(BaseModel):
    """恢复指导"""
    recovery_time_hours: int
    training_frequency_recommendation: str
    recovery_strategies: List[str]
    warning_signs: List[str]


class OvertrainingRisk(BaseModel):
    """过度训练风险"""
    risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    risk_score: float
    current_vs_mrv: str
    warnings: List[str]
    recommendations: List[str]


class MuscleGroupVolumeCalculatorOutput(BaseModel):
    """肌群训练量计算器输出"""
    success: bool
    tool_name: str
    user_id: str
    muscle_group: str
    
    # 训练量数据
    mev: int  # 最小有效训练量
    mav: int  # 最大适应训练量
    mrv: int  # 最大可恢复训练量
    
    # 推荐训练量
    volume_recommendation: VolumeRecommendation
    
    # 恢复指导
    recovery_guidance: RecoveryGuidance
    
    # 过度训练风险（如果提供了current_weekly_sets）
    overtraining_risk: Optional[OvertrainingRisk] = None
    
    # 额外建议
    additional_recommendations: List[str]
    
    execution_time_ms: float
    confidence_score: float


# =============================================================================
# 肌群训练量计算器类
# =============================================================================

class MuscleGroupVolumeCalculator(BaseMCPTool):
    """肌群训练量计算器"""
    
    def get_name(self) -> str:
        return "muscle_group_volume_calculator"
    
    def get_description(self) -> str:
        return "肌群训练量计算器 - 基于MEV/MAV/MRV科学数据的个性化训练量推荐"
    
    def get_category(self) -> str:
        return "training"
    
    def get_input_schema(self) -> type[BaseModel]:
        return MuscleGroupVolumeCalculatorInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return MuscleGroupVolumeCalculatorOutput
    
    def get_complexity(self) -> str:
        return "medium"
    
    def get_estimated_duration(self) -> float:
        return 1000.0
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["neo4j", "user_profile_mcp"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行肌群训练量计算
        
        流程：
        1. 获取用户档案（训练水平、恢复能力）
        2. 使用MuscleGroupMatcher匹配肌群名称
        3. 查询Neo4j获取肌群训练数据（MEV/MAV/MRV、training_frequency、recovery_time）
        4. 查询失败时使用默认训练量建议
        5. 基于用户训练水平推荐训练量
        6. 计算恢复时间和频率建议
        7. 检测过度训练风险（如果提供了current_weekly_sets）
        8. 生成个性化建议
        
        Requirements: 5.1, 5.2, 5.3
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: 获取用户档案（优先从DAG注入的input_data获取）
            user_profile = input_data.get("user_profile") or await self._get_user_profile(input_data.get("user_id"))
            
            # Step 2: 使用MuscleGroupMatcher匹配肌群名称
            matcher = get_muscle_group_matcher()
            original_muscle_group = input_data["muscle_group"]
            matched_muscle_group = matcher.match(original_muscle_group)
            
            if matched_muscle_group:
                self.logger.info(
                    f"📊 肌群名称匹配: '{original_muscle_group}' -> '{matched_muscle_group}'"
                )
            else:
                self.logger.warning(
                    f"⚠️ 无法匹配肌群名称: '{original_muscle_group}'，将使用默认训练量"
                )
            
            # Step 3: 查询Neo4j获取肌群训练数据
            muscle_data = None
            query_muscle_name = matched_muscle_group or original_muscle_group
            
            try:
                muscle_data = await self._get_muscle_training_data(query_muscle_name)
            except Exception as e:
                self.logger.warning(f"⚠️ Neo4j查询失败: {e}，将使用默认训练量")
            
            # Step 4: 查询失败时使用默认训练量建议
            if not muscle_data:
                self.logger.info(
                    f"📊 使用默认训练量建议: '{original_muscle_group}'"
                )
                default_volume = matcher.get_default_volume(original_muscle_group)
                muscle_data = {
                    "name_zh": matched_muscle_group or original_muscle_group,
                    "name_en": None,
                    "training_frequency": "2-3次/周",
                    "recovery_time": "48小时",
                    "mev": default_volume["mev"],
                    "mav": default_volume["mav"],
                    "mrv": default_volume["mrv"],
                    "movement_patterns": [],
                    "function": [],
                    "is_default": True  # 标记为默认值
                }
            
            # Step 5: 基于用户训练水平推荐训练量
            volume_recommendation = self._calculate_volume_recommendation(
                muscle_data,
                input_data,
                user_profile
            )
            
            # Step 6: 计算恢复时间和频率建议
            recovery_guidance = self._calculate_recovery_guidance(
                muscle_data,
                input_data,
                user_profile
            )
            
            # Step 7: 检测过度训练风险
            overtraining_risk = None
            if input_data.get("current_weekly_sets") is not None:
                overtraining_risk = self._assess_overtraining_risk(
                    muscle_data,
                    input_data["current_weekly_sets"],
                    volume_recommendation
                )
            
            # Step 8: 生成个性化建议
            additional_recommendations = self._generate_additional_recommendations(
                muscle_data,
                input_data,
                user_profile,
                volume_recommendation,
                overtraining_risk
            )
            
            # 如果使用了默认值，添加提示
            if muscle_data.get("is_default"):
                additional_recommendations.insert(
                    0,
                    f"⚠️ 未找到'{original_muscle_group}'的精确数据，以上建议基于通用训练量标准"
                )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": "muscle_group_volume_calculator",
                "user_id": input_data["user_id"],
                "muscle_group": muscle_data["name_zh"],
                "original_input": original_muscle_group,
                "matched_name": matched_muscle_group,
                "mev": muscle_data["mev"],
                "mav": muscle_data["mav"],
                "mrv": muscle_data["mrv"],
                "volume_recommendation": volume_recommendation.model_dump(),
                "recovery_guidance": recovery_guidance.model_dump(),
                "overtraining_risk": overtraining_risk.model_dump() if overtraining_risk else None,
                "additional_recommendations": additional_recommendations,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 95.0 if not muscle_data.get("is_default") else 75.0,
                "used_default_values": muscle_data.get("is_default", False)
            }
            
            self.logger.info(
                f"✅ 肌群训练量计算完成: {muscle_data['name_zh']}, "
                f"推荐{volume_recommendation.recommended_weekly_sets}组/周"
                f"{' (使用默认值)' if muscle_data.get('is_default') else ''}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 肌群训练量计算失败: {e}", exc_info=True)
            raise
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户档案"""
        # TODO: 如果有UserProfileClient，调用它
        # 目前返回默认值
        return {
            "basic_info": {
                "age": None  # 从用户档案MCP获取
            },
            "fitness_profile": {
                "training_level": "intermediate",  # beginner, intermediate, advanced
                "recovery_capacity": "moderate"     # low, moderate, high
            }
        }
    
    async def _get_muscle_training_data(
        self,
        muscle_group: str
    ) -> Optional[Dict[str, Any]]:
        """查询Neo4j获取肌群训练数据"""
        query = """
        MATCH (m:Muscle)
        WHERE m.name_zh = $muscle_group
        RETURN m.name_zh as name_zh,
               m.name_en as name_en,
               m.training_frequency as training_frequency,
               m.recovery_time as recovery_time,
               m.mev as mev,
               m.mav as mav,
               m.mrv as mrv,
               m.movement_patterns as movement_patterns,
               m.function as function
        """
        
        result = await self.neo4j_client.execute_query(query, {"muscle_group": muscle_group})
        
        if not result:
            return None
        
        record = result[0]
        
        return {
            "name_zh": record.get("name_zh"),
            "name_en": record.get("name_en"),
            "training_frequency": record.get("training_frequency"),
            "recovery_time": record.get("recovery_time"),
            "mev": record.get("mev", 10),  # 默认值
            "mav": record.get("mav", 16),  # 默认值
            "mrv": record.get("mrv", 22),  # 默认值
            "movement_patterns": record.get("movement_patterns", []),
            "function": record.get("function", [])
        }
    
    def _calculate_volume_recommendation(
        self,
        muscle_data: Dict[str, Any],
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> VolumeRecommendation:
        """计算训练量推荐"""
        training_level = user_profile.get("fitness_profile", {}).get("training_level", "intermediate")
        training_goal = input_data["training_goal"]
        training_frequency = input_data["training_frequency_per_week"]
        recovery_capacity = input_data.get("recovery_capacity") or \
                          user_profile.get("fitness_profile", {}).get("recovery_capacity", "moderate")
        
        mev = muscle_data["mev"]
        mav = muscle_data["mav"]
        mrv = muscle_data["mrv"]
        
        # 基于训练水平推荐训练量
        if training_level == "beginner":
            # 新手：接近MEV的保守训练量
            recommended_weekly_sets = int(mev + (mav - mev) * 0.2)
            reasoning = f"新手训练者，推荐接近MEV（{mev}组）的保守训练量"
        elif training_level == "advanced":
            # 高级：接近MAV的适中训练量
            recommended_weekly_sets = int(mav)
            reasoning = f"高级训练者，推荐MAV（{mav}组）的适中训练量"
        else:
            # 中级：MEV和MAV之间
            recommended_weekly_sets = int((mev + mav) / 2)
            reasoning = f"中级训练者，推荐MEV和MAV之间的训练量"
        
        # 基于恢复能力调整
        recovery_factor = {
            "low": 0.8,
            "moderate": 1.0,
            "high": 1.2
        }.get(recovery_capacity, 1.0)
        
        recommended_weekly_sets = int(recommended_weekly_sets * recovery_factor)
        
        # 确保不超过MRV
        if recommended_weekly_sets > mrv:
            recommended_weekly_sets = mrv
            reasoning += f"；已调整至MRV上限（{mrv}组）"
        
        # 动态分配单次训练量（任务18）
        # 计算公式：单次训练量 = 周总训练量 / 训练频率
        sets_per_session = self._calculate_dynamic_sets_per_session(
            recommended_weekly_sets,
            training_frequency,
            reasoning
        )
        
        # 基于训练目标推荐次数范围和休息时间
        if training_goal == "strength":
            reps_range = (3, 6)
            rest_seconds = 180  # 3分钟
        elif training_goal == "hypertrophy":
            reps_range = (8, 12)
            rest_seconds = 90   # 1.5分钟
        elif training_goal == "endurance":
            reps_range = (15, 20)
            rest_seconds = 60   # 1分钟
        # 中国本地化扩展目标 - Requirements 3.1, 3.2, 3.3
        elif training_goal == "fat_loss":
            # 减脂塑形：高次数、短休息 - Requirements 3.1
            reps_range = (12, 20)
            rest_seconds = 45   # 45秒，保持心率
        elif training_goal == "posture_correction":
            # 体态矫正：中等次数、适中休息 - Requirements 3.2
            reps_range = (10, 15)
            rest_seconds = 60   # 1分钟
        elif training_goal == "functional":
            # 功能性训练：中等次数、适中休息 - Requirements 3.3
            reps_range = (8, 15)
            rest_seconds = 60   # 1分钟
        else:  # general_fitness
            reps_range = (8, 15)
            rest_seconds = 90
        
        return VolumeRecommendation(
            recommended_weekly_sets=recommended_weekly_sets,
            sets_per_session=sets_per_session,
            reps_per_set_range=reps_range,
            rest_period_seconds=rest_seconds,
            reasoning=reasoning
        )
    
    def _calculate_dynamic_sets_per_session(
        self,
        weekly_sets: int,
        training_frequency: int,
        reasoning: str
    ) -> int:
        """
        动态分配单次训练量（任务18）
        
        实现训练频率与单次训练量的反比关系：
        - 计算公式：单次训练量 = 周总训练量 / 训练频率
        - 确保单次训练量在合理范围（4-12组）
        
        科学依据：
        - 训练频率越高，单次训练量应越低，以确保充分恢复
        - 训练频率越低，单次训练量应越高，以达到足够的训练刺激
        - 单次训练量过低（<4组）：训练刺激不足
        - 单次训练量过高（>12组）：恢复困难，质量下降
        
        Args:
            weekly_sets: 周总训练量
            training_frequency: 每星期训练频率
            reasoning: 推荐理由（会被更新）
        
        Returns:
            单次训练组数（4-12组范围内）
        """
        # 基础计算：周总训练量 / 训练频率
        base_sets_per_session = weekly_sets / training_frequency
        
        # 确保在合理范围内（4-12组）
        MIN_SETS_PER_SESSION = 4
        MAX_SETS_PER_SESSION = 12
        
        if base_sets_per_session < MIN_SETS_PER_SESSION:
            # 单次训练量过低，调整至最小值
            adjusted_sets = MIN_SETS_PER_SESSION
            
            # 重新计算周总训练量
            adjusted_weekly_sets = adjusted_sets * training_frequency
            
            self.logger.info(
                f"📊 单次训练量调整: "
                f"原始={base_sets_per_session:.1f}组/次 < 最小值{MIN_SETS_PER_SESSION}组/次, "
                f"调整至{adjusted_sets}组/次, "
                f"周总训练量 {weekly_sets}→{adjusted_weekly_sets}组/周"
            )
            
            reasoning += (
                f"；单次训练量调整至最小值{MIN_SETS_PER_SESSION}组/次，"
                f"周总训练量相应调整至{adjusted_weekly_sets}组/周"
            )
            
            return adjusted_sets
        
        elif base_sets_per_session > MAX_SETS_PER_SESSION:
            # 单次训练量过高，调整至最大值
            adjusted_sets = MAX_SETS_PER_SESSION
            
            # 重新计算周总训练量
            adjusted_weekly_sets = adjusted_sets * training_frequency
            
            self.logger.info(
                f"📊 单次训练量调整: "
                f"原始={base_sets_per_session:.1f}组/次 > 最大值{MAX_SETS_PER_SESSION}组/次, "
                f"调整至{adjusted_sets}组/次, "
                f"周总训练量 {weekly_sets}→{adjusted_weekly_sets}组/周"
            )
            
            reasoning += (
                f"；单次训练量调整至最大值{MAX_SETS_PER_SESSION}组/次，"
                f"周总训练量相应调整至{adjusted_weekly_sets}组/周"
            )
            
            return adjusted_sets
        
        else:
            # 在合理范围内，四舍五入
            adjusted_sets = round(base_sets_per_session)
            
            self.logger.info(
                f"📊 单次训练量分配: "
                f"周总训练量={weekly_sets}组/周, "
                f"训练频率={training_frequency}次/周, "
                f"单次训练量={adjusted_sets}组/次 "
                f"(反比关系: 频率↑ → 单次量↓)"
            )
            
            reasoning += (
                f"；单次训练量={adjusted_sets}组/次 "
                f"(基于训练频率{training_frequency}次/周动态分配)"
            )
            
            return adjusted_sets
    
    def _calculate_recovery_guidance(
        self,
        muscle_data: Dict[str, Any],
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> RecoveryGuidance:
        """计算恢复指导"""
        # 解析recovery_time（如："48小时"）
        recovery_time_str = muscle_data.get("recovery_time", "48小时")
        recovery_hours = self._parse_recovery_time(recovery_time_str)
        
        # 基于训练强度调整恢复时间
        training_goal = input_data["training_goal"]
        if training_goal == "strength":
            recovery_hours = int(recovery_hours * 1.2)  # 力量训练需要更多恢复
        elif training_goal == "endurance":
            recovery_hours = int(recovery_hours * 0.8)  # 耐力训练恢复较快
        
        # 基于年龄调整恢复时间（任务17）
        age = user_profile.get("basic_info", {}).get("age")
        if age is not None:
            age_factor = self._calculate_age_recovery_factor(age)
            recovery_hours = int(recovery_hours * age_factor)
        
        # 基于恢复能力调整
        recovery_capacity = input_data.get("recovery_capacity") or \
                          user_profile.get("fitness_profile", {}).get("recovery_capacity", "moderate")
        
        recovery_factor = {
            "low": 1.3,
            "moderate": 1.0,
            "high": 0.7
        }.get(recovery_capacity, 1.0)
        
        recovery_hours = int(recovery_hours * recovery_factor)
        
        # 生成训练频率建议
        training_frequency = input_data["training_frequency_per_week"]
        hours_per_week = 168
        min_recovery_hours = recovery_hours
        max_sessions_per_week = hours_per_week // min_recovery_hours
        
        if training_frequency > max_sessions_per_week:
            frequency_recommendation = (
                f"建议每星期训练{max_sessions_per_week}次，"
                f"当前频率（{training_frequency}次/周）可能不足以恢复"
            )
        else:
            frequency_recommendation = f"当前训练频率（{training_frequency}次/周）合理"
        
        # 生成恢复策略
        recovery_strategies = [
            "保证充足睡眠（7-9小时/天）",
            "摄入足够蛋白质（1.6-2.2g/kg体重）",
            "训练后进行轻度拉伸"
        ]
        
        if recovery_capacity == "low":
            recovery_strategies.extend([
                "考虑增加休息日",
                "使用主动恢复（如轻度有氧）"
            ])
        
        # 生成警告信号
        warning_signs = [
            "持续肌肉酸痛超过72小时",
            "训练表现持续下降",
            "疲劳感增加，睡眠质量下降",
            "食欲减退或情绪低落"
        ]
        
        return RecoveryGuidance(
            recovery_time_hours=recovery_hours,
            training_frequency_recommendation=frequency_recommendation,
            recovery_strategies=recovery_strategies,
            warning_signs=warning_signs
        )
    
    def _parse_recovery_time(self, recovery_time_str: str) -> int:
        """解析恢复时间字符串（如："48小时"）"""
        import re
        match = re.search(r'(\d+)', recovery_time_str)
        if match:
            return int(match.group(1))
        return 48  # 默认48小时
    
    def _calculate_age_recovery_factor(self, age: int) -> float:
        """
        根据年龄计算恢复时间系数（任务17）
        
        年龄分组：
        - <30岁：标准恢复时间（1.0）
        - 30-40岁：恢复时间×1.2
        - 40-50岁：恢复时间×1.5
        - >50岁：恢复时间×2.0
        
        科学依据：
        - 随着年龄增长，肌肉蛋白质合成速率下降
        - 激素水平（睾酮、生长激素）降低
        - 中枢神经系统恢复能力下降
        - 关节和结缔组织修复速度减慢
        """
        if age < 30:
            return 1.0
        elif age < 40:
            return 1.2
        elif age < 50:
            return 1.5
        else:
            return 2.0
    
    def _assess_overtraining_risk(
        self,
        muscle_data: Dict[str, Any],
        current_weekly_sets: int,
        volume_recommendation: VolumeRecommendation
    ) -> OvertrainingRisk:
        """评估过度训练风险"""
        mrv = muscle_data["mrv"]
        mav = muscle_data["mav"]
        
        # 计算风险评分
        if current_weekly_sets <= mav:
            risk_score = 0.0
            risk_level = "LOW"
        elif current_weekly_sets <= mrv:
            risk_score = ((current_weekly_sets - mav) / (mrv - mav)) * 5.0
            risk_level = "MODERATE"
        elif current_weekly_sets <= mrv * 1.2:
            risk_score = 5.0 + ((current_weekly_sets - mrv) / (mrv * 0.2)) * 3.0
            risk_level = "HIGH"
        else:
            risk_score = 10.0
            risk_level = "CRITICAL"
        
        # 生成对比说明
        current_vs_mrv = (
            f"当前训练量（{current_weekly_sets}组/周）"
            f"vs MRV（{mrv}组/周）："
        )
        
        if current_weekly_sets > mrv:
            percentage = ((current_weekly_sets - mrv) / mrv) * 100
            current_vs_mrv += f"超出{percentage:.1f}%"
        else:
            percentage = ((mrv - current_weekly_sets) / mrv) * 100
            current_vs_mrv += f"低于{percentage:.1f}%"
        
        # 生成警告
        warnings = []
        if risk_level == "CRITICAL":
            warnings.extend([
                "⚠️ 严重过度训练风险！",
                "当前训练量远超MRV，可能导致损伤和训练倒退",
                "建议立即减少训练量"
            ])
        elif risk_level == "HIGH":
            warnings.extend([
                "⚠️ 高过度训练风险",
                "当前训练量超过MRV，恢复能力可能不足",
                "建议减少训练量或增加休息日"
            ])
        elif risk_level == "MODERATE":
            warnings.append("当前训练量接近MRV上限，需密切监控恢复状态")
        
        # 生成建议
        recommendations = []
        if current_weekly_sets > mrv:
            recommended_reduction = current_weekly_sets - volume_recommendation.recommended_weekly_sets
            recommendations.append(
                f"建议减少{recommended_reduction}组/周，"
                f"调整至{volume_recommendation.recommended_weekly_sets}组/周"
            )
        elif current_weekly_sets > mav:
            recommendations.append("当前训练量较高，确保充足恢复")
        else:
            recommendations.append("当前训练量合理，可以继续保持")
        
        return OvertrainingRisk(
            risk_level=risk_level,
            risk_score=round(risk_score, 1),
            current_vs_mrv=current_vs_mrv,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _generate_additional_recommendations(
        self,
        muscle_data: Dict[str, Any],
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any],
        volume_recommendation: VolumeRecommendation,
        overtraining_risk: Optional[OvertrainingRisk]
    ) -> List[str]:
        """生成额外建议"""
        recommendations = []
        
        # 基于训练目标的建议
        training_goal = input_data["training_goal"]
        if training_goal == "strength":
            recommendations.append("力量训练：注重动作质量和渐进超负荷")
        elif training_goal == "hypertrophy":
            recommendations.append("肌肥大训练：保持肌肉张力和代谢压力")
        elif training_goal == "endurance":
            recommendations.append("耐力训练：控制休息时间，保持训练密度")
        # 中国本地化扩展目标 - Requirements 3.1, 3.2, 3.3
        elif training_goal == "fat_loss":
            # 减脂塑形建议 - Requirements 3.1
            recommendations.append("减脂塑形：保持高训练密度，控制休息时间在45秒内")
            recommendations.append("建议配合有氧训练和饮食控制，创造热量缺口")
        elif training_goal == "posture_correction":
            # 体态矫正建议 - Requirements 3.2
            recommendations.append("体态矫正：注重动作控制和肌肉激活，避免代偿")
            recommendations.append("建议加强核心稳定性训练和拉伸放松")
        elif training_goal == "functional":
            # 功能性训练建议 - Requirements 3.3
            recommendations.append("功能性训练：注重多关节复合动作和动态稳定性")
            recommendations.append("建议包含平衡、协调和爆发力训练元素")
        
        # 基于动作模式的建议
        movement_patterns = muscle_data.get("movement_patterns", [])
        if movement_patterns:
            patterns_str = "、".join(movement_patterns[:3])
            recommendations.append(f"建议包含以下动作模式：{patterns_str}")
        
        # 基于过度训练风险的建议
        if overtraining_risk and overtraining_risk.risk_level in ["HIGH", "CRITICAL"]:
            recommendations.append("⚠️ 优先考虑恢复，避免过度训练")
        
        # 通用建议
        recommendations.extend([
            "定期评估训练进展，根据反馈调整训练量",
            "保持训练日志，记录组数、次数和感受"
        ])
        
        return recommendations

