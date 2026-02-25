"""
TDEE计算器 MCP工具 — Thin Wrapper

计算逻辑已统一到 PHP Calculator Service (POST /api/calculators/tdee)。
本工具仅从 user_profile.nutrition_profile.auto_calculated 读取预计算结果。

前端/用户 → PHP API 计算 → save_to_profile → 本工具读取展示

版本: v2.0.0 (thin wrapper)
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
import time

from ...mcp_tools.base_tool import BaseMCPTool

logger = logging.getLogger(__name__)


class TDEECalculatorInput(BaseModel):
    """输入Schema — 仅需 user_id"""
    user_id: str = Field(..., description="用户ID")


class TDEECalculatorOutput(BaseModel):
    """输出Schema — 透传 PHP 预计算结果"""
    success: bool
    tool_name: str
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    target_calories: Optional[float] = None
    fitness_goal: Optional[str] = None
    macros: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    execution_time_ms: float = 0.0


class TDEECalculator(BaseMCPTool):
    """TDEE计算器 — 读取 PHP 预计算结果"""

    def get_name(self) -> str:
        return "tdee_calculator"

    def get_description(self) -> str:
        return "TDEE计算器 — 读取用户档案中的预计算TDEE/BMR/宏量数据"

    def get_category(self) -> str:
        return "nutrition"

    def get_input_schema(self) -> type[BaseModel]:
        return TDEECalculatorInput

    def get_output_schema(self) -> type[BaseModel]:
        return TDEECalculatorOutput

    def get_complexity(self) -> str:
        return "low"

    def get_estimated_duration(self) -> float:
        return 50.0

    def requires_user_profile(self) -> bool:
        return True

    def get_dependencies(self) -> List[str]:
        return ["user_profile_mcp"]

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从 user_profile.nutrition_profile.auto_calculated 读取预计算结果。
        如果用户尚未通过 PHP API 计算过 TDEE，返回引导提示。
        """
        start_time = time.time()

        try:
            user_profile = input_data.get("user_profile") or {}
            nutrition = user_profile.get("nutrition_profile") or {}

            # PHP save_to_profile 写入的字段名是 auto_calculated
            auto_calc = nutrition.get("auto_calculated") or {}

            if not auto_calc.get("tdee"):
                return {
                    "success": False,
                    "tool_name": self.get_name(),
                    "message": "用户尚未计算TDEE，请先使用计算器页面完善档案",
                    "execution_time_ms": (time.time() - start_time) * 1000,
                }

            self.logger.info(
                f"✅ TDEE读取完成: TDEE={auto_calc.get('tdee')}, "
                f"目标={auto_calc.get('target_calories')}"
            )

            return {
                "success": True,
                "tool_name": self.get_name(),
                "bmr": auto_calc.get("bmr"),
                "tdee": auto_calc.get("tdee"),
                "target_calories": auto_calc.get("target_calories"),
                "fitness_goal": auto_calc.get("fitness_goal"),
                "macros": auto_calc.get("macros"),
                "execution_time_ms": (time.time() - start_time) * 1000,
            }

        except Exception as e:
            self.logger.error(f"❌ TDEE读取失败: {e}", exc_info=True)
            return {
                "success": False,
                "tool_name": self.get_name(),
                "message": f"读取TDEE数据失败: {str(e)}",
                "execution_time_ms": (time.time() - start_time) * 1000,
            }
