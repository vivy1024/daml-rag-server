"""
智能重量计算器 - MCP工具

基于用户1RM、训练目标和RPE智能计算训练重量
使用科学公式和个体差异调整

根据训练目标调整重量百分比：
- 增肌训练：力量标准的60-80%
- 力量训练：力量标准的85-95%
- 耐力训练：力量标准的40-60%

作者: BUILD_BODY Team
版本: v2.2.0
最后更新: 2025-12-19
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging

from ..base_tool import BaseMCPTool

logger = logging.getLogger(__name__)


class TrainingGoal(str, Enum):
    """
    训练目标枚举
    
    包含基础训练目标和中国本地化扩展目标
    Requirements: 3.1, 3.2, 3.3
    """
    # 基础训练目标
    STRENGTH = "strength"                    # 力量提升
    HYPERTROPHY = "hypertrophy"              # 增肌
    ENDURANCE = "endurance"                  # 耐力
    GENERAL_FITNESS = "general_fitness"      # 综合健身
    
    # 中国本地化扩展目标 - Requirements 3.1, 3.2, 3.3
    FAT_LOSS = "fat_loss"                    # 减脂塑形 - Requirements 3.1
    POSTURE_CORRECTION = "posture_correction"  # 体态矫正 - Requirements 3.2
    FUNCTIONAL = "functional"                # 功能性训练 - Requirements 3.3


class UserLevel(str, Enum):
    """用户水平枚举"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class IntelligentWeightCalculatorInput(BaseModel):
    """输入Schema"""
    user_id: str = Field(..., description="用户ID")
    exercise_id: str = Field(..., description="动作ID")
    training_goal: TrainingGoal = Field(..., description="训练目标")
    reps_target: int = Field(..., description="目标重复次数", ge=1, le=30)
    rpe_target: float = Field(..., description="目标RPE (1-10)", ge=1, le=10)
    user_level: Optional[UserLevel] = Field(
        UserLevel.INTERMEDIATE,
        description="用户水平，默认intermediate"
    )


class WeightCalculation(BaseModel):
    """重量计算结果"""
    recommended_weight: float = Field(..., description="推荐重量(kg)")
    weight_range: Tuple[float, float] = Field(..., description="重量范围(kg)")
    reps_1rm_estimate: float = Field(..., description="估算1RM(kg)")
    percentage_of_1rm: float = Field(..., description="1RM百分比")
    rpe_correlation: float = Field(..., description="RPE相关性")


class WeightAdjustments(BaseModel):
    """重量调整因子"""
    level_adjustment: float = Field(..., description="水平调整因子")
    goal_adjustment: float = Field(..., description="目标调整因子")
    fatigue_adjustment: float = Field(..., description="疲劳调整因子")
    total_adjustment: float = Field(..., description="总调整因子")


class IntelligentWeightCalculatorOutput(BaseModel):
    """输出Schema"""
    success: bool
    tool_name: str
    calculation: WeightCalculation
    adjustments: WeightAdjustments
    safety_considerations: List[str]
    progression_guidelines: List[str]
    execution_time_ms: float
    confidence_score: Optional[float] = None


class IntelligentWeightCalculator(BaseMCPTool):
    """智能重量计算器工具"""

    def get_name(self) -> str:
        return "intelligent_weight_calculator"

    def get_description(self) -> str:
        return "智能重量计算器 - 基于用户1RM、训练目标和RPE智能计算训练重量"

    def get_category(self) -> str:
        return "training"

    def get_input_schema(self) -> type[BaseModel]:
        return IntelligentWeightCalculatorInput

    def get_output_schema(self) -> type[BaseModel]:
        return IntelligentWeightCalculatorOutput

    def get_complexity(self) -> str:
        return "medium"

    def get_estimated_duration(self) -> float:
        return 300.0

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行智能重量计算

        流程：
        1. 获取动作信息
        2. 计算基础1RM
        3. 应用调整因子
        4. 计算推荐重量
        5. 生成安全考虑和进阶指导
        """
        import time
        start_time = time.time()

        try:
            user_id = input_data["user_id"]
            exercise_id = input_data["exercise_id"]
            training_goal = input_data["training_goal"]
            reps_target = input_data["reps_target"]
            rpe_target = input_data["rpe_target"]
            user_level = input_data.get("user_level", "intermediate")

            # 1. 获取动作信息
            exercise_info = await self._get_exercise_info(exercise_id)

            # 2. 计算基础1RM
            base_1rm = await self._calculate_base_1rm(exercise_id, user_id)

            # 3. 应用调整因子
            adjustments = self._calculate_adjustments(
                user_level, training_goal, rpe_target
            )

            # 4. 计算推荐重量
            calculation = self._calculate_recommended_weight(
                base_1rm, reps_target, rpe_target, adjustments, training_goal
            )

            # 5. 生成安全考虑
            safety_considerations = self._generate_safety_considerations(
                exercise_id, user_level
            )

            # 6. 生成进阶指导
            progression_guidelines = self._generate_progression_guidelines(
                training_goal, reps_target
            )

            execution_time_ms = (time.time() - start_time) * 1000

            self.logger.info(
                f"✅ 智能重量计算完成 - 动作: {exercise_id}, "
                f"推荐重量: {calculation['recommended_weight']}kg"
            )

            return {
                "success": True,
                "tool_name": self.get_name(),
                "calculation": calculation,
                "adjustments": adjustments,
                "safety_considerations": safety_considerations,
                "progression_guidelines": progression_guidelines,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 85.0
            }

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"❌ 智能重量计算失败: {e}", exc_info=True)

            return {
                "success": False,
                "tool_name": self.get_name(),
                "calculation": {
                    "recommended_weight": 0.0,
                    "weight_range": (0.0, 0.0),
                    "reps_1rm_estimate": 0.0,
                    "percentage_of_1rm": 0.0,
                    "rpe_correlation": 0.0
                },
                "adjustments": {
                    "level_adjustment": 0.0,
                    "goal_adjustment": 0.0,
                    "fatigue_adjustment": 0.0,
                    "total_adjustment": 0.0
                },
                "safety_considerations": ["计算过程中发生错误"],
                "progression_guidelines": ["请检查输入参数"],
                "execution_time_ms": execution_time_ms,
                "confidence_score": 0.0
            }

    async def _get_exercise_info(self, exercise_id: str) -> Dict[str, Any]:
        """获取动作信息"""
        # 注意：Neo4j Exercise节点使用 id 字段，不是 exercise_id
        # difficulty 字段，不是 difficulty_level
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        RETURN e.mechanic_zh as mechanic, 
               e.force_zh as force, 
               e.difficulty_zh as difficulty
        """

        try:
            results = await self.neo4j_client.run_query(
                query, {"exercise_id": exercise_id}
            )
            if results:
                return results[0]
            return {}
        except Exception as e:
            self.logger.warning(f"获取动作信息失败: {e}")
            return {}

    async def _calculate_base_1rm(
        self, exercise_id: str, user_id: str
    ) -> float:
        """
        计算基础1RM

        简化实现：基于动作类型和用户水平估算1RM
        实际应该查询用户的训练历史
        """
        # 基础1RM估算表（kg）
        base_1rm_estimates = {
            "bench_press": {
                "beginner": 60.0,
                "intermediate": 80.0,
                "advanced": 120.0
            },
            "squat": {
                "beginner": 80.0,
                "intermediate": 120.0,
                "advanced": 180.0
            },
            "deadlift": {
                "beginner": 100.0,
                "intermediate": 140.0,
                "advanced": 200.0
            },
            "overhead_press": {
                "beginner": 35.0,
                "intermediate": 50.0,
                "advanced": 70.0
            }
        }

        # 默认返回中等水平的估算值
        if exercise_id in base_1rm_estimates:
            return base_1rm_estimates[exercise_id]["intermediate"]

        # 未知动作，返回默认值
        return 70.0

    def _calculate_adjustments(
        self, user_level: str, training_goal: str, rpe_target: float
    ) -> Dict[str, float]:
        """
        计算调整因子
        
        根据训练目标调整重量百分比（基于力量标准）：
        - 增肌训练：力量标准的60-80%（中位数70%）
        - 力量训练：力量标准的85-95%（中位数90%）
        - 耐力训练：力量标准的40-60%（中位数50%）
        - 一般健身：力量标准的65-75%（中位数70%）
        """
        # 水平调整
        level_adjustments = {
            "beginner": 0.7,
            "intermediate": 1.0,
            "advanced": 1.3
        }
        level_adjustment = level_adjustments.get(user_level, 1.0)

        # 目标调整（基于力量标准的百分比）
        # 这些百分比是相对于用户1RM（力量标准）的训练重量
        goal_adjustments = {
            "strength": 0.90,      # 力量训练：85-95%，中位数90%
            "hypertrophy": 0.70,   # 增肌训练：60-80%，中位数70%
            "endurance": 0.50,     # 耐力训练：40-60%，中位数50%
            "general_fitness": 0.70  # 一般健身：65-75%，中位数70%
        }
        goal_adjustment = goal_adjustments.get(training_goal, 0.70)

        # 疲劳调整（RPE影响）
        fatigue_adjustment = max(0.5, 1 - (rpe_target - 6) * 0.1)

        # 总调整因子
        total_adjustment = level_adjustment * goal_adjustment * fatigue_adjustment

        return {
            "level_adjustment": level_adjustment,
            "goal_adjustment": goal_adjustment,
            "fatigue_adjustment": fatigue_adjustment,
            "total_adjustment": total_adjustment
        }

    def _calculate_recommended_weight(
        self,
        base_1rm: float,
        reps_target: int,
        rpe_target: float,
        adjustments: Dict[str, float],
        training_goal: str
    ) -> Dict[str, Any]:
        """计算推荐重量"""
        # 使用RPE表和反推公式
        rpe_percentage = self._get_rpe_percentage(rpe_target)

        # 根据目标重复次数调整
        reps_adjustment = self._get_reps_adjustment(reps_target, training_goal)

        # 计算推荐1RM
        adjusted_1rm = base_1rm * adjustments["total_adjustment"]

        # 计算推荐重量
        recommended_weight = adjusted_1rm * rpe_percentage * reps_adjustment

        # 重量范围（±5%）
        weight_range = (
            round(recommended_weight * 0.95, 1),
            round(recommended_weight * 1.05, 1)
        )

        return {
            "recommended_weight": round(recommended_weight, 1),
            "weight_range": weight_range,
            "reps_1rm_estimate": round(adjusted_1rm, 1),
            "percentage_of_1rm": round(rpe_percentage * 100, 1),
            "rpe_correlation": rpe_target
        }

    def _get_rpe_percentage(self, rpe: float) -> float:
        """获取RPE百分比"""
        rpe_table = {
            10.0: 1.0,
            9.5: 0.975,
            9.0: 0.95,
            8.5: 0.925,
            8.0: 0.90,
            7.5: 0.875,
            7.0: 0.85,
            6.5: 0.825,
            6.0: 0.80,
            5.5: 0.775,
            5.0: 0.75
        }

        # 四舍五入到0.5
        rounded_rpe = round(rpe * 2) / 2
        return rpe_table.get(rounded_rpe, 0.85)

    def _get_reps_adjustment(self, reps: int, goal: str) -> float:
        """获取重复次数调整"""
        goal_reps_targets = {
            "strength": 3,
            "hypertrophy": 10,
            "endurance": 15,
            "general_fitness": 8
        }

        target = goal_reps_targets.get(goal, 8)
        adjustment = max(0.7, 1 - abs(reps - target) * 0.02)

        return adjustment

    def _generate_safety_considerations(
        self, exercise_id: str, user_level: str
    ) -> List[str]:
        """生成安全考虑"""
        considerations = [
            "充分热身后再使用推荐重量",
            "如有技术不熟练，建议降低10-15%重量",
            "确保动作质量和控制"
        ]

        if user_level == "beginner":
            considerations.append("初学者建议在教练指导下训练")
            considerations.append("优先掌握动作技术，再增加重量")

        if exercise_id in ["squat", "deadlift"]:
            considerations.append("大重量动作建议有保护员")

        considerations.append("倾听身体信号，如有不适立即停止")

        return considerations

    def _generate_progression_guidelines(
        self, training_goal: str, reps_target: int
    ) -> List[str]:
        """生成进阶指导"""
        guidelines = []

        if training_goal == "strength":
            guidelines.extend([
                "力量训练：使用力量标准的85-95%重量",
                "每次增加2.5-5kg重量",
                "保持重复次数在1-5次范围内",
                "当能完成5次时，增加重量"
            ])
        elif training_goal == "hypertrophy":
            guidelines.extend([
                "增肌训练：使用力量标准的60-80%重量",
                "每次增加2.5kg重量",
                "在目标重复次数范围内调整重量（8-12次）",
                "当能完成上限次数时，增加重量"
            ])
        elif training_goal == "endurance":
            guidelines.extend([
                "耐力训练：使用力量标准的40-60%重量",
                "每次增加1-2.5kg重量",
                "保持重复次数在15-20次范围内",
                "注重动作质量和肌肉耐力"
            ])
        else:
            guidelines.extend([
                "一般健身：使用力量标准的65-75%重量",
                "根据RPE调整重量，保持在目标范围内"
            ])

        guidelines.extend([
            "每周评估一次，根据表现调整",
            "记录训练日志，追踪进展"
        ])

        return guidelines
