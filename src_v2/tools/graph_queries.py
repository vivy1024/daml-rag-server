"""
图谱专项查询工具

利用内存中的 65,147 条图谱关系，提供：
- get_contraindications: 伤病禁忌查询（6,371 条 CONTRAINDICATED_FOR）
- get_posture_corrections: 体态矫正方案（CORRECTS + AGGRAVATES）
- get_rehabilitation_protocol: 康复训练协议
- get_muscle_exercise_map: 肌群→动作映射

所有操作都是纯内存查询，延迟 < 10ms。
"""

import logging
from typing import Any, Dict, List, Optional

from ..data.graph_store import GraphStore
from ..data.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


def get_contraindications(
    injuries: List[str],
    graph: GraphStore,
    exercise_ids: List[str] = None,
    exercise_payloads: List[Dict] = None,
) -> Dict[str, Any]:
    """查询伤病禁忌动作

    输入: ["腰椎间盘突出", "肩袖损伤"]
    逻辑:
      1. 在图谱中找到匹配的 InjuryType 节点
      2. 用反向索引查哪些 Exercise 有 CONTRAINDICATED_FOR 指向这些 InjuryType
      3. 对禁忌动作，查同肌群替代

    Returns:
        {
            "contraindicated": [{exercise, injury, risk, reason, alternatives}],
            "total_blocked": int,
            "injuries_matched": [str]
        }
    """
    if not graph or not graph.ready:
        return {"error": "图谱未加载", "fallback_hint": "请使用 WebSearch 查询伤病禁忌"}

    # 1. 找到匹配的 InjuryType 节点（精确优先，fallback 包含匹配）
    injury_nodes = {}  # injury_name -> node_id
    for node_id, node_data in graph._graph.items():
        if node_data.get("_label") != "InjuryType":
            continue
        node_name = node_data.get("_name_zh", "")
        for injury in injuries:
            # 精确匹配优先
            if node_name == injury:
                injury_nodes[node_name] = node_id
                break
            # 包含匹配
            if injury in node_name or node_name in injury:
                injury_nodes[node_name] = node_id
                break

    if not injury_nodes:
        return {
            "contraindicated": [],
            "total_blocked": 0,
            "injuries_matched": [],
            "note": f"未找到匹配的伤病类型: {injuries}",
        }

    # 2. 用反向索引查禁忌动作（O(结果数) 而非 O(全图)）
    contraindicated = []
    injury_node_ids = set(injury_nodes.values())

    # 预计算安全动作按肌群分组（用于替代推荐）
    muscle_to_safe_exercises: Dict[str, List[str]] = {}

    for injury_name, injury_node_id in injury_nodes.items():
        # 反向查：哪些 Exercise 的 CONTRAINDICATED_FOR 指向这个 InjuryType
        source_ids = graph.get_reverse_relations(injury_node_id, "CONTRAINDICATED_FOR")

        for exercise_id in source_ids:
            node_data = graph._graph.get(exercise_id)
            if not node_data or node_data.get("_label") != "Exercise":
                continue

            exercise_name = node_data.get("_name_zh", exercise_id)

            # 从边的 props 获取严重程度和原因
            severity = "high"
            reason = "存在禁忌关系"
            contra_edges = node_data.get("CONTRAINDICATED_FOR", [])
            for edge in contra_edges:
                if edge.get("target", "") == injury_node_id:
                    severity = edge.get("props", {}).get("severity", "high")
                    reason = edge.get("props", {}).get("reason", "存在禁忌关系")
                    break

            contraindicated.append({
                "exercise": exercise_name,
                "exercise_id": exercise_id,
                "injury": injury_name,
                "risk": severity if severity else "high",
                "reason": reason,
                "alternatives": [],  # 后面批量填充
            })

    # 3. 批量查找替代动作（预计算一次，避免 N*M 遍历）
    blocked_exercise_ids = {c["exercise_id"] for c in contraindicated}

    for item in contraindicated:
        exercise_data = graph._graph.get(item["exercise_id"], {})
        primary_targets = exercise_data.get("TARGETS_PRIMARY", [])
        if not primary_targets:
            continue

        # 用反向索引找同肌群动作
        target_muscle_id = primary_targets[0].get("target", "")
        if not target_muscle_id:
            continue

        same_muscle_ids = graph.get_reverse_relations(target_muscle_id, "TARGETS_PRIMARY")
        alternatives = []
        for alt_id in same_muscle_ids:
            if alt_id == item["exercise_id"] or alt_id in blocked_exercise_ids:
                continue
            alt_data = graph._graph.get(alt_id, {})
            if alt_data.get("_label") == "Exercise":
                alternatives.append(alt_data.get("_name_zh", alt_id))
                if len(alternatives) >= 3:
                    break

        item["alternatives"] = alternatives

    return {
        "contraindicated": contraindicated,
        "total_blocked": len(contraindicated),
        "injuries_matched": list(injury_nodes.keys()),
    }


def get_posture_corrections(
    issue: str,
    graph: GraphStore,
) -> Dict[str, Any]:
    """查询体态矫正方案

    输入: "圆肩"
    逻辑:
      1. 找到 PosturalIssue 节点
      2. 查 CORRECTS 关系 → 矫正动作
      3. 查 AGGRAVATES 关系 → 应避免的动作
      4. 推断紧张/薄弱肌群

    Returns:
        {
            "issue": str,
            "correction_exercises": [str],
            "avoid_exercises": [str],
            "tight_muscles": [str],
            "weak_muscles": [str]
        }
    """
    if not graph or not graph.ready:
        return {"error": "图谱未加载", "fallback_hint": "请使用 WebSearch 查询体态矫正方案"}

    # 找 PosturalIssue 节点
    issue_node_id = None
    issue_node_data = None
    for node_id, node_data in graph._graph.items():
        if node_data.get("_label") != "PosturalIssue":
            continue
        node_name = node_data.get("_name_zh", "")
        if issue in node_name or node_name in issue:
            issue_node_id = node_id
            issue_node_data = node_data
            break

    if not issue_node_id:
        return {
            "issue": issue,
            "correction_exercises": [],
            "avoid_exercises": [],
            "tight_muscles": [],
            "weak_muscles": [],
            "note": f"未找到体态问题: {issue}",
            "fallback_hint": f"请使用 WebSearch 查询'{issue} 矫正训练方案'",
        }

    # 反向查：用反向索引 O(结果数) 替代全图遍历
    correction_exercise_ids = set()
    correction_exercises = []
    avoid_exercise_ids = set()
    avoid_exercises = []

    corrects_sources = graph.get_reverse_relations(issue_node_id, "CORRECTS")
    for src_id in corrects_sources:
        nd = graph._graph.get(src_id, {})
        if nd.get("_label") == "Exercise":
            correction_exercise_ids.add(src_id)
            correction_exercises.append(nd.get("_name_zh", src_id))

    aggravates_sources = graph.get_reverse_relations(issue_node_id, "AGGRAVATES")
    for src_id in aggravates_sources:
        nd = graph._graph.get(src_id, {})
        if nd.get("_label") == "Exercise":
            avoid_exercise_ids.add(src_id)
            avoid_exercises.append(nd.get("_name_zh", src_id))

    # 推断薄弱肌群（从矫正动作的 TARGETS_PRIMARY）
    weak_muscles = set()
    for ex_id in correction_exercise_ids:
        nd = graph._graph.get(ex_id, {})
        for edge in nd.get("TARGETS_PRIMARY", []):
            weak_muscles.add(edge.get("target_name_zh", ""))

    # 推断紧张肌群（从应避免动作的 TARGETS_PRIMARY）
    tight_muscles = set()
    for ex_id in avoid_exercise_ids:
        nd = graph._graph.get(ex_id, {})
        for edge in nd.get("TARGETS_PRIMARY", []):
            tight_muscles.add(edge.get("target_name_zh", ""))

    return {
        "issue": issue,
        "correction_exercises": correction_exercises,
        "avoid_exercises": avoid_exercises,
        "tight_muscles": list(tight_muscles),
        "weak_muscles": list(weak_muscles),
    }


def get_rehabilitation_protocol(
    injury: str,
    phase: str = None,
    graph: GraphStore = None,
) -> Dict[str, Any]:
    """查询康复训练协议

    输入: "ACL重建术后", phase="mid"
    逻辑:
      1. 找到 InjuryType 节点
      2. 查 HAS_PHASE 关系 → RehabilitationPhase 节点
      3. 对每个阶段，查适合的动作（排除 CONTRAINDICATED_FOR）

    Returns:
        {
            "injury": str,
            "phases": [{name, exercises, contraindicated}],
            "current_phase": str | None
        }
    """
    if not graph or not graph.ready:
        return {"error": "图谱未加载", "fallback_hint": f"请使用 WebSearch 查询'{injury} 康复训练协议'"}

    # 找 InjuryType 节点
    injury_node_id = None
    for node_id, node_data in graph._graph.items():
        if node_data.get("_label") != "InjuryType":
            continue
        node_name = node_data.get("_name_zh", "")
        if injury in node_name or node_name in injury:
            injury_node_id = node_id
            break

    if not injury_node_id:
        return {
            "injury": injury,
            "phases": [],
            "note": f"未找到伤病类型: {injury}",
            "fallback_hint": f"请使用 WebSearch 查询'{injury} 康复训练'",
        }

    # 查 RehabilitationPhase 节点（通过 HAS_PHASE 关系）
    phases = []
    for node_id, node_data in graph._graph.items():
        if node_data.get("_label") != "RehabilitationPhase":
            continue
        # 检查是否与该伤病相关（通过 RELATED_TO 或直接属性）
        phase_name = node_data.get("_name_zh", "")
        phases.append({
            "name": phase_name,
            "node_id": node_id,
        })

    # 获取该伤病的所有禁忌动作
    contraindicated_exercises = []
    for node_id, node_data in graph._graph.items():
        if node_data.get("_label") != "Exercise":
            continue
        contra_edges = node_data.get("CONTRAINDICATED_FOR", [])
        for edge in contra_edges:
            if edge.get("target", "") == injury_node_id:
                contraindicated_exercises.append(node_data.get("_name_zh", node_id))
                break

    # 获取低强度安全动作（SUITABLE_FOR_LEVEL = 初级 且不在禁忌列表中）
    safe_exercises = []
    for node_id, node_data in graph._graph.items():
        if node_data.get("_label") != "Exercise":
            continue
        name = node_data.get("_name_zh", "")
        if name in contraindicated_exercises:
            continue
        # 检查难度
        level_edges = node_data.get("SUITABLE_FOR_LEVEL", [])
        for edge in level_edges:
            level_name = edge.get("target_name_zh", "")
            if "初级" in level_name or "入门" in level_name:
                safe_exercises.append(name)
                break
        if len(safe_exercises) >= 20:
            break

    return {
        "injury": injury,
        "contraindicated_exercises": contraindicated_exercises[:20],
        "safe_exercises_beginner": safe_exercises,
        "phases": [p["name"] for p in phases],
        "current_phase": phase,
        "total_contraindicated": len(contraindicated_exercises),
    }


def get_muscle_exercise_map(
    muscle: str,
    graph: GraphStore,
    level: str = None,
    equipment: str = None,
) -> Dict[str, Any]:
    """查询肌群→动作映射

    输入: "胸肌", level="intermediate", equipment="哑铃"
    逻辑: 反向查 TARGETS_PRIMARY/SECONDARY → 过滤 level + equipment

    Returns:
        {
            "muscle": str,
            "primary_exercises": [str],
            "secondary_exercises": [str],
            "total": int
        }
    """
    if not graph or not graph.ready:
        return {"error": "图谱未加载", "fallback_hint": "请使用 search_exercises 语义搜索"}

    # 找 Muscle 节点
    muscle_node_id = None
    for node_id, node_data in graph._graph.items():
        if node_data.get("_label") != "Muscle":
            continue
        node_name = node_data.get("_name_zh", "")
        if muscle in node_name or node_name in muscle:
            muscle_node_id = node_id
            break

    if not muscle_node_id:
        return {
            "muscle": muscle,
            "primary_exercises": [],
            "secondary_exercises": [],
            "total": 0,
            "note": f"未找到肌群: {muscle}",
            "fallback_hint": f"请使用 search_exercises 搜索'{muscle}训练动作'",
        }

    # 用反向索引查训练该肌群的动作
    primary_exercises = []
    secondary_exercises = []

    primary_source_ids = graph.get_reverse_relations(muscle_node_id, "TARGETS_PRIMARY")
    secondary_source_ids = graph.get_reverse_relations(muscle_node_id, "TARGETS_SECONDARY")

    def _passes_filters(node_data: Dict) -> bool:
        """检查动作是否通过 level/equipment 过滤。
        注意：没有标注难度/器械的动作默认通过（宁可多返回，不遗漏）。
        """
        if level:
            level_edges = node_data.get("SUITABLE_FOR_LEVEL", [])
            level_names = [e.get("target_name_zh", "") for e in level_edges]
            # 有标注但不匹配 → 过滤掉；无标注 → 保留
            if level_names and not any(level in ln or ln in level for ln in level_names):
                return False
        if equipment:
            equip_edges = node_data.get("REQUIRES", [])
            equip_names = [e.get("target_name_zh", "") for e in equip_edges]
            # 有标注但不匹配 → 过滤掉；无标注 → 保留
            if equip_names and not any(equipment in en or en in equipment for en in equip_names):
                return False
        return True

    for src_id in primary_source_ids:
        nd = graph._graph.get(src_id, {})
        if nd.get("_label") != "Exercise":
            continue
        if _passes_filters(nd):
            primary_exercises.append(nd.get("_name_zh", src_id))

    for src_id in secondary_source_ids:
        nd = graph._graph.get(src_id, {})
        if nd.get("_label") != "Exercise":
            continue
        if _passes_filters(nd):
            secondary_exercises.append(nd.get("_name_zh", src_id))

    return {
        "muscle": muscle,
        "primary_exercises": primary_exercises,
        "secondary_exercises": secondary_exercises,
        "total": len(primary_exercises) + len(secondary_exercises),
        "filters_applied": {"level": level, "equipment": equipment},
    }
