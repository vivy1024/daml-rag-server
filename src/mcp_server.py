"""
DAML-RAG MCP Server — 将健身领域工具暴露为标准 MCP 协议

使用 FastMCP 框架，通过 stdio transport 与 YuzhenFork Agent 通信。
暴露 10 个高内聚工具，内部调用三层检索引擎/Neo4j/规则引擎。

启动方式：
  docker exec fitness_daml_rag python -m src.mcp_server
  或
  python -m src.mcp_server
"""

import sys
import logging
from typing import Annotated, Optional
from pydantic import Field

from mcp.server.fastmcp import FastMCP

# 配置 logging 到 stderr（stdio MCP 不能 print 到 stdout）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_server")

# === 初始化 MCP Server ===
mcp = FastMCP("daml-rag-fitness")


# === 延迟初始化客户端（避免 import 时连接） ===

_clients_initialized = False
_neo4j_client = None
_qdrant_client = None
_three_layer_engine = None
_tool_registry = None


async def _ensure_clients():
    """延迟初始化数据库客户端和工具注册表"""
    global _clients_initialized, _neo4j_client, _qdrant_client, _three_layer_engine, _tool_registry

    if _clients_initialized:
        return

    logger.info("Initializing DAML-RAG clients...")

    try:
        from src.framework.clients.neo4j_client import Neo4jClient
        from src.framework.clients.qdrant_client import QdrantClientWrapper
        from src.framework.retrieval.three_layer_engine import ThreeLayerRetrievalEngine
        from src.applications.fitness.mcp_tools.registry import MCPToolRegistry

        # 初始化客户端（使用容器内地址）
        _neo4j_client = Neo4jClient(
            uri="bolt://neo4j:7687",
            user="neo4j",
            password="fitness_neo4j_2024",
        )
        _qdrant_client = QdrantClientWrapper(host="qdrant", port=6333)
        _three_layer_engine = ThreeLayerRetrievalEngine(
            neo4j_client=_neo4j_client,
            qdrant_client=_qdrant_client,
        )

        # 注册所有工具
        _tool_registry = MCPToolRegistry()
        await _register_all_tools(_tool_registry)

        _clients_initialized = True
        logger.info(f"DAML-RAG clients initialized. {len(_tool_registry.tools)} tools registered.")
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}", exc_info=True)
        raise


async def _register_all_tools(registry):
    """注册所有 MCP 工具到 registry"""
    from src.applications.fitness.mcp_tools.exercise.intelligent_exercise_selector import IntelligentExerciseSelector
    from src.applications.fitness.mcp_tools.exercise.exercise_alternative_finder import ExerciseAlternativeFinder
    from src.applications.fitness.mcp_tools.safety.contraindications_checker import ContraindicationsChecker
    from src.applications.fitness.mcp_tools.safety.injury_risk_assessor import InjuryRiskAssessor
    from src.applications.fitness.mcp_tools.safety.postural_assessor import PosturalAssessor
    from src.applications.fitness.mcp_tools.training.muscle_group_volume_calculator import MuscleGroupVolumeCalculator
    from src.applications.fitness.mcp_tools.nutrition.tdee_calculator import TDEECalculator

    tools = [
        IntelligentExerciseSelector(_neo4j_client, _qdrant_client, _three_layer_engine),
        ExerciseAlternativeFinder(_neo4j_client, _qdrant_client, _three_layer_engine),
        ContraindicationsChecker(_neo4j_client, _qdrant_client, _three_layer_engine),
        InjuryRiskAssessor(_neo4j_client, _qdrant_client, _three_layer_engine),
        PosturalAssessor(_neo4j_client, _qdrant_client, _three_layer_engine),
        MuscleGroupVolumeCalculator(_neo4j_client, _qdrant_client, _three_layer_engine),
        TDEECalculator(_neo4j_client, _qdrant_client, _three_layer_engine),
    ]

    for tool in tools:
        try:
            registry.register_tool(tool)
        except Exception as e:
            logger.warning(f"Failed to register tool {tool.get_name()}: {e}")


# === MCP 工具定义 ===

@mcp.tool()
async def search_exercises(
    query: Annotated[str, Field(description="自然语言查询，如'练胸的动作'")],
    muscle_group: Annotated[Optional[str], Field(description="目标肌群")] = None,
    difficulty: Annotated[Optional[str], Field(description="难度等级: beginner/intermediate/advanced")] = None,
    equipment: Annotated[Optional[list[str]], Field(description="可用器械列表")] = None,
    injuries: Annotated[Optional[list[str]], Field(description="用户伤病（用于安全过滤）")] = None,
    top_k: Annotated[int, Field(description="返回数量")] = 10,
) -> dict:
    """基于三层检索引擎的动作搜索。支持语义搜索+图谱推理+安全规则验证。"""
    await _ensure_clients()

    try:
        tool = _tool_registry.tools.get("intelligent_exercise_selector")
        if not tool:
            return {"error": "Exercise selector tool not available"}

        result = await tool.execute({
            "query": query,
            "muscle_group": muscle_group,
            "difficulty": difficulty,
            "equipment": equipment or [],
            "injuries": injuries or [],
            "top_k": top_k,
        })
        return result
    except Exception as e:
        logger.error(f"search_exercises failed: {e}")
        return {"error": str(e)}


@mcp.tool()
async def check_contraindications(
    exercise_ids: Annotated[list[str], Field(description="动作 ID 列表")],
    user_conditions: Annotated[list[str], Field(description="用户健康状况列表")],
) -> dict:
    """批量检查动作禁忌症。基于 Neo4j CONTRAINDICATED_FOR 关系。"""
    await _ensure_clients()

    try:
        tool = _tool_registry.tools.get("contraindications_checker")
        if not tool:
            return {"error": "Contraindications checker not available"}

        result = await tool.execute({
            "exercise_ids": exercise_ids,
            "user_conditions": user_conditions,
        })
        return result
    except Exception as e:
        logger.error(f"check_contraindications failed: {e}")
        return {"error": str(e)}


@mcp.tool()
async def find_alternatives(
    exercise_id: Annotated[str, Field(description="原动作 ID")],
    reason: Annotated[str, Field(description="替代原因（伤病/器械/偏好）")],
    constraints: Annotated[Optional[dict], Field(description="约束条件")] = None,
) -> dict:
    """查找动作替代方案。基于共享肌肉群和运动模式。"""
    await _ensure_clients()

    try:
        tool = _tool_registry.tools.get("exercise_alternative_finder")
        if not tool:
            return {"error": "Alternative finder not available"}

        result = await tool.execute({
            "exercise_id": exercise_id,
            "reason": reason,
            "constraints": constraints or {},
        })
        return result
    except Exception as e:
        logger.error(f"find_alternatives failed: {e}")
        return {"error": str(e)}


@mcp.tool()
async def query_muscle_relations(
    entity: Annotated[str, Field(description="肌肉名或动作名")],
    direction: Annotated[str, Field(description="查询方向: forward/reverse/both")] = "both",
    include_volume: Annotated[bool, Field(description="是否包含 MEV/MAV/MRV")] = False,
) -> dict:
    """查询肌肉-动作关系图谱。支持正向（肌肉→动作）和反向（动作→肌肉）。"""
    await _ensure_clients()

    try:
        # 直接使用 Neo4j 查询
        if direction in ("forward", "both"):
            query = """
            MATCH (m:MuscleGroup {name: $entity})-[r:TARGETS|ASSISTS]-(e:Exercise)
            RETURN e.name as exercise, type(r) as relation, r.activation as activation
            LIMIT 20
            """
            forward_results = await _neo4j_client.run_query(query, {"entity": entity})
        else:
            forward_results = []

        if direction in ("reverse", "both"):
            query = """
            MATCH (e:Exercise {name: $entity})-[r:TARGETS|ASSISTS]->(m:MuscleGroup)
            RETURN m.name as muscle, type(r) as relation, r.activation as activation
            """
            reverse_results = await _neo4j_client.run_query(query, {"entity": entity})
        else:
            reverse_results = []

        return {
            "entity": entity,
            "forward_relations": forward_results if direction != "reverse" else [],
            "reverse_relations": reverse_results if direction != "forward" else [],
        }
    except Exception as e:
        logger.error(f"query_muscle_relations failed: {e}")
        return {"error": str(e)}


@mcp.tool()
async def assess_injury_risk(
    exercise_ids: Annotated[list[str], Field(description="动作 ID 列表")],
    user_injuries: Annotated[list[str], Field(description="用户伤病列表")],
    user_level: Annotated[str, Field(description="训练水平")] = "intermediate",
) -> dict:
    """评估动作的损伤风险。结合用户伤病史和动作力学特征。"""
    await _ensure_clients()

    try:
        tool = _tool_registry.tools.get("injury_risk_assessor")
        if not tool:
            return {"error": "Injury risk assessor not available"}

        result = await tool.execute({
            "exercise_ids": exercise_ids,
            "user_injuries": user_injuries,
            "user_level": user_level,
        })
        return result
    except Exception as e:
        logger.error(f"assess_injury_risk failed: {e}")
        return {"error": str(e)}


@mcp.tool()
async def check_postural_issues(
    postural_issues: Annotated[list[str], Field(description="体态问题列表")],
    exercise_ids: Annotated[Optional[list[str]], Field(description="待检查动作（不传则推荐矫正动作）")] = None,
) -> dict:
    """体态问题检查。查询 CORRECTS/AGGRAVATES 关系。"""
    await _ensure_clients()

    try:
        tool = _tool_registry.tools.get("postural_assessor")
        if not tool:
            return {"error": "Postural assessor not available"}

        result = await tool.execute({
            "postural_issues": postural_issues,
            "exercise_ids": exercise_ids or [],
        })
        return result
    except Exception as e:
        logger.error(f"check_postural_issues failed: {e}")
        return {"error": str(e)}


@mcp.tool()
async def get_strength_standards(
    exercise: Annotated[str, Field(description="动作名称")],
    gender: Annotated[Optional[str], Field(description="性别: male/female")] = None,
    bodyweight: Annotated[Optional[float], Field(description="体重 kg")] = None,
) -> dict:
    """获取力量标准。按性别、体重、动作查询各水平标准。"""
    await _ensure_clients()

    try:
        query = """
        MATCH (e:Exercise {name: $exercise})-[:HAS_STANDARD]->(s:StrengthStandard)
        WHERE ($gender IS NULL OR s.gender = $gender)
        RETURN s.level as level, s.ratio as ratio, s.description as description
        ORDER BY s.ratio
        """
        results = await _neo4j_client.run_query(query, {
            "exercise": exercise,
            "gender": gender,
        })

        standards = []
        for r in results:
            entry = {"level": r["level"], "ratio": r["ratio"], "description": r["description"]}
            if bodyweight and r.get("ratio"):
                entry["estimated_weight"] = round(bodyweight * r["ratio"], 1)
            standards.append(entry)

        return {"exercise": exercise, "standards": standards}
    except Exception as e:
        logger.error(f"get_strength_standards failed: {e}")
        return {"error": str(e)}


@mcp.tool()
async def get_training_volume(
    muscle_group: Annotated[str, Field(description="肌群名称")],
) -> dict:
    """获取肌群训练容量参数（MEV/MAV/MRV）和恢复时间。"""
    await _ensure_clients()

    try:
        tool = _tool_registry.tools.get("muscle_group_volume_calculator")
        if not tool:
            return {"error": "Volume calculator not available"}

        result = await tool.execute({"muscle_group": muscle_group})
        return result
    except Exception as e:
        logger.error(f"get_training_volume failed: {e}")
        return {"error": str(e)}


@mcp.tool()
async def search_foods(
    query: Annotated[str, Field(description="搜索文本")],
    min_protein: Annotated[Optional[float], Field(description="最低蛋白质 g")] = None,
    max_calories: Annotated[Optional[float], Field(description="最高热量 kcal")] = None,
    top_k: Annotated[int, Field(description="返回数量")] = 10,
) -> dict:
    """食物营养搜索。支持语义搜索和营养素过滤。"""
    await _ensure_clients()

    try:
        # 使用 Qdrant 向量搜索
        results = await _qdrant_client.search(
            collection_name="foods",
            query_text=query,
            limit=top_k,
            filters={
                "min_protein": min_protein,
                "max_calories": max_calories,
            } if min_protein or max_calories else None,
        )
        return {"query": query, "results": results}
    except Exception as e:
        logger.error(f"search_foods failed: {e}")
        return {"error": str(e)}


@mcp.tool()
async def search_knowledge(
    query: Annotated[str, Field(description="搜索文本")],
    category: Annotated[Optional[str], Field(description="知识分类: 训练理论/营养学/运动生理学")] = None,
    top_k: Annotated[int, Field(description="返回数量")] = 5,
) -> dict:
    """知识库语义搜索。搜索健身教科书、训练理论等结构化知识。"""
    await _ensure_clients()

    try:
        results = await _qdrant_client.search(
            collection_name="knowledge",
            query_text=query,
            limit=top_k,
            filters={"category": category} if category else None,
        )
        return {"query": query, "results": results}
    except Exception as e:
        logger.error(f"search_knowledge failed: {e}")
        return {"error": str(e)}


# === 入口 ===

if __name__ == "__main__":
    logger.info("Starting DAML-RAG MCP Server (stdio transport)...")
    mcp.run(transport="stdio")
