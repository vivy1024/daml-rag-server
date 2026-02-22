# -*- coding: utf-8 -*-
"""
专业程序设计器 — 周计划生成 Mixin

包含：
- _generate_weekly_program: 生成周训练计划
- _create_full_body_day / _create_upper_body_day / _create_lower_body_day
- _create_push_day / _create_pull_day / _create_legs_day
- _create_single_muscle_day / _create_muscle_group_day
- _estimate_duration: 估算训练时长
- _generate_warmup_exercises / _generate_cooldown_exercises
"""

from typing import Dict, Any, List
import logging

from ....services.warmup_cooldown_exercises import (
    WarmupCooldownSelector,
    TrainingFocus,
)

logger = logging.getLogger(__name__)


class ProgramGeneratorMixin:
    """周计划生成 + 训练日创建 + 热身/放松"""

    def _generate_weekly_program(
        self,
        input_data: Dict[str, Any],
        muscle_group_data: Dict[str, Dict[str, Any]],
        cycle_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成周训练计划"""
        training_split = input_data["training_split"]
        training_days_per_week = input_data["training_days_per_week"]
        training_weeks = input_data.get("training_weeks", 4)

        self.logger.info(
            f"📅 生成{training_weeks}周训练计划: "
            f"{training_split}, "
            f"周期={cycle_info['cycle_days']}天, "
            f"模式={cycle_info['training_pattern']}"
        )

        training_days = []

        if training_split == "full_body":
            for day_num in range(1, training_days_per_week + 1):
                training_day = self._create_full_body_day(
                    day_num, muscle_group_data, input_data
                )
                training_days.append(training_day)

        elif training_split == "upper_lower":
            for day_num in range(1, training_days_per_week + 1):
                if day_num % 2 == 1:
                    training_day = self._create_upper_body_day(
                        day_num, muscle_group_data, input_data
                    )
                else:
                    training_day = self._create_lower_body_day(
                        day_num, muscle_group_data, input_data
                    )
                training_days.append(training_day)

        elif training_split == "push_pull_legs":
            split_pattern = ["push", "pull", "legs"]
            for day_num in range(1, training_days_per_week + 1):
                pattern_index = (day_num - 1) % 3
                pattern = split_pattern[pattern_index]

                if pattern == "push":
                    training_day = self._create_push_day(
                        day_num, muscle_group_data, input_data
                    )
                elif pattern == "pull":
                    training_day = self._create_pull_day(
                        day_num, muscle_group_data, input_data
                    )
                else:
                    training_day = self._create_legs_day(
                        day_num, muscle_group_data, input_data
                    )
                training_days.append(training_day)

        elif training_split == "bro_split":
            muscle_groups = list(muscle_group_data.keys())
            for day_num in range(1, training_days_per_week + 1):
                muscle_index = (day_num - 1) % len(muscle_groups)
                focus_muscle = muscle_groups[muscle_index]
                training_day = self._create_single_muscle_day(
                    day_num, focus_muscle, muscle_group_data, input_data
                )
                training_days.append(training_day)

        # 检测并应用减量日
        deload_day_numbers = self._detect_deload_days(training_days)

        if deload_day_numbers:
            self.logger.info(
                f"🔄 检测到{len(deload_day_numbers)}个减量日: {deload_day_numbers}"
            )
            for i, day in enumerate(training_days):
                if day["day_number"] in deload_day_numbers:
                    training_days[i] = self._apply_deload_to_day(day)

        rest_days = [i for i in range(1, 8) if i not in [d["day_number"] for d in training_days]]
        total_weekly_sets = sum(day["total_sets"] for day in training_days)

        muscle_group_distribution = {}
        for muscle_group in muscle_group_data.keys():
            muscle_sets = sum(
                sum(1 for ex in day["exercises"] if muscle_group in ex.get("primary_muscles", []))
                for day in training_days
            )
            muscle_group_distribution[muscle_group] = muscle_sets

        deload_days_count = len(deload_day_numbers)

        return {
            "week_number": 1,
            "training_days": training_days,
            "rest_days": rest_days,
            "total_weekly_sets": total_weekly_sets,
            "muscle_group_distribution": muscle_group_distribution,
            "cycle_days": cycle_info["cycle_days"],
            "cycles_per_week": cycle_info["cycles_per_week"],
            "training_pattern": cycle_info["training_pattern"],
            "has_deload_days": deload_days_count > 0,
            "deload_days_count": deload_days_count,
            "deload_day_numbers": deload_day_numbers
        }

    def _create_full_body_day(
        self,
        day_number: int,
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建全身训练日"""
        exercises = []
        total_sets = 0

        for muscle_group, data in muscle_group_data.items():
            recommendations = data["exercise_recommendations"].get("recommendations", [])
            volume_data = data["volume_data"]
            selected_exercises = recommendations[:2]

            for ex in selected_exercises:
                volume_rec = volume_data.get("volume_recommendation", {})
                sets = min(3, volume_rec.get("sets_per_session", 3))

                exercise_in_program = {
                    "exercise_id": ex.get("exercise_id", ""),
                    "name_zh": ex.get("name_zh", ""),
                    "name_en": ex.get("name_en", ""),
                    "category": ex.get("category", ""),
                    "difficulty": ex.get("difficulty_zh") or ex.get("difficulty_en") or "",
                    "sets": sets,
                    "reps_range": volume_rec.get("reps_per_set_range", (8, 12)),
                    "rest_seconds": volume_rec.get("rest_period_seconds", 90),
                    "primary_muscles": ex.get("muscles_primary_zh") or ex.get("primary_muscles") or [],
                    "secondary_muscles": ex.get("muscles_secondary_zh") or ex.get("secondary_muscles") or [],
                    "safety_level": ex.get("safety_level", ""),
                    "safety_notes": ex.get("contraindications_zh", []),
                    "reasoning": ex.get("reasoning", "")
                }
                exercises.append(exercise_in_program)
                total_sets += sets

        target_muscles = list(muscle_group_data.keys())
        include_warmup = input_data.get("include_warmup", True)
        warmup_exercises = self._generate_warmup_exercises(
            target_muscles=target_muscles,
            training_split="full_body",
            include_warmup=include_warmup,
            warmup_duration=10
        )

        include_cooldown = input_data.get("include_cooldown", True)
        cooldown_exercises = self._generate_cooldown_exercises(
            target_muscles=target_muscles,
            training_split="full_body",
            include_cooldown=include_cooldown,
            cooldown_duration=10
        )

        return {
            "day_number": day_number,
            "day_name": f"全身训练日 {day_number}",
            "focus_muscle_groups": target_muscles,
            "warmup_exercises": warmup_exercises,
            "exercises": exercises,
            "cooldown_exercises": cooldown_exercises,
            "total_sets": total_sets,
            "estimated_duration_minutes": self._estimate_duration(exercises),
            "notes": ["全身训练，注意动作质量", "充分热身和拉伸"],
            "warmup_duration_minutes": 10 if include_warmup else 0,
            "cooldown_duration_minutes": 10 if include_cooldown else 0,
        }

    def _create_upper_body_day(self, day_number, muscle_group_data, input_data):
        """创建上肢训练日"""
        upper_body_muscles = ["胸大肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌"]
        return self._create_muscle_group_day(
            day_number, f"上肢训练日 {day_number}",
            upper_body_muscles, muscle_group_data, input_data
        )

    def _create_lower_body_day(self, day_number, muscle_group_data, input_data):
        """创建下肢训练日"""
        lower_body_muscles = ["股四头肌", "腘绳肌", "臀大肌", "小腿肌群"]
        return self._create_muscle_group_day(
            day_number, f"下肢训练日 {day_number}",
            lower_body_muscles, muscle_group_data, input_data
        )

    def _create_push_day(self, day_number, muscle_group_data, input_data):
        """创建推日"""
        push_muscles = ["胸大肌", "三角肌", "肱三头肌"]
        return self._create_muscle_group_day(
            day_number, f"推日 {day_number}",
            push_muscles, muscle_group_data, input_data
        )

    def _create_pull_day(self, day_number, muscle_group_data, input_data):
        """创建拉日"""
        pull_muscles = ["背阔肌", "肱二头肌"]
        return self._create_muscle_group_day(
            day_number, f"拉日 {day_number}",
            pull_muscles, muscle_group_data, input_data
        )

    def _create_legs_day(self, day_number, muscle_group_data, input_data):
        """创建腿日"""
        leg_muscles = ["股四头肌", "腘绳肌", "臀大肌"]
        return self._create_muscle_group_day(
            day_number, f"腿日 {day_number}",
            leg_muscles, muscle_group_data, input_data
        )

    def _create_single_muscle_day(self, day_number, focus_muscle, muscle_group_data, input_data):
        """创建单肌群训练日"""
        return self._create_muscle_group_day(
            day_number, f"{focus_muscle}训练日",
            [focus_muscle], muscle_group_data, input_data
        )

    def _create_muscle_group_day(
        self,
        day_number: int,
        day_name: str,
        target_muscles: List[str],
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建肌群训练日（通用方法）"""
        exercises = []
        total_sets = 0

        for muscle_group in target_muscles:
            if muscle_group not in muscle_group_data:
                continue

            data = muscle_group_data[muscle_group]
            recommendations = data["exercise_recommendations"].get("recommendations", [])
            volume_data = data["volume_data"]
            selected_exercises = recommendations[:3]

            for ex in selected_exercises:
                volume_rec = volume_data.get("volume_recommendation", {})
                sets = volume_rec.get("sets_per_session", 4)

                exercise_in_program = {
                    "exercise_id": ex.get("exercise_id", ""),
                    "name_zh": ex.get("name_zh", ""),
                    "name_en": ex.get("name_en", ""),
                    "category": ex.get("category", ""),
                    "difficulty": ex.get("difficulty_zh") or ex.get("difficulty_en") or "",
                    "sets": sets,
                    "reps_range": volume_rec.get("reps_per_set_range", (8, 12)),
                    "rest_seconds": volume_rec.get("rest_period_seconds", 90),
                    "primary_muscles": ex.get("muscles_primary_zh") or ex.get("primary_muscles") or [],
                    "secondary_muscles": ex.get("muscles_secondary_zh") or ex.get("secondary_muscles") or [],
                    "safety_level": ex.get("safety_level", ""),
                    "safety_notes": ex.get("contraindications_zh", []),
                    "reasoning": ex.get("reasoning", "")
                }
                exercises.append(exercise_in_program)
                total_sets += sets

        include_warmup = input_data.get("include_warmup", True)
        warmup_exercises = self._generate_warmup_exercises(
            target_muscles=target_muscles,
            training_split=input_data.get("training_split", "full_body"),
            include_warmup=include_warmup,
            warmup_duration=10
        )

        include_cooldown = input_data.get("include_cooldown", True)
        cooldown_exercises = self._generate_cooldown_exercises(
            target_muscles=target_muscles,
            training_split=input_data.get("training_split", "full_body"),
            include_cooldown=include_cooldown,
            cooldown_duration=10
        )

        return {
            "day_number": day_number,
            "day_name": day_name,
            "focus_muscle_groups": target_muscles,
            "warmup_exercises": warmup_exercises,
            "exercises": exercises,
            "cooldown_exercises": cooldown_exercises,
            "total_sets": total_sets,
            "estimated_duration_minutes": self._estimate_duration(exercises),
            "notes": [f"专注于{', '.join(target_muscles)}训练", "注意动作质量和肌肉感受"],
            "warmup_duration_minutes": 10 if include_warmup else 0,
            "cooldown_duration_minutes": 10 if include_cooldown else 0,
        }

    def _estimate_duration(self, exercises: List[Dict[str, Any]]) -> int:
        """估算训练时长（分钟）"""
        total_minutes = 10  # 热身时间

        for ex in exercises:
            sets = ex.get("sets", 3)
            rest_seconds = ex.get("rest_seconds", 90)
            exercise_time = sets * (30 + rest_seconds) / 60
            total_minutes += exercise_time

        total_minutes += 10  # 放松时间
        return int(total_minutes)

    def _generate_warmup_exercises(
        self,
        target_muscles: List[str],
        training_split: str,
        include_warmup: bool = True,
        warmup_duration: int = 10
    ) -> List[Dict[str, Any]]:
        """生成热身动作列表"""
        if not include_warmup:
            return []

        training_focus = WarmupCooldownSelector.determine_training_focus(
            target_muscles, training_split
        )
        warmup_exercises = WarmupCooldownSelector.get_warmup_exercises(
            training_focus=training_focus,
            duration_minutes=warmup_duration,
            include_cardio=True
        )

        self.logger.info(
            f"🔥 生成热身动作: 训练重点={training_focus.value}, "
            f"动作数={len(warmup_exercises)}, 时长={warmup_duration}分钟"
        )
        return warmup_exercises

    def _generate_cooldown_exercises(
        self,
        target_muscles: List[str],
        training_split: str,
        include_cooldown: bool = True,
        cooldown_duration: int = 10
    ) -> List[Dict[str, Any]]:
        """生成放松动作列表"""
        if not include_cooldown:
            return []

        training_focus = WarmupCooldownSelector.determine_training_focus(
            target_muscles, training_split
        )
        cooldown_exercises = WarmupCooldownSelector.get_cooldown_exercises(
            training_focus=training_focus,
            duration_minutes=cooldown_duration
        )

        self.logger.info(
            f"🧘 生成放松动作: 训练重点={training_focus.value}, "
            f"动作数={len(cooldown_exercises)}, 时长={cooldown_duration}分钟"
        )
        return cooldown_exercises
