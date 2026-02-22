# -*- coding: utf-8 -*-
"""
专业程序设计器 — 训练量计算 Mixin

包含：
- adjust_volume_by_level: 根据训练水平调整训练量
- apply_periodization_volume: 周期化训练量调整
- _call_volume_calculator: 调用训练量计算工具
- _detect_deload_days: 检测减量日位置
- _apply_deload_to_day: 应用减量日调整
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class VolumeMixin:
    """训练量计算 + 周期化 + 减量日逻辑"""

    def adjust_volume_by_level(
        self,
        volume_data: Dict[str, Any],
        fitness_level: str
    ) -> Dict[str, Any]:
        """
        根据训练水平调整训练量

        训练水平系数：
        - beginner: 0.7 | intermediate: 1.0 | advanced: 1.2 | elite: 1.4
        """
        level_coefficients = {
            "beginner": 0.7,
            "intermediate": 1.0,
            "advanced": 1.2,
            "elite": 1.4
        }

        coefficient = level_coefficients.get(fitness_level, 1.0)
        adjusted_data = volume_data.copy()

        if "mev" in adjusted_data:
            adjusted_data["mev"] = int(adjusted_data["mev"] * coefficient)
        if "mav" in adjusted_data:
            adjusted_data["mav"] = int(adjusted_data["mav"] * coefficient)
        if "mrv" in adjusted_data:
            adjusted_data["mrv"] = int(adjusted_data["mrv"] * coefficient)

        if "volume_recommendation" in adjusted_data:
            vol_rec = adjusted_data["volume_recommendation"]
            if "recommended_weekly_sets" in vol_rec:
                vol_rec["recommended_weekly_sets"] = int(
                    vol_rec["recommended_weekly_sets"] * coefficient
                )
            if "sets_per_session" in vol_rec:
                vol_rec["sets_per_session"] = int(
                    vol_rec["sets_per_session"] * coefficient
                )

        self.logger.info(
            f"📊 训练量调整: 水平={fitness_level}, "
            f"系数={coefficient}, "
            f"MEV={volume_data.get('mev', 'N/A')}→{adjusted_data.get('mev', 'N/A')}, "
            f"MAV={volume_data.get('mav', 'N/A')}→{adjusted_data.get('mav', 'N/A')}, "
            f"MRV={volume_data.get('mrv', 'N/A')}→{adjusted_data.get('mrv', 'N/A')}"
        )

        return adjusted_data

    def apply_periodization_volume(
        self,
        volume_data: Dict[str, Any],
        week_number: int
    ) -> Dict[str, Any]:
        """
        根据周期化原则调整训练量

        - 第1-2周：MAV（最大适应训练量）
        - 第3周：MRV（最大可恢复训练量，冲刺周）
        - 第4周：MEV（最小有效训练量，减量周）
        """
        adjusted_data = volume_data.copy()

        mev = volume_data.get("mev", 10)
        mav = volume_data.get("mav", 16)
        mrv = volume_data.get("mrv", 22)

        if week_number in [1, 2]:
            target_volume = mav
            phase_name = "积累期"
            phase_description = "使用最大适应训练量，诱导肌肥大适应"
        elif week_number == 3:
            target_volume = mrv
            phase_name = "冲刺期"
            phase_description = "使用最大可恢复训练量，达到训练峰值"
        elif week_number == 4:
            target_volume = mev
            phase_name = "减量期"
            phase_description = "使用最小有效训练量，促进超量恢复"
        else:
            cycle_week = ((week_number - 1) % 4) + 1
            return self.apply_periodization_volume(volume_data, cycle_week)

        if "volume_recommendation" in adjusted_data:
            vol_rec = adjusted_data["volume_recommendation"]
            if "recommended_weekly_sets" in vol_rec:
                vol_rec["recommended_weekly_sets"] = target_volume
            training_frequency = 2
            if "sets_per_session" in vol_rec:
                vol_rec["sets_per_session"] = max(1, target_volume // training_frequency)
            vol_rec["periodization_phase"] = phase_name
            vol_rec["phase_description"] = phase_description
            vol_rec["target_volume"] = target_volume

        self.logger.info(
            f"📊 周期化训练量调整: 第{week_number}周, "
            f"阶段={phase_name}, "
            f"目标训练量={target_volume}组/周, "
            f"MEV={mev}, MAV={mav}, MRV={mrv}"
        )

        return adjusted_data

    async def _call_volume_calculator(
        self,
        input_data: Dict[str, Any],
        muscle_group: str,
        week_number: int = 1
    ) -> Dict[str, Any]:
        """调用muscle_group_volume_calculator工具并根据训练水平和周期调整"""
        default_volume = {
            "mev": 10,
            "mav": 16,
            "mrv": 22,
            "volume_recommendation": {
                "recommended_weekly_sets": 12,
                "sets_per_session": 4,
                "reps_per_set_range": (8, 12),
                "rest_period_seconds": 90
            }
        }

        if not self.tool_registry:
            self.logger.warning("工具注册表未设置，返回默认训练量")
            fitness_level = input_data.get("difficulty_level", "intermediate")
            adjusted_volume = self.adjust_volume_by_level(default_volume, fitness_level)
            return self.apply_periodization_volume(adjusted_volume, week_number)

        try:
            calculator_input = {
                "user_id": input_data["user_id"],
                "muscle_group": muscle_group,
                "training_goal": input_data["training_goal"],
                "training_frequency_per_week": input_data["training_days_per_week"],
                "current_weekly_sets": None,
                "recovery_capacity": None
            }

            result = await self.tool_registry.call_tool(
                "muscle_group_volume_calculator",
                calculator_input
            )

            if result.get("success"):
                fitness_level = input_data.get("difficulty_level", "intermediate")
                adjusted_result = self.adjust_volume_by_level(result, fitness_level)
                return self.apply_periodization_volume(adjusted_result, week_number)
            else:
                self.logger.error(f"训练量计算失败: {result.get('error')}")

        except Exception as e:
            self.logger.error(f"调用muscle_group_volume_calculator失败: {e}", exc_info=True)

        # Fallback
        fitness_level = input_data.get("difficulty_level", "intermediate")
        adjusted_volume = self.adjust_volume_by_level(default_volume, fitness_level)
        return self.apply_periodization_volume(adjusted_volume, week_number)

    def _detect_deload_days(
        self,
        training_days: List[Dict[str, Any]]
    ) -> List[int]:
        """
        检测需要插入减量日的位置

        当连续训练≥3天时，自动插入减量日
        """
        deload_day_numbers = []
        consecutive_training_days = 0

        sorted_days = sorted(training_days, key=lambda d: d["day_number"])

        for i, day in enumerate(sorted_days):
            consecutive_training_days += 1

            if consecutive_training_days >= 3:
                deload_day_numbers.append(day["day_number"])
                self.logger.info(
                    f"🔄 检测到连续训练3天，"
                    f"将第{day['day_number']}天设置为减量日"
                )
                consecutive_training_days = 0

        return deload_day_numbers

    def _apply_deload_to_day(
        self,
        training_day: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将训练日转换为减量日

        减量日特点：训练量减半（50%），强度降至80%
        """
        deload_day = training_day.copy()
        deload_day["day_name"] = f"{training_day['day_name']} (减量日)"

        adjusted_exercises = []
        original_total_sets = 0
        adjusted_total_sets = 0

        for ex in training_day["exercises"]:
            adjusted_ex = ex.copy()

            original_sets = ex.get("sets", 3)
            adjusted_sets = max(1, (original_sets + 1) // 2)
            adjusted_ex["sets"] = adjusted_sets

            original_total_sets += original_sets
            adjusted_total_sets += adjusted_sets

            original_reps = ex.get("reps_range", (8, 12))
            if isinstance(original_reps, tuple) and len(original_reps) == 2:
                adjusted_reps = (max(1, int(original_reps[0] * 0.8)), original_reps[1])
                adjusted_ex["reps_range"] = adjusted_reps

            adjusted_ex["is_deload"] = True
            adjusted_ex["deload_note"] = "减量日：训练量50%，强度80%"

            adjusted_exercises.append(adjusted_ex)

        deload_day["exercises"] = adjusted_exercises
        deload_day["total_sets"] = adjusted_total_sets
        deload_day["is_deload_day"] = True

        original_duration = training_day.get("estimated_duration_minutes", 60)
        deload_day["estimated_duration_minutes"] = max(30, original_duration // 2)

        deload_day["notes"] = [
            "🔄 减量日：训练量减半（50%），强度降至80%",
            "💡 目的：促进中枢神经系统恢复，避免过度训练",
            "📊 科学依据：连续高强度训练会累积疲劳，减量日有助于超量恢复",
            "✅ 执行要点：保持动作质量，专注于肌肉感受，不追求极限重量",
            "⚠️ 重要：不要跳过减量日，这是训练计划的重要组成部分"
        ]

        self.logger.info(
            f"🔄 应用减量日调整: 第{deload_day['day_number']}天, "
            f"组数 {original_total_sets}→{adjusted_total_sets}, "
            f"时长 {original_duration}→{deload_day['estimated_duration_minutes']}分钟"
        )

        return deload_day
