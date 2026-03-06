# -*- coding: utf-8 -*-
"""
三层检索引擎 - Layer 3 业务规则验证
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import LayerExecutionResult

logger = logging.getLogger(__name__)


class Layer3RulesMixin:
    """Layer 3: 业务规则验证 Mixin"""

    async def _execute_layer3_business_rules(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]],
        top_k: int,
        safety_check: bool,
        session_context: Optional[Dict[str, Any]] = None,
        recent_training: Optional[List[Dict[str, Any]]] = None,
        use_enhanced_rules: bool = True
    ) -> LayerExecutionResult:
        """
        Layer 3: 业务规则验证（增强版）

        基础规则:
        1. 用户档案匹配 (经验等级)
        2. 安全性检查 (禁忌症)
        3. 器械可用性
        4. 训练容量合理性

        增强规则 (Requirements 11.1-11.6, 18.1-18.6):
        5. kinetic_chain_rule（动力链规则）
        6. force_balance_rule（推拉平衡规则）
        7. joint_load_rule（关节负荷规则）
        8. recovery_time_rule（恢复时间规则）
        9. postural_correction_rule（体态矫正规则）
        10. body_type_constraint（体型约束）
        11. training_frequency_constraint（训练频率约束）
        12. session_duration_constraint（训练时长约束）
        13. goal_alignment_constraint（目标对齐约束）
        14. progressive_overload_constraint（渐进超负荷约束）
        15. nutrition_constraint（营养约束）
        """
        start_time = datetime.now()
        logger.info("→ Layer 3: 业务规则验证")

        try:
            user_profile = user_profile or {}
            session_context = session_context or {}
            recent_training = recent_training or []

            # ============ 基础规则过滤 ============
            validated_results = []

            for candidate in candidates:
                # 规则1: 经验等级匹配
                if not self._match_fitness_level(candidate, user_profile):
                    continue

                # 规则2: 安全性检查
                if safety_check:
                    if not await self._validate_safety(candidate, user_profile):
                        continue

                # 规则3: 器械可用性
                if not self._check_equipment_availability(candidate, user_profile):
                    continue

                # 规则4: 训练容量合理性
                volume_score = self._assess_training_volume(candidate, user_profile)

                # 添加规则评分
                candidate["rule_validation_score"] = volume_score
                candidate["validation_passed"] = True

                validated_results.append(candidate)

            # ============ 增强规则处理 ============
            enhanced_metadata = {}

            if use_enhanced_rules and validated_results:
                try:
                    from ..layer3_rule_engine import Layer3RuleEngine

                    # 初始化增强规则引擎
                    rule_engine = Layer3RuleEngine(neo4j_client=self.neo4j_manager, domain_adapter=self.domain_adapter)

                    # 应用增强规则
                    validated_results, execution_log = await rule_engine.apply_all_rules(
                        candidates=validated_results,
                        user_profile=user_profile,
                        query=query,
                        session_context=session_context,
                        recent_training=recent_training,
                        top_k=top_k * 2  # 给后续处理留余量
                    )

                    # 记录增强规则执行结果
                    enhanced_metadata = {
                        "enhanced_rules_applied": True,
                        "rules_count": len(execution_log.rules_applied),
                        "rules_details": [
                            {
                                "name": r.rule_name,
                                "applied": r.applied,
                                "before": r.candidates_before,
                                "after": r.candidates_after,
                                "time_ms": r.execution_time_ms
                            }
                            for r in execution_log.rules_applied
                        ]
                    }

                    logger.info(f"  → 增强规则完成: {len(execution_log.rules_applied)}条规则")

                except ImportError as e:
                    logger.warning(f"  ⚠️ 增强规则引擎未加载: {e}")
                    enhanced_metadata = {"enhanced_rules_applied": False, "reason": str(e)}
                except Exception as e:
                    logger.error(f"  ⚠️ 增强规则执行失败: {e}")
                    enhanced_metadata = {"enhanced_rules_applied": False, "error": str(e)}

            # 限制返回数量
            final_results = validated_results[:top_k]

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            confidence = 0.95 if final_results else 0.0

            self.stats["layer3_success"] += 1
            logger.info(f"  ✓ Layer 3完成: {len(final_results)}/{len(candidates)}个通过规则验证")

            return LayerExecutionResult(
                layer_name="Layer3-Rules",
                success=bool(final_results),
                results=final_results,
                execution_time_ms=execution_time,
                confidence=confidence,
                metadata={
                    "validated_count": len(final_results),
                    "total_candidates": len(candidates),
                    "pass_rate": len(final_results) / len(candidates) if candidates else 0,
                    **enhanced_metadata
                }
            )

        except Exception as e:
            logger.error(f"  ✗ Layer 3失败: {e}")
            return self._empty_layer_result("Layer3-Rules", error=str(e))

    def _match_fitness_level(
        self,
        exercise: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> bool:
        """匹配健身经验等级"""
        if not user_profile:
            return True

        user_level = user_profile.get("fitness_level", "intermediate").lower()
        exercise_difficulty = (exercise.get("difficulty_zh") or exercise.get("difficulty_en") or "intermediate").lower()

        # 等级映射（支持中英文）
        level_hierarchy = {
            "beginner": ["beginner", "easy", "novice", "新手", "初级", "简单"],
            "intermediate": ["beginner", "intermediate", "moderate", "novice", "新手", "中级", "中等", "初级"],
            "advanced": ["intermediate", "advanced", "hard", "elite", "中级", "高级", "困难", "精英"]
        }

        allowed_difficulties = level_hierarchy.get(user_level, ["intermediate", "中级"])
        return any(diff in exercise_difficulty for diff in allowed_difficulties)

    async def _validate_safety(
        self,
        exercise: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> bool:
        """
        增强版安全性验证 (Requirements 4.3, 4.6)

        检查项目：
        1. Neo4j禁忌症查询（优先，基于CONTRAINDICATED_FOR关系）
        1b. Payload禁忌症匹配（Neo4j不可用时的降级方案）
        2. 年龄限制
        3. 健康状况检查（慢性病、损伤史）
        4. 关节损伤检查
        5. 体态问题检查

        框架层领域无关（Requirements 6.1, 6.2）：
        - 安全规则数据从领域适配器获取
        - 如果没有适配器，跳过领域特定检查
        """
        if not user_profile:
            return True

        exercise_name = exercise.get("exercise_name_zh", "") or exercise.get("name", "Unknown")

        # 获取健康档案
        health_profile = user_profile.get("health_status", {})
        user_conditions = user_profile.get("medical_conditions", [])

        # 整合所有健康状况
        all_conditions = set(user_conditions)

        # 添加慢性病
        chronic_conditions = health_profile.get("chronic_conditions", [])
        for condition in chronic_conditions:
            if isinstance(condition, dict):
                all_conditions.add(condition.get("name", ""))
            else:
                all_conditions.add(str(condition))

        # 添加当前症状
        current_symptoms = health_profile.get("current_symptoms", [])
        for symptom in current_symptoms:
            all_conditions.add(str(symptom))

        # ============ 1. Neo4j禁忌症查询（优先）============
        neo4j_checked = False
        if self.neo4j_available and self.neo4j_manager and exercise_name and all_conditions:
            try:
                neo4j_contras = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._query_neo4j_contraindications_sync,
                        exercise_name,
                        list(all_conditions)
                    ),
                    timeout=5.0
                )
                if neo4j_contras:
                    neo4j_checked = True
                    for contra in neo4j_contras:
                        severity = (contra.get("severity") or "relative").lower()
                        if severity == "absolute":
                            logger.debug(
                                f"安全过滤(Neo4j): {exercise_name} - 绝对禁忌 "
                                f"{contra.get('injury_name_zh')} (severity_score={contra.get('severity_score')})"
                            )
                            return False
                        elif severity == "relative":
                            difficulty = (exercise.get("difficulty_zh") or exercise.get("difficulty_en") or "").lower()
                            if "advanced" in difficulty or "高级" in difficulty or "elite" in difficulty:
                                logger.debug(
                                    f"安全过滤(Neo4j): {exercise_name} - 相对禁忌+高难度 "
                                    f"{contra.get('injury_name_zh')}"
                                )
                                return False
                        elif severity == "caution":
                            logger.debug(
                                f"安全提示(Neo4j): {exercise_name} - 谨慎使用 "
                                f"{contra.get('injury_name_zh')}"
                            )
            except asyncio.TimeoutError:
                logger.warning(f"Neo4j禁忌症查询超时(5s): {exercise_name}")
            except Exception as e:
                logger.warning(f"Neo4j禁忌症异步查询失败: {e}")

        # ============ 1b. Fallback: Payload禁忌症匹配 ============
        if not neo4j_checked:
            contraindications = exercise.get("contraindications", [])
            for condition in all_conditions:
                if not condition:
                    continue
                if condition in contraindications:
                    logger.debug(f"安全过滤(payload): {exercise_name} - 禁忌症 {condition}")
                    return False
                for contra in contraindications:
                    if isinstance(contra, str) and (condition in contra or contra in condition):
                        logger.debug(f"安全过滤(payload): {exercise_name} - 禁忌症匹配 {condition} ~ {contra}")
                        return False

        # ============ 2. 年龄限制检查 ============
        basic_info = user_profile.get("basic_info", {})
        user_age = basic_info.get("age") or user_profile.get("age", 30)

        difficulty = (exercise.get("difficulty_zh") or exercise.get("difficulty_en") or exercise.get("difficulty") or "").lower()

        # 高龄用户限制
        if user_age > 60:
            if "advanced" in difficulty or "elite" in difficulty or "高级" in difficulty or "精英" in difficulty:
                logger.debug(f"安全过滤: {exercise_name} - 高龄(>{user_age})不适合高难度")
                return False

        # 青少年用户限制（<16岁）
        if user_age < 16:
            high_load_keywords = []
            if self.domain_adapter and hasattr(self.domain_adapter, 'get_high_load_keywords'):
                high_load_keywords = self.domain_adapter.get_high_load_keywords()

            if high_load_keywords and any(kw in exercise_name.lower() for kw in high_load_keywords):
                if "advanced" in difficulty or "高级" in difficulty:
                    logger.debug(f"安全过滤: {exercise_name} - 青少年(<16)不适合高负荷项目")
                    return False

        # ============ 3. 关节损伤检查 ============
        injuries = health_profile.get("injuries", [])
        injury_history = health_profile.get("injury_history", [])

        injured_parts = set()
        for injury in injuries + injury_history:
            if isinstance(injury, dict):
                body_part = injury.get("body_part", "")
                injury_type = injury.get("type", "")
                if body_part:
                    injured_parts.add(body_part.lower())
                if injury_type:
                    injured_parts.add(injury_type.lower())
            elif isinstance(injury, str):
                injured_parts.add(injury.lower())

        if injured_parts:
            target_muscle = (exercise.get("primary_muscle_zh") or exercise.get("target_muscle") or "").lower()
            involved_joints = exercise.get("involved_joints", [])

            joint_keywords = {}
            if self.domain_adapter:
                joint_keywords = self.domain_adapter.get_joint_keywords()

            for injured_part in injured_parts:
                for joint_name, keywords in joint_keywords.items():
                    if any(kw in injured_part for kw in keywords):
                        exercise_text = f"{exercise_name} {target_muscle} {' '.join(involved_joints)}".lower()
                        if any(kw in exercise_text for kw in keywords):
                            logger.debug(f"安全过滤: {exercise_name} - 涉及受伤部位 {injured_part}")
                            return False

        # ============ 4. 体态问题检查 ============
        postural_issues = health_profile.get("postural_issues", [])

        postural_contraindications = {}
        if self.domain_adapter:
            postural_contraindications = self.domain_adapter.get_safety_contraindications()

        for issue in postural_issues:
            issue_name = issue if isinstance(issue, str) else issue.get("name", "")
            if issue_name in postural_contraindications:
                contra_items = postural_contraindications[issue_name]
                if any(contra in exercise_name for contra in contra_items):
                    if "advanced" in difficulty or "高级" in difficulty:
                        logger.debug(f"安全过滤: {exercise_name} - 体态问题 {issue_name} 不适合高难度")
                        return False

        # ============ 5. 特殊健康状况检查（通用）============
        cardiovascular_conditions = ["高血压", "心脏病", "心律不齐", "冠心病", "hypertension", "heart disease"]
        has_cardiovascular = any(
            any(cv in str(cond).lower() for cv in cardiovascular_conditions)
            for cond in all_conditions
        )

        if has_cardiovascular:
            high_intensity_keywords = ["爆发", "冲刺", "跳跃", "波比跳", "burpee", "sprint", "plyometric"]
            if any(kw in exercise_name.lower() for kw in high_intensity_keywords):
                logger.debug(f"安全过滤: {exercise_name} - 心血管疾病不适合高强度项目")
                return False

        osteoporosis_conditions = ["骨质疏松", "osteoporosis"]
        has_osteoporosis = any(
            any(op in str(cond).lower() for op in osteoporosis_conditions)
            for cond in all_conditions
        )

        if has_osteoporosis:
            high_impact_keywords = ["跳跃", "跑步", "跳绳", "波比跳", "jump", "running", "plyometric"]
            if any(kw in exercise_name.lower() for kw in high_impact_keywords):
                logger.debug(f"安全过滤: {exercise_name} - 骨质疏松不适合高冲击项目")
                return False

        return True

    def _check_equipment_availability(
        self,
        exercise: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> bool:
        """检查器械可用性"""
        if not user_profile:
            return True

        available_equipment = user_profile.get("available_equipment", [])
        if not available_equipment:
            return True

        required_equipment = exercise.get("equipment", "")
        if not required_equipment:
            return True

        if isinstance(required_equipment, str):
            required_equipment_list = [required_equipment]
        elif isinstance(required_equipment, list):
            required_equipment_list = required_equipment
        else:
            return True

        if "全部" in available_equipment:
            return True

        for req_equip in required_equipment_list:
            if req_equip in available_equipment:
                return True

        logger.debug(f"器械过滤: {exercise.get('exercise_name_zh')} - 需要 {required_equipment_list}，可用 {available_equipment}")
        return False

    def _assess_training_volume(
        self,
        exercise: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> float:
        """评估训练容量合理性"""
        volume_data = exercise.get("training_volume", {})
        if not volume_data:
            return 0.8

        mev = volume_data.get("mev", 0)
        mav = volume_data.get("mav", 0)
        mrv = volume_data.get("mrv", 0)

        if mev and mav and mrv:
            return 1.0
        elif mev or mav:
            return 0.9
        else:
            return 0.7
