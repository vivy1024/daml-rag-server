# -*- coding: utf-8 -*-
"""
专业程序设计器 MCP工具

综合多个工具结果生成完整训练计划。
通过 Mixin 模式将方法分散到独立模块，保持 API 完全向后兼容。

拆分结构:
- program_designer/models.py: 枚举 + Pydantic schemas
- program_designer/volume_mixin.py: 训练量计算 + 周期化 + 减量日
- program_designer/program_generator_mixin.py: 周计划生成 + 训练日创建
- program_designer/program_analysis_mixin.py: 平衡分析 + 安全评估 + 建议

作者: BUILD_BODY Team
版本: v2.0.0
日期: 2026-01-06
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from ..base_tool import BaseMCPTool

# Re-export models for backward compatibility
from .program_designer.models import (
    TrainingGoal,
    TrainingSplit,
    DifficultyLevel,
    ProfessionalProgramDesignerInput,
    ExerciseInProgram,
    TrainingDay,
    WeeklyProgram,
    ProgramBalance,
    SafetyAssessment,
    ProfessionalProgramDesignerOutput,
)

from .program_designer.volume_mixin import VolumeMixin
from .program_designer.program_generator_mixin import ProgramGeneratorMixin
from .program_designer.program_analysis_mixin import ProgramAnalysisMixin

logger = logging.getLogger(__name__)


class ProfessionalProgramDesigner(
    BaseMCPTool,
    VolumeMixin,
    ProgramGeneratorMixin,
    ProgramAnalysisMixin,
):
    """
    专业程序设计器

    整合多个MCP工具生成完整训练计划：
    - intelligent_exercise_selector: 获取动作推荐
    - muscle_group_volume_calculator: 获取训练量
    - contraindications_checker: 确保安全
    """

    def __init__(
        self,
        neo4j_client,
        qdrant_client,
        three_layer_engine,
        logger: Optional[logging.Logger] = None,
        tool_registry=None
    ):
        super().__init__(neo4j_client, qdrant_client, three_layer_engine, logger)
        self.tool_registry = tool_registry

    def get_name(self) -> str:
        return "professional_program_designer"

    def get_description(self) -> str:
        return "专业程序设计器 - 整合多个工具生成完整训练计划，确保肌群平衡和充分恢复"

    def get_category(self) -> str:
        return "training"

    def get_input_schema(self) -> type[BaseModel]:
        return ProfessionalProgramDesignerInput

    def get_output_schema(self) -> type[BaseModel]:
        return ProfessionalProgramDesignerOutput

    def get_complexity(self) -> str:
        return "complex"

    def get_estimated_duration(self) -> float:
        return 5000.0

    def requires_user_profile(self) -> bool:
        return True

    def get_dependencies(self) -> List[str]:
        return [
            "neo4j",
            "qdrant",
            "three_layer_engine",
            "intelligent_exercise_selector",
            "muscle_group_volume_calculator",
            "contraindications_checker"
        ]

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行专业程序设计

        流程：
        1. 确定适用训练标准 → 2. 计算训练周期 → 3. 确定目标肌群
        4. 为每星期生成训练计划 → 5. 平衡性分析 → 6. 安全评估
        7. 执行建议 → 8. 注意事项
        """
        import time
        start_time = time.time()

        tools_called = []

        try:
            # Step 1: 确定适用的训练标准
            applicable_standard = self._determine_applicable_standard(input_data)
            self.logger.info(
                f"📚 确定训练标准: {applicable_standard['standard_name']}, "
                f"原因: {applicable_standard['application_reason'][:50]}..."
            )

            # Step 2: 计算训练周期
            cycle_info = self._calculate_training_cycle(input_data)

            # Step 3: 确定目标肌群
            target_muscle_groups = self._determine_target_muscle_groups(input_data)

            # Step 4: 获取训练周数
            training_weeks = input_data.get("training_weeks", 4)

            # Step 5: 为每星期生成训练计划（应用周期化训练量）
            weekly_programs = []

            for week_num in range(1, training_weeks + 1):
                muscle_group_data = await self._gather_muscle_group_data(
                    input_data, target_muscle_groups, tools_called,
                    week_number=week_num
                )

                weekly_program = self._generate_weekly_program(
                    input_data, muscle_group_data, cycle_info
                )
                weekly_program["week_number"] = week_num

                # 添加周期化信息
                cycle_week = ((week_num - 1) % 4) + 1
                if cycle_week in [1, 2]:
                    weekly_program["periodization_phase"] = "积累期"
                    weekly_program["phase_description"] = "使用最大适应训练量（MAV），诱导肌肥大适应"
                elif cycle_week == 3:
                    weekly_program["periodization_phase"] = "冲刺期"
                    weekly_program["phase_description"] = "使用最大可恢复训练量（MRV），达到训练峰值"
                else:
                    weekly_program["periodization_phase"] = "减量期"
                    weekly_program["phase_description"] = "使用最小有效训练量（MEV），促进超量恢复"

                weekly_programs.append(weekly_program)

                self.logger.info(
                    f"📅 第{week_num}训练周期计划生成完成: "
                    f"阶段={weekly_program['periodization_phase']}, "
                    f"总组数={weekly_program['total_weekly_sets']}"
                )

            # Step 6: 使用第1周的数据进行平衡性分析
            first_week_program = weekly_programs[0]
            first_week_muscle_data = await self._gather_muscle_group_data(
                input_data, target_muscle_groups, tools_called, week_number=1
            )

            program_balance = self._analyze_program_balance(
                first_week_program, first_week_muscle_data
            )

            # Step 7: 安全评估
            safety_assessment = await self._perform_safety_assessment(
                first_week_program, input_data, tools_called
            )

            # Step 8: 执行建议
            execution_guidelines = self._generate_execution_guidelines(
                input_data, first_week_program, program_balance,
                safety_assessment, applicable_standard
            )
            execution_guidelines.extend([
                f"周期化训练：第1-2训练周期积累期（MAV），第3训练周期冲刺期（MRV），第4训练周期减量期（MEV）",
                "训练量波动：根据训练周期调整训练量，避免过度训练和停滞",
                "监控恢复：注意疲劳累积，必要时提前进入减量训练周期"
            ])

            # Step 9: 注意事项
            important_notes = self._generate_important_notes(
                input_data, safety_assessment, program_balance, first_week_program
            )
            important_notes.extend([
                "⚠️ 第3训练周期（冲刺期）训练量最大，注意监控疲劳水平",
                "✅ 第4训练周期（减量期）是恢复期，不要跳过或增加训练量",
                "📊 记录每个训练周期的训练感受，根据恢复情况调整下一周期"
            ])

            # 生成计划概览
            total_exercises = sum(
                len(day["exercises"])
                for week in weekly_programs
                for day in week["training_days"]
            )
            total_weekly_sets_avg = sum(
                week["total_weekly_sets"] for week in weekly_programs
            ) / len(weekly_programs)
            total_deload_days = sum(
                week.get("deload_days_count", 0) for week in weekly_programs
            )

            program_overview = {
                "training_goal": input_data["training_goal"],
                "training_split": input_data["training_split"],
                "training_days_per_week": input_data["training_days_per_week"],
                "difficulty_level": input_data["difficulty_level"],
                "total_exercises": total_exercises,
                "average_weekly_sets": int(total_weekly_sets_avg),
                "estimated_weekly_duration_minutes": sum(
                    day["estimated_duration_minutes"] for day in first_week_program["training_days"]
                ),
                "training_weeks": training_weeks,
                "cycle_days": cycle_info["cycle_days"],
                "cycles_per_week": cycle_info["cycles_per_week"],
                "training_pattern": cycle_info["training_pattern"],
                "total_cycles": int(cycle_info["cycles_per_week"] * training_weeks),
                "periodization_model": "4周周期化模型",
                "week_1_2_phase": "积累期（MAV）",
                "week_3_phase": "冲刺期（MRV）",
                "week_4_phase": "减量期（MEV）",
                "has_deload_days": total_deload_days > 0,
                "total_deload_days": total_deload_days,
                "deload_day_description": "连续训练≥3天时自动插入减量日，训练量50%，强度80%",
                "scientific_basis": {
                    "standard_name": applicable_standard["standard_name"],
                    "standard_full_name": applicable_standard["standard_full_name"],
                    "standard_description": applicable_standard["standard_description"],
                    "application_reason": applicable_standard["application_reason"],
                    "key_principles": applicable_standard["key_principles"],
                    "reference": applicable_standard["reference"],
                    "适用场景": applicable_standard["适用场景"]
                }
            }

            execution_time_ms = (time.time() - start_time) * 1000

            result = {
                "success": True,
                "tool_name": self.get_name(),
                "user_id": input_data["user_id"],
                "program_overview": program_overview,
                "weekly_programs": weekly_programs,
                "weekly_program": first_week_program,
                "program_balance": program_balance,
                "safety_assessment": safety_assessment,
                "execution_guidelines": execution_guidelines,
                "important_notes": important_notes,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 90.0,
                "tools_called": tools_called
            }

            self.logger.info(
                f"✅ 专业程序设计完成: {input_data['training_split']}, "
                f"{len(first_week_program['training_days'])}天/周, "
                f"平均{int(total_weekly_sets_avg)}组/周, "
                f"周期={cycle_info['cycle_days']}天, "
                f"模式={cycle_info['training_pattern']}, "
                f"总周数={training_weeks}周, "
                f"周期化模型=4周（积累-冲刺-减量）, "
                f"减量日={total_deload_days}天"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ 专业程序设计失败: {e}", exc_info=True)
            raise

    def _calculate_training_cycle(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算实际训练周期"""
        training_split = input_data["training_split"]
        training_days_per_week = input_data["training_days_per_week"]

        if training_split == "push_pull_legs":
            base_cycle = 3
            if training_days_per_week == 3:
                cycle_days = 4
                training_pattern = "练三休一"
            elif training_days_per_week == 6:
                cycle_days = 7
                training_pattern = "练六休一"
            else:
                cycle_days = 7
                training_pattern = f"每星期{training_days_per_week}天"

        elif training_split == "upper_lower":
            base_cycle = 2
            if training_days_per_week == 4:
                cycle_days = 3
                training_pattern = "练二休一"
            else:
                cycle_days = 7
                training_pattern = f"每星期{training_days_per_week}天"

        elif training_split == "full_body":
            base_cycle = 1
            if training_days_per_week == 3:
                cycle_days = 2
                training_pattern = "练一休一"
            else:
                cycle_days = 7
                training_pattern = f"每星期{training_days_per_week}天"

        elif training_split == "bro_split":
            base_cycle = 5
            cycle_days = 7
            training_pattern = f"每星期{training_days_per_week}天"

        else:
            base_cycle = training_days_per_week
            cycle_days = 7
            training_pattern = f"每星期{training_days_per_week}天"

        cycles_per_week = 7.0 / cycle_days

        self.logger.info(
            f"📊 训练周期计算: {training_split}, "
            f"周期={cycle_days}天, "
            f"每星期{cycles_per_week:.1f}个周期, "
            f"模式={training_pattern}"
        )

        return {
            "cycle_days": cycle_days,
            "cycles_per_week": cycles_per_week,
            "training_pattern": training_pattern,
            "base_cycle": base_cycle
        }

    def _determine_applicable_standard(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """确定适用的训练标准（ACSM或NSCA）"""
        difficulty_level = input_data.get("difficulty_level", "intermediate")
        training_goal = input_data.get("training_goal", "general_fitness")

        if difficulty_level == "beginner":
            return {
                "standard_name": "ACSM FITT原则",
                "standard_full_name": "美国运动医学会（ACSM）FITT-VP原则",
                "standard_description": "ACSM FITT原则是针对一般健康人群的基础训练指南，强调频率、强度、时间、类型的科学配置",
                "application_reason": f"您的训练水平为初学者，ACSM FITT原则提供了安全、渐进的训练框架，适合建立运动基础和培养训练习惯",
                "key_principles": [
                    "Frequency（频率）：力量训练2-3天/周，确保充分恢复",
                    "Intensity（强度）：60-80% 1RM，适合肌肉适应和技术学习",
                    "Time（时间）：每个肌群2-4组，每组8-12次",
                    "Type（类型）：多样化动作选择，包含复合和孤立动作",
                    "Volume（容量）：渐进增加训练量，遵循10%原则",
                    "Progression（进阶）：每2-4周评估并调整训练参数"
                ],
                "reference": "ACSM's Guidelines for Exercise Testing and Prescription (11th Edition)",
                "适用场景": ["健身初学者", "一般健康人群", "康复训练者", "体重管理"]
            }

        elif difficulty_level == "intermediate":
            if training_goal in ["strength", "hypertrophy"]:
                return {
                    "standard_name": "NSCA周期化模型",
                    "standard_full_name": "美国国家体能协会（NSCA）周期化训练模型",
                    "standard_description": "NSCA周期化模型通过系统性地变化训练强度和容量，优化训练适应和防止平台期",
                    "application_reason": f"您的训练水平为中级，且目标为{training_goal}，NSCA周期化模型能够通过科学的训练周期安排，突破训练平台期，实现持续进步",
                    "key_principles": [
                        "线性周期化：肥大期(65-75% 1RM, 8-12次) → 力量期(85-95% 1RM, 2-6次)",
                        "波动周期化：每周变化训练强度和容量，防止适应性停滞",
                        "训练量管理：MEV（最小有效量）→ MAV（最大适应量）→ MRV（最大可恢复量）",
                        "减量周期：每4周安排1周减量期，促进超量恢复",
                        "渐进超负荷：系统性增加训练负荷，确保持续适应"
                    ],
                    "reference": "NSCA's Essentials of Strength Training and Conditioning (4th Edition)",
                    "适用场景": ["中高级训练者", "力量提升", "肌肥大训练", "运动表现"]
                }
            else:
                return {
                    "standard_name": "ACSM FITT原则",
                    "standard_full_name": "美国运动医学会（ACSM）FITT-VP原则",
                    "standard_description": "ACSM FITT原则是针对一般健康人群的基础训练指南，强调频率、强度、时间、类型的科学配置",
                    "application_reason": f"您的训练目标为{training_goal}，ACSM FITT原则提供了全面、平衡的训练框架，适合健康促进和体能提升",
                    "key_principles": [
                        "Frequency（频率）：力量训练2-3天/周，有氧训练3-5天/周",
                        "Intensity（强度）：力量60-80% 1RM，有氧50-70% HRmax",
                        "Time（时间）：力量训练每个肌群2-4组，有氧30-60分钟",
                        "Type（类型）：多样化运动选择，结合力量和有氧训练",
                        "Volume（容量）：根据个体恢复能力调整训练量",
                        "Progression（进阶）：渐进增加训练负荷，遵循10%原则"
                    ],
                    "reference": "ACSM's Guidelines for Exercise Testing and Prescription (11th Edition)",
                    "适用场景": ["健康促进", "体重管理", "一般体能提升", "耐力训练"]
                }

        elif difficulty_level in ["advanced", "elite"]:
            return {
                "standard_name": "NSCA高级周期化模型",
                "standard_full_name": "美国国家体能协会（NSCA）高级周期化训练模型",
                "standard_description": "NSCA高级周期化模型针对有经验的训练者，通过复杂的周期安排和专项训练，实现运动表现的最大化",
                "application_reason": f"您的训练水平为{difficulty_level}，NSCA高级周期化模型提供了精细的训练周期管理和专项能力发展策略，适合追求极致表现",
                "key_principles": [
                    "分块周期化：专注特定能力发展（力量块、爆发力块、耐力块）",
                    "波动周期化：日常、周、月多层次训练变化",
                    "高级训练量管理：精确控制MEV/MAV/MRV，优化训练刺激",
                    "专项训练整合：结合运动专项需求，定制训练方案",
                    "恢复策略：主动恢复、营养时机、睡眠优化",
                    "监控与调整：基于表现数据实时调整训练计划"
                ],
                "reference": "NSCA's Essentials of Strength Training and Conditioning (4th Edition), Periodization Training for Sports (Bompa & Haff)",
                "适用场景": ["高级训练者", "竞技运动员", "力量举/健美", "运动表现优化"]
            }

        else:
            return {
                "standard_name": "ACSM FITT原则",
                "standard_full_name": "美国运动医学会（ACSM）FITT-VP原则",
                "standard_description": "ACSM FITT原则是针对一般健康人群的基础训练指南",
                "application_reason": "基于您的情况，ACSM FITT原则提供了安全、有效的训练框架",
                "key_principles": [
                    "Frequency（频率）：力量训练2-3天/周",
                    "Intensity（强度）：60-80% 1RM",
                    "Time（时间）：每个肌群2-4组",
                    "Type（类型）：多样化动作选择"
                ],
                "reference": "ACSM's Guidelines for Exercise Testing and Prescription",
                "适用场景": ["一般健身人群"]
            }

    def _determine_target_muscle_groups(
        self,
        input_data: Dict[str, Any]
    ) -> List[str]:
        """确定目标肌群（基于训练分化）"""
        if input_data.get("target_muscle_groups"):
            return input_data["target_muscle_groups"]

        training_split = input_data["training_split"]

        if training_split == "full_body":
            return ["胸大肌", "背阔肌", "股四头肌", "腘绳肌", "三角肌", "肱二头肌", "肱三头肌"]
        elif training_split == "upper_lower":
            return ["胸大肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌", "股四头肌", "腘绳肌", "臀大肌"]
        elif training_split == "push_pull_legs":
            return ["胸大肌", "三角肌", "肱三头肌", "背阔肌", "肱二头肌", "股四头肌", "腘绳肌", "臀大肌"]
        elif training_split == "bro_split":
            return ["胸大肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌", "股四头肌", "腘绳肌"]
        else:
            return ["胸大肌", "背阔肌", "股四头肌", "腘绳肌", "三角肌"]

    async def _gather_muscle_group_data(
        self,
        input_data: Dict[str, Any],
        target_muscle_groups: List[str],
        tools_called: List[str],
        week_number: int = 1
    ) -> Dict[str, Dict[str, Any]]:
        """为每个肌群收集数据（调用工具）"""
        muscle_group_data = {}

        for muscle_group in target_muscle_groups:
            exercise_recommendations = await self._call_exercise_selector(
                input_data, muscle_group
            )
            tools_called.append("intelligent_exercise_selector")

            volume_data = await self._call_volume_calculator(
                input_data, muscle_group, week_number
            )
            tools_called.append("muscle_group_volume_calculator")

            muscle_group_data[muscle_group] = {
                "exercise_recommendations": exercise_recommendations,
                "volume_data": volume_data
            }

        return muscle_group_data

    async def _call_exercise_selector(
        self,
        input_data: Dict[str, Any],
        muscle_group: str
    ) -> Dict[str, Any]:
        """调用intelligent_exercise_selector工具"""
        if not self.tool_registry:
            self.logger.warning("工具注册表未设置，返回空推荐")
            return {"recommendations": [], "total_found": 0}

        try:
            selector_input = {
                "user_id": input_data["user_id"],
                "muscle_group": muscle_group,
                "training_goal": input_data["training_goal"],
                "difficulty_level": input_data["difficulty_level"],
                "available_equipment": input_data["available_equipment"],
                "injury_history": input_data.get("injury_history"),
                "session_focus": None
            }

            result = await self.tool_registry.call_tool(
                "intelligent_exercise_selector",
                selector_input
            )

            if result.get("success"):
                return result
            else:
                self.logger.error(f"动作选择失败: {result.get('error')}")

        except Exception as e:
            self.logger.error(f"调用intelligent_exercise_selector失败: {e}", exc_info=True)

        return {"recommendations": [], "total_found": 0}
