# -*- coding: utf-8 -*-
"""
Layer3 业务规则引擎 - 增强版

基于设计文档Requirements 11.1-11.6, 18.1-18.6实现的专业规则引擎。

规则分类:
1. 运动学规则 (kinetic_chain_rule, force_balance_rule)
2. 安全规则 (joint_load_rule, postural_correction_rule)
3. 恢复规则 (recovery_time_rule)
4. 领域专业约束 (goal_alignment, progressive_overload, nutrition)

版本: v1.0.0
日期: 2026-01-06
作者: 薛小川
"""

import asyncio
import logging
from collections import deque
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


# ============ 枚举定义 ============

class ForceType(Enum):
    """力的方向类型"""
    PUSH = "push"
    PULL = "pull"
    HOLD = "hold"
    UNKNOWN = "unknown"


class KineticChainType(Enum):
    """动力链类型"""
    OPEN = "open_chain"
    CLOSED = "closed_chain"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class BodyType(Enum):
    """体型分类"""
    ECTOMORPH = "ectomorph"      # 外胚型（瘦长型）
    MESOMORPH = "mesomorph"      # 中胚型（肌肉型）
    ENDOMORPH = "endomorph"      # 内胚型（圆润型）
    UNKNOWN = "unknown"


from src.applications.fitness.types.enums import TrainingGoal


# ============ 数据类定义 ============

@dataclass
class RuleExecutionResult:
    """规则执行结果"""
    rule_name: str
    applied: bool
    candidates_before: int
    candidates_after: int
    execution_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    filtered_exercises: List[str] = field(default_factory=list)
    boosted_exercises: List[str] = field(default_factory=list)


@dataclass
class Layer3ExecutionLog:
    """Layer3执行日志"""
    user_id: Optional[str]
    query: str
    rules_applied: List[RuleExecutionResult]
    total_candidates: int
    filtered_candidates: int
    execution_time_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============ 肌肉恢复时间配置 ============
# 注意：此处保留空配置作为默认值
# 实际数据应通过domain_adapter.get_muscle_recovery_hours()获取
# 框架层领域无关 - Requirements 6.1, 6.2

MUSCLE_RECOVERY_HOURS = {
    # 默认值（当domain_adapter未配置时使用）
    "default": 48
}


# ============ 体态问题与肌肉关联 ============
# 注意：此处保留空配置作为默认值
# 实际数据应通过domain_adapter.get_postural_issue_config()获取
# 框架层领域无关 - Requirements 6.1, 6.2

POSTURAL_ISSUE_MUSCLES = {
    # 默认空配置（当domain_adapter未配置时使用）
}


# ============ 训练目标与动作特征匹配 ============
# 注意：此处保留空配置作为默认值
# 实际数据应通过domain_adapter.get_goal_preferences()获取
# 框架层领域无关 - Requirements 6.1, 6.2

GOAL_EXERCISE_PREFERENCES = {
    # 默认空配置（当domain_adapter未配置时使用）
}




# ============ Layer3规则引擎类 ============

class Layer3RuleEngine:
    """
    Layer3 业务规则引擎 - 增强版
    
    实现Requirements:
    - 11.1: kinetic_chain_rule（动力链规则）
    - 11.2: force_balance_rule（推拉平衡规则）
    - 11.3: joint_load_rule（关节负荷规则）
    - 11.4: recovery_time_rule（恢复时间规则）
    - 11.5: relevancy_score（相关性评分）
    - 11.6: 规则执行日志
    - 18.1: body_type_constraint（体型约束）
    - 18.2: training_frequency_constraint（训练频率约束）
    - 18.3: session_duration_constraint（训练时长约束）
    - 18.4: goal_alignment_constraint（目标对齐约束）
    - 18.5: progressive_overload_constraint（渐进超负荷约束）
    - 18.6: nutrition_constraint（营养约束）
    
    框架层领域无关 - Requirements 6.1, 6.2:
    - 所有领域特定数据通过domain_adapter获取
    - 框架层不包含硬编码的健身数据
    """
    
    # 规则列表（按执行顺序）
    RULES = [
        # 安全规则（优先级最高）
        "joint_load_rule",
        "postural_correction_rule",
        
        # 运动学规则
        "kinetic_chain_rule",
        "force_balance_rule",
        
        # 恢复规则
        "recovery_time_rule",
        
        # 领域专业约束
        "body_type_constraint",
        "training_frequency_constraint",
        "session_duration_constraint",
        "goal_alignment_constraint",
        "progressive_overload_constraint",
        "nutrition_constraint",
    ]
    
    def __init__(self, neo4j_client=None, domain_adapter=None):
        """
        初始化Layer3规则引擎
        
        Args:
            neo4j_client: Neo4j客户端（可选，用于查询关系数据）
            domain_adapter: 领域适配器（用于获取领域特定配置）
        """
        self.neo4j_client = neo4j_client
        self.domain_adapter = domain_adapter
        self.execution_logs: deque = deque(maxlen=1000)
        
        # 从domain_adapter加载领域特定配置
        self._load_domain_config()
        
        logger.info("Layer3RuleEngine initialized with %d rules", len(self.RULES))
    
    def _load_domain_config(self):
        """从domain_adapter加载领域特定配置"""
        if self.domain_adapter:
            # 加载肌肉恢复时间配置
            if hasattr(self.domain_adapter, 'get_muscle_recovery_hours'):
                self._muscle_recovery_hours = self.domain_adapter.get_muscle_recovery_hours()
            else:
                self._muscle_recovery_hours = MUSCLE_RECOVERY_HOURS
            
            # 加载体态问题配置
            if hasattr(self.domain_adapter, 'get_postural_issue_config'):
                self._postural_issue_config = self.domain_adapter.get_postural_issue_config()
            else:
                self._postural_issue_config = POSTURAL_ISSUE_MUSCLES
            
            # 加载目标偏好配置
            if hasattr(self.domain_adapter, 'get_goal_preferences'):
                self._goal_preferences = self.domain_adapter.get_goal_preferences()
            else:
                self._goal_preferences = GOAL_EXERCISE_PREFERENCES
            
            # 加载体型偏好配置
            if hasattr(self.domain_adapter, 'get_body_type_preferences'):
                self._body_type_preferences = self.domain_adapter.get_body_type_preferences()
            else:
                self._body_type_preferences = {}
            
            # 加载关节关键词配置
            if hasattr(self.domain_adapter, 'get_joint_keywords'):
                self._joint_keywords = self.domain_adapter.get_joint_keywords()
            else:
                self._joint_keywords = {}
            
            logger.info(f"从domain_adapter加载领域配置: "
                       f"recovery_hours={len(self._muscle_recovery_hours)}, "
                       f"postural_issues={len(self._postural_issue_config)}, "
                       f"goal_prefs={len(self._goal_preferences)}")
        else:
            # 使用默认空配置
            self._muscle_recovery_hours = MUSCLE_RECOVERY_HOURS
            self._postural_issue_config = POSTURAL_ISSUE_MUSCLES
            self._goal_preferences = GOAL_EXERCISE_PREFERENCES
            self._body_type_preferences = {}
            self._joint_keywords = {}
            logger.warning("未配置domain_adapter，使用默认空配置")

    def _query_neo4j_postural_relations_sync(
        self,
        exercise_name: str,
        postural_issues: list
    ) -> dict:
        """
        同步查询Neo4j中动作与体态问题的CORRECTS/AGGRAVATES关系

        此方法为同步方法，需要通过asyncio.to_thread()在async上下文中调用。

        Args:
            exercise_name: 动作中文名称
            postural_issues: 用户体态问题列表（如["骨盆前倾", "圆肩"]）

        Returns:
            dict: {
                "corrects": bool, "aggravates": bool,
                "corrects_details": [...], "aggravates_details": [...]
            }
        """
        empty_result = {
            "corrects": False, "aggravates": False,
            "corrects_details": [], "aggravates_details": []
        }

        if not self.neo4j_client or not hasattr(self.neo4j_client, 'get_session'):
            return empty_result

        try:
            # 标准化体态问题名称
            issue_names = []
            for issue in postural_issues:
                if isinstance(issue, str):
                    issue_names.append(issue)
                elif isinstance(issue, dict):
                    issue_names.append(issue.get("name", ""))
            issue_names = [n for n in issue_names if n]

            if not issue_names or not exercise_name:
                return empty_result

            # 查询CORRECTS关系
            corrects_query = """
            MATCH (e:Exercise)-[r:CORRECTS]->(p:PosturalIssue)
            WHERE (e.name_zh CONTAINS $exercise_name OR e.name CONTAINS $exercise_name)
              AND (p.name_zh IN $issue_names OR p.name IN $issue_names)
            RETURN p.name_zh AS issue_name, p.name AS issue_name_en,
                   r.reason AS reason, e.name_zh AS exercise_name_zh
            """

            # 查询AGGRAVATES关系
            aggravates_query = """
            MATCH (e:Exercise)-[r:AGGRAVATES]->(p:PosturalIssue)
            WHERE (e.name_zh CONTAINS $exercise_name OR e.name CONTAINS $exercise_name)
              AND (p.name_zh IN $issue_names OR p.name IN $issue_names)
            RETURN p.name_zh AS issue_name, p.name AS issue_name_en,
                   r.reason AS reason, e.name_zh AS exercise_name_zh
            """

            params = {"exercise_name": exercise_name, "issue_names": issue_names}

            with self.neo4j_client.get_session() as session:
                corrects_result = session.run(corrects_query, params)
                corrects_records = [record.data() for record in corrects_result]

                aggravates_result = session.run(aggravates_query, params)
                aggravates_records = [record.data() for record in aggravates_result]

            return {
                "corrects": bool(corrects_records),
                "aggravates": bool(aggravates_records),
                "corrects_details": corrects_records,
                "aggravates_details": aggravates_records
            }

        except Exception as e:
            logger.warning(f"Neo4j体态关系查询失败（降级到关键词匹配）: {e}")
            return empty_result

    async def apply_all_rules(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None,
        query: str = "",
        session_context: Optional[Dict[str, Any]] = None,
        recent_training: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        enabled_rules: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], Layer3ExecutionLog]:
        """
        应用所有Layer3规则
        
        Args:
            candidates: 候选动作列表
            user_profile: 用户档案
            query: 用户查询
            session_context: 会话上下文（包含已选动作的推拉统计等）
            recent_training: 最近训练记录
            top_k: 返回结果数
            enabled_rules: 启用的规则列表（None表示全部启用）
            
        Returns:
            Tuple[List[Dict], Layer3ExecutionLog]: 过滤后的候选列表和执行日志
        """
        start_time = datetime.now()
        user_profile = user_profile or {}
        session_context = session_context or {}
        recent_training = recent_training or []
        
        rules_to_apply = enabled_rules or self.RULES
        rule_results: List[RuleExecutionResult] = []
        
        current_candidates = candidates.copy()
        
        logger.info(f"Layer3规则引擎开始: {len(candidates)}个候选, {len(rules_to_apply)}条规则")
        
        for rule_name in rules_to_apply:
            if not hasattr(self, f"_apply_{rule_name}"):
                logger.warning(f"规则 {rule_name} 未实现，跳过")
                continue
            
            rule_start = datetime.now()
            candidates_before = len(current_candidates)
            
            try:
                rule_method = getattr(self, f"_apply_{rule_name}")
                current_candidates, details = await rule_method(
                    candidates=current_candidates,
                    user_profile=user_profile,
                    query=query,
                    session_context=session_context,
                    recent_training=recent_training
                )
                
                rule_time = (datetime.now() - rule_start).total_seconds() * 1000
                
                rule_result = RuleExecutionResult(
                    rule_name=rule_name,
                    applied=True,
                    candidates_before=candidates_before,
                    candidates_after=len(current_candidates),
                    execution_time_ms=rule_time,
                    details=details
                )
                rule_results.append(rule_result)
                
                logger.debug(
                    f"  → {rule_name}: {candidates_before} → {len(current_candidates)} "
                    f"({rule_time:.1f}ms)"
                )
                
            except Exception as e:
                logger.error(f"规则 {rule_name} 执行失败: {e}")
                rule_results.append(RuleExecutionResult(
                    rule_name=rule_name,
                    applied=False,
                    candidates_before=candidates_before,
                    candidates_after=candidates_before,
                    execution_time_ms=0,
                    details={"error": str(e)}
                ))
        
        # 限制返回数量
        final_candidates = current_candidates[:top_k]
        
        # 构建执行日志
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        execution_log = Layer3ExecutionLog(
            user_id=user_profile.get("user_id"),
            query=query,
            rules_applied=rule_results,
            total_candidates=len(candidates),
            filtered_candidates=len(final_candidates),
            execution_time_ms=total_time
        )
        
        self.execution_logs.append(execution_log)
        
        logger.info(
            f"Layer3规则引擎完成: {len(candidates)} → {len(final_candidates)} "
            f"({total_time:.1f}ms)"
        )
        
        return final_candidates, execution_log
    
    # ============ 运动学规则 ============
    
    async def _apply_kinetic_chain_rule(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        动力链规则 - 康复场景优先闭链动作
        
        Requirements: 11.1
        
        规则逻辑:
        - 康复阶段用户优先推荐闭链动作（closed_chain）
        - 闭链动作更安全，关节负荷更可控
        """
        health_profile = user_profile.get("health_status", {})
        rehabilitation_phase = health_profile.get("rehabilitation_phase")
        injuries = health_profile.get("injuries", [])
        
        # 如果不是康复阶段且没有伤病，不应用此规则
        if not rehabilitation_phase and not injuries:
            return candidates, {"skipped": True, "reason": "非康复场景"}
        
        # 分离闭链和开链动作
        closed_chain = []
        open_chain = []
        other = []
        
        for candidate in candidates:
            kinetic_chain = self._get_kinetic_chain(candidate)
            
            if kinetic_chain == KineticChainType.CLOSED:
                # 闭链动作加分
                candidate["kinetic_chain_boost"] = 0.2
                closed_chain.append(candidate)
            elif kinetic_chain == KineticChainType.OPEN:
                open_chain.append(candidate)
            else:
                other.append(candidate)
        
        # 闭链优先排序
        sorted_candidates = closed_chain + other + open_chain
        
        return sorted_candidates, {
            "closed_chain_count": len(closed_chain),
            "open_chain_count": len(open_chain),
            "rehabilitation_phase": rehabilitation_phase,
            "has_injuries": bool(injuries)
        }
    
    async def _apply_force_balance_rule(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        推拉平衡规则 - 确保push:pull比例在1:1到2:1之间
        
        Requirements: 11.2
        
        规则逻辑:
        - 统计当前会话的推拉比例
        - 如果推力过多，优先推荐拉力动作
        - 如果拉力过多，优先推荐推力动作
        """
        # 获取当前会话的推拉统计
        push_count = session_context.get("push_count", 0)
        pull_count = session_context.get("pull_count", 0)
        
        # 如果没有会话上下文，不调整排序
        if push_count == 0 and pull_count == 0:
            return candidates, {"skipped": True, "reason": "无会话上下文"}
        
        # 计算当前比例
        if pull_count > 0:
            current_ratio = push_count / pull_count
        else:
            current_ratio = float('inf') if push_count > 0 else 1.0
        
        # 根据比例调整排序
        if current_ratio > 2.0:
            # 推力过多，优先拉力
            candidates = sorted(
                candidates,
                key=lambda x: (
                    0 if self._get_force_type(x) == ForceType.PULL else 1,
                    -x.get("score", 0)
                )
            )
            adjustment = "prioritize_pull"
        elif current_ratio < 1.0:
            # 拉力过多，优先推力
            candidates = sorted(
                candidates,
                key=lambda x: (
                    0 if self._get_force_type(x) == ForceType.PUSH else 1,
                    -x.get("score", 0)
                )
            )
            adjustment = "prioritize_push"
        else:
            adjustment = "balanced"
        
        return candidates, {
            "push_count": push_count,
            "pull_count": pull_count,
            "current_ratio": current_ratio,
            "adjustment": adjustment
        }
    
    # ============ 安全规则 ============
    
    async def _apply_joint_load_rule(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        关节负荷规则 - 排除涉及受伤关节的动作（增强版）
        
        Requirements: 11.3, 4.3, 4.6
        
        规则逻辑:
        1. 获取用户受伤关节列表
        2. 区分绝对禁忌（absolute）和相对禁忌（relative）
        3. 绝对禁忌：完全排除
        4. 相对禁忌：降低优先级但不完全排除
        5. 高负荷关节动作优先排除
        
        框架层领域无关 - Requirements 6.1, 6.2:
        - 关节关键词配置通过domain_adapter获取
        """
        health_profile = user_profile.get("health_status", {})
        injuries = health_profile.get("injuries", [])
        injury_history = health_profile.get("injury_history", [])
        
        if not injuries and not injury_history:
            return candidates, {"skipped": True, "reason": "无伤病记录"}
        
        # 提取受伤关节及其严重程度
        injured_joints = {}  # joint -> severity (absolute/relative/caution)
        
        for injury in injuries + injury_history:
            if isinstance(injury, dict):
                body_part = injury.get("body_part", "")
                severity = injury.get("severity", "relative")  # 默认相对禁忌
                status = injury.get("status", "active")  # active/recovered
                
                if body_part and status != "recovered":
                    # 如果已有记录，取更严重的级别
                    current_severity = injured_joints.get(body_part.lower())
                    if current_severity != "absolute":
                        injured_joints[body_part.lower()] = severity
            elif isinstance(injury, str):
                injured_joints[injury.lower()] = "relative"
        
        if not injured_joints:
            return candidates, {"skipped": True, "reason": "无活跃关节伤病"}
        
        # 使用实例变量（从domain_adapter加载）
        joint_keywords = self._joint_keywords
        
        if not joint_keywords:
            return candidates, {"skipped": True, "reason": "未配置关节关键词数据"}
        
        # 过滤涉及受伤关节的动作
        safe_candidates = []
        relative_risk_candidates = []  # 相对禁忌的动作
        filtered_exercises = []
        
        for candidate in candidates:
            exercise_name = candidate.get("exercise_name_zh", "")
            involved_joints = self._get_involved_joints(candidate)
            target_muscle = (candidate.get("primary_muscle_zh") or candidate.get("target_muscle") or "").lower()
            
            # 构建动作文本用于匹配
            exercise_text = f"{exercise_name} {target_muscle} {' '.join(involved_joints)}".lower()
            
            # 检查是否涉及受伤关节
            is_absolute_risk = False
            is_relative_risk = False
            matched_joint = None
            
            for injured_joint, severity in injured_joints.items():
                # 查找匹配的关节关键词
                for joint_name, keywords in joint_keywords.items():
                    if any(kw in injured_joint for kw in keywords):
                        # 检查动作是否涉及该关节
                        if any(kw in exercise_text for kw in keywords):
                            matched_joint = injured_joint
                            if severity == "absolute":
                                is_absolute_risk = True
                                break
                            else:
                                is_relative_risk = True
                
                if is_absolute_risk:
                    break
            
            if is_absolute_risk:
                # 绝对禁忌：完全排除
                filtered_exercises.append(exercise_name)
                logger.debug(f"关节负荷规则-绝对禁忌: {exercise_name} - 涉及 {matched_joint}")
            elif is_relative_risk:
                # 相对禁忌：降低优先级
                candidate["joint_load_penalty"] = -0.3
                candidate["joint_risk_level"] = "relative"
                candidate["affected_joint"] = matched_joint
                relative_risk_candidates.append(candidate)
                logger.debug(f"关节负荷规则-相对禁忌: {exercise_name} - 涉及 {matched_joint}")
            else:
                safe_candidates.append(candidate)
        
        # 安全动作优先，相对禁忌动作放后面
        sorted_candidates = safe_candidates + relative_risk_candidates
        
        return sorted_candidates, {
            "injured_joints": dict(injured_joints),
            "absolute_filtered_count": len(filtered_exercises),
            "relative_risk_count": len(relative_risk_candidates),
            "filtered_exercises": filtered_exercises[:5],  # 只记录前5个
            "severity_levels": {
                "absolute": sum(1 for s in injured_joints.values() if s == "absolute"),
                "relative": sum(1 for s in injured_joints.values() if s == "relative"),
                "caution": sum(1 for s in injured_joints.values() if s == "caution")
            }
        }
    
    def _get_involved_joints(self, exercise: Dict[str, Any]) -> List[str]:
        """获取动作涉及的关节"""
        # 尝试多个可能的字段名
        joints = exercise.get("involved_joints", [])
        if not joints:
            joints = exercise.get("joints", [])
        if not joints:
            joints = exercise.get("target_joints", [])
        
        if isinstance(joints, str):
            joints = [joints]
        
        return joints or []
    
    async def _apply_postural_correction_rule(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        体态矫正规则 - 推荐矫正动作并避免加重动作

        Requirements: 新增（体态矫正功能）

        规则逻辑:
        - 获取用户体态问题
        - 优先：查询Neo4j CORRECTS/AGGRAVATES关系进行精确分类
        - 降级：使用domain_adapter关键词匹配

        框架层领域无关 - Requirements 6.1, 6.2:
        - 体态问题配置通过domain_adapter获取
        - Neo4j关系数据作为优先数据源
        """
        health_profile = user_profile.get("health_status", {})
        postural_issues = health_profile.get("postural_issues", [])

        if not postural_issues:
            return candidates, {"skipped": True, "reason": "无体态问题"}

        # 分类动作
        corrective = []
        neutral = []
        aggravating = []
        neo4j_used = False
        neo4j_corrects_total = 0
        neo4j_aggravates_total = 0

        # ============ 优先：Neo4j CORRECTS/AGGRAVATES关系查询 ============
        if self.neo4j_client and hasattr(self.neo4j_client, 'get_session'):
            try:
                for candidate in candidates:
                    exercise_name = candidate.get("exercise_name_zh", "")
                    if not exercise_name:
                        neutral.append(candidate)
                        continue

                    # 通过asyncio.to_thread包装同步Neo4j查询（5s超时）
                    relations = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._query_neo4j_postural_relations_sync,
                            exercise_name,
                            postural_issues
                        ),
                        timeout=5.0
                    )

                    if relations["corrects"] and not relations["aggravates"]:
                        candidate["postural_boost"] = 0.3
                        candidate["postural_neo4j_corrects"] = [
                            d.get("issue_name", "") for d in relations["corrects_details"]
                        ]
                        corrective.append(candidate)
                        neo4j_corrects_total += 1
                    elif relations["aggravates"]:
                        candidate["postural_penalty"] = -0.2
                        candidate["postural_neo4j_aggravates"] = [
                            d.get("issue_name", "") for d in relations["aggravates_details"]
                        ]
                        aggravating.append(candidate)
                        neo4j_aggravates_total += 1
                    else:
                        neutral.append(candidate)

                # 只要有任何Neo4j查询成功执行（即使没有匹配结果），标记为已使用
                neo4j_used = True

            except asyncio.TimeoutError:
                logger.warning("Neo4j体态关系查询超时(5s)，降级到关键词匹配")
                corrective = []
                neutral = []
                aggravating = []
                neo4j_used = False
            except Exception as e:
                logger.warning(f"Neo4j体态关系批量查询失败，降级到关键词匹配: {e}")
                # 重置分类列表，准备用关键词方式重新分类
                corrective = []
                neutral = []
                aggravating = []
                neo4j_used = False

        # ============ 降级：domain_adapter关键词匹配 ============
        if not neo4j_used:
            # 使用实例变量（从domain_adapter加载）
            postural_config = self._postural_issue_config

            if not postural_config:
                return candidates, {"skipped": True, "reason": "未配置体态问题数据且Neo4j不可用"}

            corrective_keywords = set()
            aggravating_keywords = set()

            # 收集所有体态问题的关键词
            for issue in postural_issues:
                issue_name = issue if isinstance(issue, str) else issue.get("name", "")
                if issue_name in postural_config:
                    config = postural_config[issue_name]
                    corrective_keywords.update(config.get("corrective_keywords", []))
                    aggravating_keywords.update(config.get("aggravating_keywords", []))

            for candidate in candidates:
                exercise_name = candidate.get("exercise_name_zh", "")

                # 检查是否为矫正动作
                is_corrective = any(kw in exercise_name for kw in corrective_keywords)
                # 检查是否为加重动作
                is_aggravating = any(kw in exercise_name for kw in aggravating_keywords)

                if is_corrective and not is_aggravating:
                    candidate["postural_boost"] = 0.3
                    corrective.append(candidate)
                elif is_aggravating:
                    candidate["postural_penalty"] = -0.2
                    aggravating.append(candidate)
                else:
                    neutral.append(candidate)

        # 矫正动作优先，加重动作放最后
        sorted_candidates = corrective + neutral + aggravating

        metadata = {
            "postural_issues": postural_issues,
            "corrective_count": len(corrective),
            "aggravating_count": len(aggravating),
            "data_source": "neo4j" if neo4j_used else "keyword_fallback"
        }
        if neo4j_used:
            metadata["neo4j_corrects_matched"] = neo4j_corrects_total
            metadata["neo4j_aggravates_matched"] = neo4j_aggravates_total

        return sorted_candidates, metadata

    
    # ============ 恢复规则 ============
    
    async def _apply_recovery_time_rule(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        恢复时间规则 - 基于肌肉恢复时间推荐
        
        Requirements: 11.4
        
        规则逻辑:
        - 获取最近训练记录
        - 计算各肌群的恢复状态
        - 降低未恢复肌群动作的优先级
        
        框架层领域无关 - Requirements 6.1, 6.2:
        - 恢复时间配置通过domain_adapter获取
        """
        if not recent_training:
            return candidates, {"skipped": True, "reason": "无最近训练记录"}
        
        # 使用实例变量（从domain_adapter加载）
        recovery_hours_config = self._muscle_recovery_hours
        
        if not recovery_hours_config:
            return candidates, {"skipped": True, "reason": "未配置恢复时间数据"}
        
        # 计算各肌群的恢复状态
        now = datetime.now()
        muscle_recovery_status = {}  # 肌肉 -> 剩余恢复小时数
        
        for session in recent_training:
            session_time = session.get("timestamp") or session.get("created_at")
            if not session_time:
                continue
            
            # 解析时间
            if isinstance(session_time, str):
                try:
                    session_dt = datetime.fromisoformat(session_time.replace("Z", "+00:00"))
                except Exception:
                    continue
            elif isinstance(session_time, datetime):
                session_dt = session_time
            else:
                continue
            
            # 计算已过时间
            hours_since = (now - session_dt).total_seconds() / 3600
            
            # 获取训练的肌群
            for exercise in session.get("exercises", []):
                target_muscles = exercise.get("target_muscles", [])
                if isinstance(target_muscles, str):
                    target_muscles = [target_muscles]
                
                for muscle in target_muscles:
                    recovery_hours = recovery_hours_config.get(
                        muscle, 
                        recovery_hours_config.get("default", 48)
                    )
                    remaining = recovery_hours - hours_since
                    
                    if remaining > 0:
                        # 记录最长的剩余恢复时间
                        if muscle not in muscle_recovery_status:
                            muscle_recovery_status[muscle] = remaining
                        else:
                            muscle_recovery_status[muscle] = max(
                                muscle_recovery_status[muscle],
                                remaining
                            )
        
        if not muscle_recovery_status:
            return candidates, {"skipped": True, "reason": "所有肌群已恢复"}
        
        # 根据恢复状态调整候选排序
        def recovery_score(candidate):
            target_muscle = candidate.get("target_muscle", "")
            remaining = muscle_recovery_status.get(target_muscle, 0)
            
            if remaining > 0:
                # 未恢复的肌群降低优先级
                return remaining  # 剩余时间越长，排序越靠后
            return -1  # 已恢复的排在前面
        
        sorted_candidates = sorted(candidates, key=recovery_score)
        
        return sorted_candidates, {
            "unrecovered_muscles": {
                k: f"{v:.1f}h" for k, v in muscle_recovery_status.items()
            },
            "recent_sessions_count": len(recent_training)
        }
    
    # ============ 领域专业约束 ============
    
    async def _apply_body_type_constraint(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        体型约束 - 根据用户体型推荐适合的动作
        
        Requirements: 18.1
        
        规则逻辑:
        - 外胚型（瘦长）：优先复合动作、大重量
        - 中胚型（肌肉）：均衡推荐
        - 内胚型（圆润）：优先高代谢动作、复合动作
        
        框架层领域无关 - Requirements 6.1, 6.2:
        - 体型偏好配置通过domain_adapter获取
        """
        basic_info = user_profile.get("basic_info", {})
        body_type = basic_info.get("body_type", "").lower()
        
        if not body_type or body_type == "unknown":
            return candidates, {"skipped": True, "reason": "未设置体型"}
        
        # 使用实例变量（从domain_adapter加载）
        body_type_preferences = self._body_type_preferences
        
        if not body_type_preferences:
            return candidates, {"skipped": True, "reason": "未配置体型偏好数据"}
        
        preferences = body_type_preferences.get(body_type, {})
        if not preferences:
            return candidates, {"skipped": True, "reason": f"未知体型: {body_type}"}
        
        preferred_mechanics = preferences.get("preferred_mechanics", [])
        boost_keywords = preferences.get("boost_keywords", [])
        
        # 调整候选排序
        def body_type_score(candidate):
            score = 0
            
            # 机制匹配加分
            mechanic = candidate.get("mechanic", "").lower()
            if mechanic in preferred_mechanics:
                score += 0.1
            
            # 关键词匹配加分
            exercise_name = candidate.get("exercise_name_zh", "")
            if any(kw in exercise_name for kw in boost_keywords):
                score += 0.15
            
            return score
        
        # 按体型适合度排序
        for candidate in candidates:
            candidate["body_type_boost"] = body_type_score(candidate)
        
        sorted_candidates = sorted(
            candidates,
            key=lambda x: (-x.get("body_type_boost", 0), -x.get("score", 0))
        )
        
        return sorted_candidates, {
            "body_type": body_type,
            "preferences": preferences.get("description", "")
        }
    
    async def _apply_training_frequency_constraint(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        训练频率约束 - 根据用户训练频率调整推荐
        
        Requirements: 18.2
        
        规则逻辑:
        - 低频训练（1-2天/周）：优先全身训练动作
        - 中频训练（3-4天/周）：推荐分化训练
        - 高频训练（5+天/周）：可以更细致的分化
        """
        fitness_config = user_profile.get("fitness_config", {})
        training_days = fitness_config.get("training_days_per_week", 3)
        
        # 根据训练频率调整策略
        if training_days <= 2:
            # 低频：优先复合动作
            strategy = "full_body"
            preferred_mechanics = ["compound"]
        elif training_days <= 4:
            # 中频：均衡
            strategy = "split"
            preferred_mechanics = ["compound", "isolation"]
        else:
            # 高频：可以更多孤立动作
            strategy = "detailed_split"
            preferred_mechanics = ["compound", "isolation"]
        
        # 调整排序
        def frequency_score(candidate):
            mechanic = candidate.get("mechanic", "").lower()
            if mechanic in preferred_mechanics:
                return 0.1 if mechanic == "compound" else 0.05
            return 0
        
        for candidate in candidates:
            candidate["frequency_boost"] = frequency_score(candidate)
        
        return candidates, {
            "training_days_per_week": training_days,
            "strategy": strategy
        }
    
    async def _apply_session_duration_constraint(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        训练时长约束 - 确保推荐动作适合用户的训练时长
        
        Requirements: 18.3
        
        规则逻辑:
        - 短时训练（<45分钟）：优先高效复合动作
        - 中等时长（45-75分钟）：均衡推荐
        - 长时训练（>75分钟）：可以包含更多孤立动作
        """
        fitness_config = user_profile.get("fitness_config", {})
        session_duration = fitness_config.get("training_duration_per_session", 60)
        
        # 根据时长调整策略
        if session_duration < 45:
            strategy = "efficient"
            max_exercises = 5
            preferred_mechanics = ["compound"]
        elif session_duration <= 75:
            strategy = "balanced"
            max_exercises = 8
            preferred_mechanics = ["compound", "isolation"]
        else:
            strategy = "comprehensive"
            max_exercises = 12
            preferred_mechanics = ["compound", "isolation"]
        
        # 调整排序（短时训练优先复合动作）
        def duration_score(candidate):
            mechanic = candidate.get("mechanic", "").lower()
            if strategy == "efficient" and mechanic == "compound":
                return 0.15
            return 0
        
        for candidate in candidates:
            candidate["duration_boost"] = duration_score(candidate)
        
        return candidates, {
            "session_duration": session_duration,
            "strategy": strategy,
            "max_exercises": max_exercises
        }
    
    async def _apply_goal_alignment_constraint(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        目标对齐约束 - 优先推荐与用户目标匹配的动作
        
        Requirements: 18.4
        
        规则逻辑:
        - 增肌：优先复合动作，中等次数范围
        - 减脂：优先高代谢动作
        - 力量：优先大重量复合动作
        - 康复：优先低风险、闭链动作
        
        框架层领域无关 - Requirements 6.1, 6.2:
        - 目标偏好配置通过domain_adapter获取
        """
        fitness_goals = user_profile.get("fitness_goals", {})
        primary_goal = fitness_goals.get("primary_goal", "general_fitness").lower()
        
        # 目标映射（英文 primary_goal → _goal_preferences 键）
        goal_mapping = {
            "muscle_gain": "muscle_gain",
            "hypertrophy": "muscle_gain",
            "fat_loss": "fat_loss",
            "strength": "strength",
            "endurance": "endurance",
            "body_shaping": "body_shaping",
            "rehabilitation": "rehabilitation",
            "general_fitness": "general_fitness",
        }

        goal_key = goal_mapping.get(primary_goal, "general_fitness")
        
        # 使用实例变量（从domain_adapter加载）
        goal_preferences = self._goal_preferences
        
        if not goal_preferences:
            return candidates, {"skipped": True, "reason": "未配置目标偏好数据"}
        
        preferences = goal_preferences.get(goal_key, {})
        
        if not preferences:
            return candidates, {"skipped": True, "reason": f"未知目标: {primary_goal}"}
        
        preferred_mechanics = preferences.get("preferred_mechanics", [])
        preferred_force = preferences.get("preferred_force", [])
        preferred_kinetic = preferences.get("preferred_kinetic_chain", [])
        
        # 计算目标对齐分数
        def goal_alignment_score(candidate):
            score = 0
            
            # 机制匹配
            mechanic = candidate.get("mechanic", "").lower()
            if mechanic in preferred_mechanics:
                score += 0.1
            
            # 力类型匹配
            force = self._get_force_type(candidate)
            if force.value in preferred_force:
                score += 0.05
            
            # 动力链匹配（康复场景）
            if preferred_kinetic:
                kinetic = self._get_kinetic_chain(candidate)
                if kinetic.value in preferred_kinetic:
                    score += 0.15
            
            return score
        
        for candidate in candidates:
            candidate["goal_alignment_boost"] = goal_alignment_score(candidate)
        
        sorted_candidates = sorted(
            candidates,
            key=lambda x: (-x.get("goal_alignment_boost", 0), -x.get("score", 0))
        )
        
        return sorted_candidates, {
            "primary_goal": primary_goal,
            "goal_key": goal_key,
            "preferred_mechanics": preferred_mechanics
        }

    
    async def _apply_progressive_overload_constraint(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        渐进超负荷约束 - 根据训练周数调整难度推荐
        
        Requirements: 18.5
        
        规则逻辑:
        - 新手期（0-4周）：优先基础动作
        - 适应期（5-12周）：可以引入进阶动作
        - 成熟期（12+周）：可以尝试高级动作
        """
        training_system = user_profile.get("training_system", {})
        consecutive_weeks = training_system.get("consecutive_training_weeks", 0)
        
        fitness_config = user_profile.get("fitness_config", {})
        fitness_level = fitness_config.get("fitness_level", "beginner").lower()
        
        # 根据训练周数确定适合的难度
        if consecutive_weeks < 4:
            phase = "novice"
            allowed_difficulties = ["beginner", "easy", "novice", "初级", "简单"]
        elif consecutive_weeks < 12:
            phase = "adaptation"
            allowed_difficulties = ["beginner", "intermediate", "easy", "moderate", 
                                   "初级", "中级", "简单", "中等"]
        else:
            phase = "mature"
            allowed_difficulties = ["beginner", "intermediate", "advanced", 
                                   "初级", "中级", "高级"]
        
        # 根据用户等级进一步调整
        if fitness_level in ["advanced", "elite", "高级", "精英"]:
            allowed_difficulties.extend(["advanced", "elite", "hard", "高级", "困难"])
        
        # 过滤不适合的难度
        filtered_candidates = []
        for candidate in candidates:
            # 使用统一字段名：difficulty_zh / difficulty_en
            difficulty = (candidate.get("difficulty_zh") or candidate.get("difficulty_en") or "intermediate").lower()
            
            # 检查难度是否在允许范围内
            is_allowed = any(d in difficulty for d in allowed_difficulties)
            
            if is_allowed:
                filtered_candidates.append(candidate)
            else:
                # 不完全排除，但降低优先级
                candidate["progressive_penalty"] = -0.1
                filtered_candidates.append(candidate)
        
        # 按难度适合度排序
        sorted_candidates = sorted(
            filtered_candidates,
            key=lambda x: (x.get("progressive_penalty", 0), -x.get("score", 0))
        )
        
        return sorted_candidates, {
            "consecutive_weeks": consecutive_weeks,
            "phase": phase,
            "fitness_level": fitness_level,
            "allowed_difficulties": allowed_difficulties[:5]
        }
    
    async def _apply_nutrition_constraint(
        self,
        candidates: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        query: str,
        session_context: Dict[str, Any],
        recent_training: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        营养约束 - 根据营养摄入调整高强度动作推荐
        
        Requirements: 18.6
        
        规则逻辑:
        - 低热量摄入时，降低高强度动作优先级
        - 蛋白质不足时，提醒恢复可能受影响
        """
        nutrition_profile = user_profile.get("nutrition_profile", {})
        daily_calories = nutrition_profile.get("daily_calories", 2000)
        protein_g = nutrition_profile.get("protein_g", 100)
        
        basic_info = user_profile.get("basic_info", {})
        weight = basic_info.get("weight", 70)
        
        # 计算营养状态
        # 基础代谢估算（简化版）
        bmr_estimate = weight * 24  # 简化估算
        calorie_ratio = daily_calories / bmr_estimate if bmr_estimate > 0 else 1.0
        
        # 蛋白质摄入评估（推荐1.6-2.2g/kg）
        protein_per_kg = protein_g / weight if weight > 0 else 1.5
        
        # 营养状态判断
        if calorie_ratio < 0.8:
            nutrition_status = "deficit"
            intensity_limit = "moderate"
        elif calorie_ratio < 1.0:
            nutrition_status = "slight_deficit"
            intensity_limit = "high"
        else:
            nutrition_status = "adequate"
            intensity_limit = "any"
        
        # 根据营养状态调整
        if nutrition_status == "deficit":
            # 低热量时降低高强度动作优先级
            for candidate in candidates:
                # 使用统一字段名：difficulty_zh / difficulty_en
                difficulty = (candidate.get("difficulty_zh") or candidate.get("difficulty_en") or "").lower()
                if "advanced" in difficulty or "elite" in difficulty or "hard" in difficulty:
                    candidate["nutrition_penalty"] = -0.15
        
        return candidates, {
            "daily_calories": daily_calories,
            "protein_g": protein_g,
            "calorie_ratio": round(calorie_ratio, 2),
            "protein_per_kg": round(protein_per_kg, 2),
            "nutrition_status": nutrition_status,
            "intensity_limit": intensity_limit
        }
    
    # ============ 辅助方法 ============
    
    def _get_force_type(self, exercise: Dict[str, Any]) -> ForceType:
        """获取动作的力类型 - 使用统一字段名"""
        force = (exercise.get("force_zh") or exercise.get("force_en") or exercise.get("force") or "").lower()
        
        force_mapping = {
            "push": ForceType.PUSH,
            "pull": ForceType.PULL,
            "hold": ForceType.HOLD,
            "static": ForceType.HOLD,
            "推": ForceType.PUSH,
            "拉": ForceType.PULL,
            "保持": ForceType.HOLD,
        }
        
        return force_mapping.get(force, ForceType.UNKNOWN)
    
    def _get_kinetic_chain(self, exercise: Dict[str, Any]) -> KineticChainType:
        """获取动作的动力链类型"""
        kinetic = (exercise.get("kinetic_chain") or "").lower()
        
        kinetic_mapping = {
            "open_chain": KineticChainType.OPEN,
            "open": KineticChainType.OPEN,
            "closed_chain": KineticChainType.CLOSED,
            "closed": KineticChainType.CLOSED,
            "mixed": KineticChainType.MIXED,
            "开链": KineticChainType.OPEN,
            "闭链": KineticChainType.CLOSED,
            "混合": KineticChainType.MIXED,
        }
        
        return kinetic_mapping.get(kinetic, KineticChainType.UNKNOWN)
    
    def get_execution_logs(self, limit: int = 10) -> List[Layer3ExecutionLog]:
        """获取最近的执行日志"""
        return self.execution_logs[-limit:]
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """获取规则执行统计"""
        if not self.execution_logs:
            return {"total_executions": 0}
        
        stats = {
            "total_executions": len(self.execution_logs),
            "rules": {}
        }
        
        for log in self.execution_logs:
            for rule_result in log.rules_applied:
                rule_name = rule_result.rule_name
                if rule_name not in stats["rules"]:
                    stats["rules"][rule_name] = {
                        "applied_count": 0,
                        "skipped_count": 0,
                        "total_filtered": 0,
                        "avg_execution_time_ms": 0
                    }
                
                rule_stats = stats["rules"][rule_name]
                if rule_result.applied:
                    rule_stats["applied_count"] += 1
                    rule_stats["total_filtered"] += (
                        rule_result.candidates_before - rule_result.candidates_after
                    )
                else:
                    rule_stats["skipped_count"] += 1
                
                # 更新平均执行时间
                total_count = rule_stats["applied_count"] + rule_stats["skipped_count"]
                rule_stats["avg_execution_time_ms"] = (
                    (rule_stats["avg_execution_time_ms"] * (total_count - 1) + 
                     rule_result.execution_time_ms) / total_count
                )
        
        return stats
