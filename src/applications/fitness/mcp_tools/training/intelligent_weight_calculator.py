"""
智能重量计算器 MCP工具 — Thin Wrapper

计算逻辑已统一到 PHP Calculator Service:
- POST /api/calculators/one-rm (1RM估算)
- POST /api/calculators/weight (重量推荐)
- POST /api/calculators/intensity (RPE/RIR/%1RM转换)

本工具从 user_profile.strength_data 读取预计算结果，
结合 personal_bests 提供个性化重量建议。

版本: v3.0.0 (thin wrapper)
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging
import time

from ..base_tool import BaseMCPTool
from ...types.enums import TrainingGoal, DifficultyLevel

logger = logging.getLogger(__name__)

# 保持向后兼容
UserLevel = DifficultyLevel


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


class IntelligentWeightCalculatorOutput(BaseModel):
    """输出Schema"""
    success: bool
    tool_name: str
    recommended_weight: Optional[float] = None
    weight_range: Optional[Tuple[float, float]] = None
    estimated_1rm: Optional[float] = None
    training_goal: Optional[str] = None
    safety_considerations: List[str] = []
    message: Optional[str] = None
    execution_time_ms: float = 0.0


class IntelligentWeightCalculator(BaseMCPTool):
    """智能重量计算器 — 读取 PHP 预计算结果"""

    def get_name(self) -> str:
        return "intelligent_weight_calculator"

    def get_description(self) -> str:
        return "智能重量计算器 — 基于用户力量档案推荐训练重量"

    def get_category(self) -> str:
        return "training"

    def get_input_schema(self) -> type[BaseModel]:
        return IntelligentWeightCalculatorInput

    def get_output_schema(self) -> type[BaseModel]:
        return IntelligentWeightCalculatorOutput

    def get_complexity(self) -> str:
        return "low"

    def get_estimated_duration(self) -> float:
        return 50.0

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从 user_profile.strength_data 和 personal_bests 读取预计算结果。
        PHP WeightRecommender 已完成核心计算，这里只做数据组装和安全提示。
        """
        start_time = time.time()

        try:
            exercise_id = input_data["exercise_id"]
            training_goal = input_data["training_goal"]
            reps_target = input_data["reps_target"]
            rpe_target = input_data["rpe_target"]
            user_level = input_data.get("user_level", "intermediate")

            user_profile = input_data.get("user_profile") or {}
            strength_data = user_profile.get("strength_data") or {}
            personal_bests = strength_data.get("personal_bests") or {}

            # 查找该动作的 1RM 记录
            exercise_1rm = personal_bests.get(exercise_id, {}).get("estimated_1rm")

            if not exercise_1rm:
                return {
                    "success": False,
                    "tool_name": self.get_name(),
                    "message": (
                        f"未找到动作 {exercise_id} 的1RM记录。"
                        "请先通过训练记录或1RM计算器建立力量基线。"
                    ),
                    "safety_considerations": [
                        "建议从较轻重量开始，逐步找到合适的训练重量",
                        "首次训练新动作时，优先掌握动作技术",
                    ],
                    "execution_time_ms": (time.time() - start_time) * 1000,
                }

            # 基于 PHP WeightRecommender 的逻辑简化版：
            # 目标百分比范围（与 PHP GOAL_PROFILES 一致）
            goal_profiles = {
                "strength": {"min_pct": 85, "max_pct": 95},
                "hypertrophy": {"min_pct": 67, "max_pct": 82},
                "endurance": {"min_pct": 50, "max_pct": 65},
                "power": {"min_pct": 75, "max_pct": 90},
                "general_fitness": {"min_pct": 60, "max_pct": 75},
            }
            profile = goal_profiles.get(training_goal, goal_profiles["hypertrophy"])
            mid_pct = (profile["min_pct"] + profile["max_pct"]) / 2 / 100

            recommended = exercise_1rm * mid_pct
            # 向下取整到 2.5kg
            recommended = int(recommended / 2.5) * 2.5

            weight_min = int(exercise_1rm * profile["min_pct"] / 100 / 2.5) * 2.5
            weight_max = int(exercise_1rm * profile["max_pct"] / 100 / 2.5) * 2.5

            safety = self._build_safety_tips(user_level, exercise_id)

            self.logger.info(
                f"✅ 重量推荐完成 - 动作: {exercise_id}, "
                f"推荐: {recommended}kg ({profile['min_pct']}-{profile['max_pct']}% 1RM)"
            )

            return {
                "success": True,
                "tool_name": self.get_name(),
                "recommended_weight": recommended,
                "weight_range": (weight_min, weight_max),
                "estimated_1rm": exercise_1rm,
                "training_goal": training_goal,
                "safety_considerations": safety,
                "execution_time_ms": (time.time() - start_time) * 1000,
            }

        except Exception as e:
            self.logger.error(f"❌ 重量推荐失败: {e}", exc_info=True)
            return {
                "success": False,
                "tool_name": self.get_name(),
                "message": f"重量推荐失败: {str(e)}",
                "safety_considerations": ["计算过程中发生错误，请检查输入参数"],
                "execution_time_ms": (time.time() - start_time) * 1000,
            }

    @staticmethod
    def _build_safety_tips(user_level: str, exercise_id: str) -> List[str]:
        """构建安全提示"""
        tips = [
            "充分热身后再使用推荐重量",
            "确保动作质量和控制",
        ]
        if user_level == "beginner":
            tips.append("初学者建议在教练指导下训练")
            tips.append("优先掌握动作技术，再增加重量")
        if exercise_id in ("squat", "deadlift", "bench_press"):
            tips.append("大重量复合动作建议有保护员")
        tips.append("倾听身体信号，如有不适立即停止")
        return tips
