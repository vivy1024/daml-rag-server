# -*- coding: utf-8 -*-
"""
Neo4j 数据修正工具 — knowledge_correction Skill 的执行器

功能：
- 修改节点属性（SET）
- 创建关系（CREATE relationship）
- 补充缺失数据（MERGE）
- 所有操作需 HITL 确认后才执行

安全约束：
- 禁止 DELETE / DETACH DELETE / DROP
- 禁止修改数据库约束和索引
- 单次操作影响节点数 ≤ 10
- 所有操作记录审计日志

版本: v1.0.0
日期: 2026-05-10
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 禁止的 Cypher 关键词（大小写不敏感）
FORBIDDEN_PATTERNS = [
    r'\bDELETE\b',
    r'\bDETACH\s+DELETE\b',
    r'\bDROP\b',
    r'\bREMOVE\b',          # 禁止移除属性/标签
    r'\bCALL\s+db\.',       # 禁止调用数据库管理过程
    r'\bCALL\s+apoc\.',     # 禁止调用 APOC 过程
]

# 允许的操作类型
ALLOWED_OPERATIONS = {
    "SET_PROPERTY",         # 修改节点/关系属性
    "CREATE_RELATIONSHIP",  # 创建关系
    "MERGE_NODE",           # 合并（创建或匹配）节点
    "ADD_LABEL",            # 添加标签
}

# 单次操作最大影响节点数
MAX_AFFECTED_NODES = 10


@dataclass
class PatchOperation:
    """单个修正操作"""
    operation_type: str          # ALLOWED_OPERATIONS 之一
    cypher: str                  # Cypher 语句
    parameters: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""             # 修正原因
    source: str = ""             # 来源（评测样本ID / 用户反馈等）
    affected_nodes: int = 0      # 预估影响节点数


@dataclass
class PatchResult:
    """修正结果"""
    success: bool
    operation: PatchOperation
    records_affected: int = 0
    error: Optional[str] = None
    executed_at: Optional[datetime] = None


class Neo4jDataPatcher:
    """
    Neo4j 数据修正工具

    所有写入操作必须：
    1. 通过安全校验（无禁止关键词）
    2. 影响范围检查（≤10 节点）
    3. HITL 确认（由 Harness 层控制）
    4. 执行后记录审计日志
    """

    tool_name = "neo4j_data_patcher"
    description = "修正 Neo4j 知识图谱中的数据（属性/关系/标签），需人工确认"

    def __init__(self, neo4j_client=None):
        """
        Args:
            neo4j_client: Neo4jClient 实例（需要 execute_write_query 方法）
        """
        self.neo4j_client = neo4j_client
        self._audit_log: List[PatchResult] = []

    def validate_operation(self, operation: PatchOperation) -> tuple[bool, str]:
        """
        校验操作是否安全

        Returns:
            (is_valid, error_message)
        """
        # 1. 检查操作类型
        if operation.operation_type not in ALLOWED_OPERATIONS:
            return False, f"不允许的操作类型: {operation.operation_type}，允许: {ALLOWED_OPERATIONS}"

        # 2. 检查禁止关键词
        cypher_upper = operation.cypher.upper()
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, cypher_upper, re.IGNORECASE):
                return False, f"Cypher 包含禁止操作: {pattern}"

        # 3. 检查影响范围
        if operation.affected_nodes > MAX_AFFECTED_NODES:
            return False, f"影响节点数 {operation.affected_nodes} 超过限制 {MAX_AFFECTED_NODES}"

        # 4. 基本语法检查 — 必须有 MATCH（确保不是盲写）
        if "MATCH" not in cypher_upper and "MERGE" not in cypher_upper:
            return False, "Cypher 必须包含 MATCH 或 MERGE（禁止盲写）"

        return True, ""

    async def preview_operation(self, operation: PatchOperation) -> Dict[str, Any]:
        """
        预览操作影响（不执行写入）

        通过将写入语句改为只读查询来预览影响范围。
        """
        if not self.neo4j_client:
            return {"error": "Neo4j 客户端未初始化"}

        # 构造预览查询：只取 MATCH 部分 + RETURN count
        cypher = operation.cypher
        # 简单策略：找到 SET/CREATE 之前的 MATCH 部分
        match_part = re.split(r'\b(SET|CREATE|MERGE)\b', cypher, maxsplit=1, flags=re.IGNORECASE)
        if match_part:
            preview_query = match_part[0].strip() + " RETURN count(*) as affected_count"
        else:
            preview_query = cypher

        try:
            result = await self.neo4j_client.execute_query(preview_query, operation.parameters)
            count = result[0].get("affected_count", 0) if result else 0
            operation.affected_nodes = count

            return {
                "preview_query": preview_query,
                "affected_count": count,
                "within_limit": count <= MAX_AFFECTED_NODES,
            }
        except Exception as e:
            return {"error": f"预览查询失败: {str(e)}"}

    async def execute_operation(
        self,
        operation: PatchOperation,
        hitl_approved: bool = False,
    ) -> PatchResult:
        """
        执行修正操作

        Args:
            operation: 修正操作
            hitl_approved: 是否已获得人工确认

        Returns:
            PatchResult
        """
        # 安全门：必须 HITL 确认
        if not hitl_approved:
            result = PatchResult(
                success=False,
                operation=operation,
                error="操作未获人工确认（HITL required）",
            )
            self._audit_log.append(result)
            return result

        # 校验
        is_valid, error = self.validate_operation(operation)
        if not is_valid:
            result = PatchResult(
                success=False,
                operation=operation,
                error=f"安全校验失败: {error}",
            )
            self._audit_log.append(result)
            return result

        # 执行
        if not self.neo4j_client:
            result = PatchResult(
                success=False,
                operation=operation,
                error="Neo4j 客户端未初始化",
            )
            self._audit_log.append(result)
            return result

        try:
            records = await self.neo4j_client.execute_write_query(
                operation.cypher, operation.parameters
            )
            result = PatchResult(
                success=True,
                operation=operation,
                records_affected=len(records) if records else 0,
                executed_at=datetime.now(),
            )
            logger.info(
                f"✅ Neo4j 数据修正成功: type={operation.operation_type}, "
                f"reason={operation.reason}, affected={result.records_affected}"
            )
        except Exception as e:
            result = PatchResult(
                success=False,
                operation=operation,
                error=f"执行失败: {str(e)}",
            )
            logger.error(f"❌ Neo4j 数据修正失败: {e}")

        self._audit_log.append(result)
        return result

    async def batch_execute(
        self,
        operations: List[PatchOperation],
        hitl_approved: bool = False,
    ) -> List[PatchResult]:
        """批量执行修正操作（逐条执行，任一失败则停止）"""
        results = []
        for op in operations:
            result = await self.execute_operation(op, hitl_approved=hitl_approved)
            results.append(result)
            if not result.success:
                logger.warning(f"⚠️ 批量修正在第 {len(results)} 条停止: {result.error}")
                break
        return results

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return [
            {
                "success": r.success,
                "operation_type": r.operation.operation_type,
                "cypher": r.operation.cypher,
                "reason": r.operation.reason,
                "source": r.operation.source,
                "records_affected": r.records_affected,
                "error": r.error,
                "executed_at": r.executed_at.isoformat() if r.executed_at else None,
            }
            for r in self._audit_log
        ]

    # ===== 便捷方法：常见修正操作 =====

    def create_contraindication(
        self,
        exercise_name_zh: str,
        injury_type_name: str,
        severity: str = "high",
        reason: str = "",
        source: str = "",
    ) -> PatchOperation:
        """创建动作-伤病禁忌关系"""
        return PatchOperation(
            operation_type="CREATE_RELATIONSHIP",
            cypher="""
                MATCH (e:Exercise {name_zh: $exercise_name})
                MATCH (i:InjuryType {name: $injury_name})
                MERGE (e)-[r:CONTRAINDICATED_FOR]->(i)
                SET r.severity = $severity, r.reason = $reason, r.created_at = datetime()
                RETURN e.name_zh, i.name, r.severity
            """,
            parameters={
                "exercise_name": exercise_name_zh,
                "injury_name": injury_type_name,
                "severity": severity,
                "reason": reason,
            },
            reason=f"补充禁忌关系: {exercise_name_zh} → {injury_type_name}",
            source=source,
            affected_nodes=2,
        )

    def update_exercise_property(
        self,
        exercise_name_zh: str,
        property_name: str,
        new_value: Any,
        reason: str = "",
        source: str = "",
    ) -> PatchOperation:
        """修改动作属性"""
        return PatchOperation(
            operation_type="SET_PROPERTY",
            cypher=f"""
                MATCH (e:Exercise {{name_zh: $exercise_name}})
                SET e.{property_name} = $new_value
                RETURN e.name_zh, e.{property_name}
            """,
            parameters={
                "exercise_name": exercise_name_zh,
                "new_value": new_value,
            },
            reason=f"修改属性: {exercise_name_zh}.{property_name} = {new_value}",
            source=source,
            affected_nodes=1,
        )

    def create_posture_correction_relation(
        self,
        exercise_name_zh: str,
        postural_issue_name: str,
        relation_type: str = "CORRECTS",
        source: str = "",
    ) -> PatchOperation:
        """创建动作-体态矫正关系"""
        if relation_type not in ("CORRECTS", "AGGRAVATES"):
            raise ValueError(f"relation_type 必须是 CORRECTS 或 AGGRAVATES，收到: {relation_type}")

        return PatchOperation(
            operation_type="CREATE_RELATIONSHIP",
            cypher=f"""
                MATCH (e:Exercise {{name_zh: $exercise_name}})
                MATCH (p:PosturalIssue {{name: $issue_name}})
                MERGE (e)-[r:{relation_type}]->(p)
                SET r.created_at = datetime()
                RETURN e.name_zh, p.name
            """,
            parameters={
                "exercise_name": exercise_name_zh,
                "issue_name": postural_issue_name,
            },
            reason=f"补充体态关系: {exercise_name_zh} -{relation_type}-> {postural_issue_name}",
            source=source,
            affected_nodes=2,
        )

    def update_muscle_training_params(
        self,
        muscle_name_zh: str,
        mev: Optional[int] = None,
        mav: Optional[int] = None,
        mrv: Optional[int] = None,
        reason: str = "",
        source: str = "",
    ) -> PatchOperation:
        """修改肌群训练参数（MEV/MAV/MRV）"""
        set_clauses = []
        params = {"muscle_name": muscle_name_zh}

        if mev is not None:
            set_clauses.append("m.mev = $mev")
            params["mev"] = mev
        if mav is not None:
            set_clauses.append("m.mav = $mav")
            params["mav"] = mav
        if mrv is not None:
            set_clauses.append("m.mrv = $mrv")
            params["mrv"] = mrv

        if not set_clauses:
            raise ValueError("至少需要提供一个参数（mev/mav/mrv）")

        return PatchOperation(
            operation_type="SET_PROPERTY",
            cypher=f"""
                MATCH (m:Muscle {{name_zh: $muscle_name}})
                SET {', '.join(set_clauses)}
                RETURN m.name_zh, m.mev, m.mav, m.mrv
            """,
            parameters=params,
            reason=reason or f"修改肌群训练参数: {muscle_name_zh}",
            source=source,
            affected_nodes=1,
        )
