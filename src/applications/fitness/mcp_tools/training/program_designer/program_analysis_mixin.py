# -*- coding: utf-8 -*-
"""
专业程序设计器 — 计划分析 Mixin

包含：
- _analyze_program_balance: 平衡性分析
- _perform_safety_assessment: 安全评估
- _generate_execution_guidelines: 执行建议
- _generate_important_notes: 注意事项
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ProgramAnalysisMixin:
    """平衡分析 + 安全评估 + 执行建议 + 注意事项"""

    def _analyze_program_balance(
        self,
        weekly_program: Dict[str, Any],
        muscle_group_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析计划平衡性"""
        training_days = weekly_program["training_days"]
        muscle_distribution = weekly_program["muscle_group_distribution"]

        # 1. 分析肌群覆盖
        muscle_group_coverage = {}
        for muscle_group, sets in muscle_distribution.items():
            volume_data = muscle_group_data.get(muscle_group, {}).get("volume_data", {})
            mev = volume_data.get("mev", 10)
            mav = volume_data.get("mav", 16)

            if sets >= mav:
                coverage = "充分"
            elif sets >= mev:
                coverage = "适中"
            else:
                coverage = "不足"
            muscle_group_coverage[muscle_group] = coverage

        # 2. 分析动作模式平衡
        movement_pattern_balance = {}
        for day in training_days:
            for ex in day["exercises"]:
                category = ex.get("category", "Unknown")
                movement_pattern_balance[category] = movement_pattern_balance.get(category, 0) + 1

        # 3. 计算推拉比例
        push_count = sum(
            1 for day in training_days
            for ex in day["exercises"]
            if any(m in ["胸大肌", "三角肌", "肱三头肌"] for m in ex.get("primary_muscles", []))
        )
        pull_count = sum(
            1 for day in training_days
            for ex in day["exercises"]
            if any(m in ["背阔肌", "肱二头肌"] for m in ex.get("primary_muscles", []))
        )

        push_pull_ratio = f"{push_count}:{pull_count}" if pull_count > 0 else f"{push_count}:0"

        # 4. 计算复合/孤立比例
        compound_count = sum(
            1 for day in training_days
            for ex in day["exercises"]
            if "复合" in ex.get("category", "") or len(ex.get("primary_muscles", [])) > 1
        )
        isolation_count = sum(
            1 for day in training_days
            for ex in day["exercises"]
            if "孤立" in ex.get("category", "")
        )

        compound_isolation_ratio = (
            f"{compound_count}:{isolation_count}" if isolation_count > 0
            else f"{compound_count}:0"
        )

        # 5. 计算平衡评分
        balance_score = 100.0
        insufficient_count = sum(1 for c in muscle_group_coverage.values() if c == "不足")
        balance_score -= insufficient_count * 10

        if push_count > 0 and pull_count > 0:
            ratio = push_count / pull_count
            if ratio < 0.7 or ratio > 1.5:
                balance_score -= 10

        balance_score = max(0.0, balance_score)

        # 6. 生成建议
        recommendations = []
        for muscle_group, coverage in muscle_group_coverage.items():
            if coverage == "不足":
                recommendations.append(f"增加{muscle_group}的训练量")

        if push_count > pull_count * 1.5:
            recommendations.append("增加拉类动作，平衡推拉比例")
        elif pull_count > push_count * 1.5:
            recommendations.append("增加推类动作，平衡推拉比例")

        if compound_count < isolation_count:
            recommendations.append("增加复合动作比例，提高训练效率")

        return {
            "muscle_group_coverage": muscle_group_coverage,
            "movement_pattern_balance": movement_pattern_balance,
            "push_pull_ratio": push_pull_ratio,
            "compound_isolation_ratio": compound_isolation_ratio,
            "balance_score": balance_score,
            "recommendations": recommendations
        }

    async def _perform_safety_assessment(
        self,
        weekly_program: Dict[str, Any],
        input_data: Dict[str, Any],
        tools_called: List[str]
    ) -> Dict[str, Any]:
        """进行安全评估"""
        default_safe = {
            "overall_risk_level": "LOW",
            "high_risk_exercises": [],
            "contraindications_found": 0,
            "safety_recommendations": [],
            "medical_consultation_needed": False
        }

        if not self.tool_registry:
            self.logger.warning("工具注册表未设置，跳过安全评估")
            return default_safe

        try:
            exercise_ids = []
            for day in weekly_program["training_days"]:
                for ex in day["exercises"]:
                    exercise_id = ex.get("exercise_id")
                    if exercise_id and exercise_id not in exercise_ids:
                        exercise_ids.append(exercise_id)

            if not exercise_ids:
                return default_safe

            checker_input = {
                "user_id": input_data["user_id"],
                "exercise_ids": exercise_ids,
                "health_conditions": input_data.get("injury_history"),
                "include_recommendations": True,
                "strict_mode": False
            }

            result = await self.tool_registry.call_tool(
                "contraindications_checker",
                checker_input
            )
            tools_called.append("contraindications_checker")

            if result.get("success"):
                high_risk_exercises = [
                    ex["exercise_name_zh"]
                    for ex in result.get("exercise_results", [])
                    if ex.get("max_risk_level") in ["HIGH", "CRITICAL"]
                ]
                safety_recommendations = result.get("overall_assessment", {}).get("recommendations", [])

                return {
                    "overall_risk_level": result.get("overall_assessment", {}).get("risk_level", "LOW"),
                    "high_risk_exercises": high_risk_exercises,
                    "contraindications_found": result.get("exercises_with_contraindications", 0),
                    "safety_recommendations": safety_recommendations,
                    "medical_consultation_needed": result.get("overall_assessment", {}).get("risk_level") in ["HIGH", "CRITICAL"]
                }
            else:
                self.logger.error(f"安全评估失败: {result.get('error')}")

        except Exception as e:
            self.logger.error(f"调用contraindications_checker失败: {e}", exc_info=True)

        return {
            "overall_risk_level": "MODERATE",
            "high_risk_exercises": [],
            "contraindications_found": 0,
            "safety_recommendations": ["安全评估出错，建议谨慎训练"],
            "medical_consultation_needed": False
        }

    def _generate_execution_guidelines(
        self,
        input_data: Dict[str, Any],
        weekly_program: Dict[str, Any],
        program_balance: Dict[str, Any],
        safety_assessment: Dict[str, Any],
        applicable_standard: Dict[str, Any]
    ) -> List[str]:
        """生成执行建议（包含标准引用）"""
        guidelines = []

        guidelines.append(
            f"📚 科学依据：本计划基于{applicable_standard['standard_name']}制定"
        )
        guidelines.append(
            f"   {applicable_standard['application_reason']}"
        )

        training_goal = input_data["training_goal"]
        if training_goal == "strength":
            guidelines.append("力量训练：注重动作质量和渐进超负荷")
        elif training_goal == "hypertrophy":
            guidelines.append("肌肥大训练：保持肌肉张力和代谢压力")
        elif training_goal == "endurance":
            guidelines.append("耐力训练：控制休息时间，保持训练密度")

        cycle_days = weekly_program.get("cycle_days", 7)
        training_pattern = weekly_program.get("training_pattern", "")

        if cycle_days <= 4:
            guidelines.append(
                f"训练周期为{cycle_days}天（{training_pattern}），"
                f"注意在每个周期结束后充分休息恢复"
            )

        if training_pattern == "练三休一":
            guidelines.append("推拉腿分化：每3天训练后休息1天，确保肌群充分恢复")
        elif training_pattern == "练六休一":
            guidelines.append("高频训练：连续6天训练后休息1天，注意监控疲劳水平")
        elif training_pattern == "练二休一":
            guidelines.append("上下肢分化：每2天训练后休息1天，平衡训练强度")

        has_deload_days = weekly_program.get("has_deload_days", False)
        deload_days_count = weekly_program.get("deload_days_count", 0)

        if has_deload_days:
            guidelines.append(
                f"🔄 减量日管理：本计划包含{deload_days_count}个减量日，"
                f"用于促进中枢神经系统恢复"
            )
            guidelines.append(
                "减量日执行要点：训练量减半（50%），强度降至80%，"
                "专注于动作质量和肌肉感受"
            )
            guidelines.append(
                "⚠️ 重要：不要跳过减量日，这是避免过度训练和促进超量恢复的关键"
            )

        guidelines.extend([
            "每次训练前进行充分热身（5-10分钟）",
            "训练后进行拉伸放松（5-10分钟）",
            "保持训练日志，记录组数、次数和感受",
            "根据身体反馈调整训练强度"
        ])

        return guidelines

    def _generate_important_notes(
        self,
        input_data: Dict[str, Any],
        safety_assessment: Dict[str, Any],
        program_balance: Dict[str, Any],
        weekly_program: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """生成注意事项"""
        notes = []

        if safety_assessment["overall_risk_level"] in ["HIGH", "CRITICAL"]:
            notes.append("⚠️ 存在高风险动作，建议在专业人士指导下进行")

        if safety_assessment["medical_consultation_needed"]:
            notes.append("⚠️ 建议在开始训练前咨询医疗专业人士")

        if program_balance["balance_score"] < 70:
            notes.append("注意：计划平衡性有待改善，建议调整动作选择")

        if weekly_program:
            has_deload_days = weekly_program.get("has_deload_days", False)
            deload_day_numbers = weekly_program.get("deload_day_numbers", [])

            if has_deload_days:
                notes.append(
                    f"🔄 减量日安排：第{', '.join(map(str, deload_day_numbers))}天为减量日"
                )
                notes.append(
                    "💡 减量日科学依据：连续高强度训练会累积中枢神经系统疲劳，"
                    "减量日有助于神经系统恢复和超量恢复"
                )
                notes.append(
                    "📊 研究表明：适当的减量日可以提高训练效果，"
                    "降低过度训练风险，促进长期进步"
                )

        notes.extend([
            "如有不适立即停止训练",
            "保证充足睡眠和营养摄入",
            "定期评估训练进展"
        ])

        return notes
